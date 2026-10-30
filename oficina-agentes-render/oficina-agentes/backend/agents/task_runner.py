"""
Ejecutor de tareas por departamento + revisión obligatoria de la Asistente.
"""
import os
from crewai import Task, Crew, Process
from dotenv import load_dotenv

from agents.all_agents import create_assistant, create_department_agents, get_llm, DEPARTMENTS
from tools.web_search import web_search_tool
from tools.code_executor import code_executor_tool
from tools.file_tools import read_file_tool, write_file_tool, list_files_tool
from tools.memory_tool import add_lesson_tool, get_lessons_tool
from tools.file_manager import save_outgoing_file, get_pending_for_assistant

load_dotenv()

# Herramientas disponibles según el departamento
BASE_TOOLS = [web_search_tool, get_lessons_tool, add_lesson_tool, list_files_tool, read_file_tool, write_file_tool]
CODE_TOOLS = BASE_TOOLS + [code_executor_tool]


def run_department_task(dept_id: str, task_text: str, on_event=None) -> dict:
    """
    Versión estable:
    - 1 agente (el jefe)
    - sin tools (por ahora)
    - proceso sequential
    - modelo distinto por departamento
    """
    if dept_id not in DEPARTMENTS:
        return {"success": False, "error": f"Departamento desconocido: {dept_id}"}

    # LLM del departamento + Asistente
    llm = get_llm(dept_id=dept_id)
    llm_assistant = get_llm(temperature=0.2)  # Asistente con modelo por defecto

    boss, members, info = create_department_agents(dept_id, tools=[], llm=llm)
    assistant = create_assistant(llm=llm_assistant)

    if on_event:
        on_event({
            "type": "status",
            "department": dept_id,
            "message": f"{info['name']}: el equipo está trabajando..."
        })

    work_task = Task(
        description=(
            f"Eres el jefe de {info['name']} ({info['boss']}). "
            f"Tu especialidad: {info['focus']}.\n\n"
            f"Tarea del usuario:\n{task_text}\n\n"
            "Responde en español de forma clara y útil. "
            "Si la tarea es solo un saludo o está incompleta, responde amable y pide más detalle. "
            "Si es una tarea real, entrega un resultado concreto (texto, plan, pasos o resumen)."
        ),
        expected_output="Respuesta clara y útil en español.",
        agent=boss,
    )

    crew = Crew(
        agents=[boss],
        tasks=[work_task],
        process=Process.sequential,
        verbose=True,
    )

    try:
        result = crew.kickoff()
        result_text = str(result)

        filename = f"entregable_{dept_id}.md"
        file_entry = save_outgoing_file(
            filename=filename,
            content=result_text,
            department=info["name"],
            description=f"Resultado de: {task_text[:80]}"
        )

        if on_event:
            on_event({
                "type": "status",
                "department": dept_id,
                "message": f"{info['name']} terminó. La Asistente está revisando..."
            })

        review_task = Task(
            description=(
                f"Como Asistente de Dirección, revisa este entregable de {info['name']}.\n\n"
                f"Tarea original: {task_text}\n\n"
                f"Entregable:\n{result_text[:4000]}\n\n"
                "Responde SOLO así:\n"
                "APROBADO - comentario breve\n"
                "o\n"
                "RECHAZADO - qué falta o qué está mal"
            ),
            expected_output="APROBADO o RECHAZADO + comentario breve.",
            agent=assistant,
        )

        review_crew = Crew(
            agents=[assistant],
            tasks=[review_task],
            process=Process.sequential,
            verbose=True,
        )
        review_result = str(review_crew.kickoff())
        approved = "APROBADO" in review_result.upper() and "RECHAZADO" not in review_result.upper()[:15]

        from tools.file_manager import assistant_review
        assistant_review(
            file_id=file_entry["id"],
            approve=approved,
            comment=review_result[:500],
            reviewer="Asistente"
        )

        if on_event:
            on_event({
                "type": "assistant_review",
                "department": dept_id,
                "approved": approved,
                "message": f"Asistente: {'✅ APROBADO' if approved else '❌ RECHAZADO'} – {info['name']}",
                "comment": review_result[:400],
                "file_id": file_entry["id"],
                "filename": filename,
            })

        return {
            "success": True,
            "department": info["name"],
            "result": result_text,
            "file_id": file_entry["id"],
            "filename": filename,
            "assistant_approved": approved,
            "assistant_comment": review_result,
        }

    except Exception as e:
        if on_event:
            on_event({"type": "error", "message": str(e)})
        return {"success": False, "error": str(e)}

def run_meeting_reports(on_event=None) -> dict:
    """
    Genera un resumen de reunión con los últimos entregables aprobados
    para mostrar en la pantalla de la sala de reuniones.
    """
    from tools.file_manager import get_approved_for_user, list_files

    approved = get_approved_for_user()
    pending = get_pending_for_assistant()

    lines = ["# Informe de Reunión – IA Market Agents\n"]
    lines.append(f"**Fecha:** generado automáticamente\n")

    if approved:
        lines.append("## Entregables aprobados por la Asistente\n")
        for f in approved[:10]:
            lines.append(f"- **{f['filename']}** ({f['department']}) – {f.get('description','')[:60]}")
    else:
        lines.append("## Entregables aprobados\nNinguno pendiente de presentar.\n")

    if pending:
        lines.append("\n## Pendientes de revisión de la Asistente\n")
        for f in pending[:5]:
            lines.append(f"- {f['filename']} ({f['department']})")

    report = "\n".join(lines)

    if on_event:
        on_event({
            "type": "meeting_report",
            "message": "Informe de reunión generado",
            "report": report,
            "approved_count": len(approved),
            "pending_count": len(pending),
        })

    return {
        "success": True,
        "report": report,
        "approved": approved,
        "pending": pending,
    }
