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
    Ejecuta una tarea en un departamento y deja el entregable
    pendiente de aprobación de la Asistente.
    """
    if dept_id not in DEPARTMENTS:
        return {"success": False, "error": f"Departamento desconocido: {dept_id}"}

    llm = get_llm()
    tools = CODE_TOOLS if dept_id == "ing" else BASE_TOOLS

    boss, members, info = create_department_agents(dept_id, tools=tools, llm=llm)
    assistant = create_assistant(llm)

    if on_event:
        on_event({
            "type": "status",
            "department": dept_id,
            "message": f"{info['name']}: el equipo está trabajando en la tarea..."
        })

    # Tarea del departamento
    work_task = Task(
        description=(
            f"Tarea asignada al departamento de {info['name']}:\n\n"
            f"{task_text}\n\n"
            "Instrucciones:\n"
            "1. Consulta lecciones aprendidas si es relevante.\n"
            "2. Investiga lo necesario.\n"
            "3. Produce el entregable (texto, código, plan, informe...).\n"
            "4. Si generas archivos, guárdalos con write_file.\n"
            "5. Prepara un resumen claro de lo realizado para la Asistente de Dirección."
        ),
        expected_output=(
            "Un entregable completo + un resumen ejecutivo de máximo 1 página "
            "que la Asistente pueda revisar rápidamente."
        ),
        agent=boss,
    )

    crew = Crew(
        agents=[boss] + members,
        tasks=[work_task],
        process=Process.hierarchical,
        manager_llm=llm,
        verbose=True,
    )

    try:
        result = crew.kickoff()
        result_text = str(result)

        # Guardar el entregable como archivo pendiente de la Asistente
        filename = f"entregable_{dept_id}_{info['name'].lower().replace(' ', '_')}.md"
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
                "message": f"{info['name']} terminó. Entregable enviado a la Asistente para revisión."
            })

        # La Asistente revisa automáticamente (puede aprobar o rechazar)
        review_task = Task(
            description=(
                f"Como Asistente de Dirección, revisa el siguiente entregable del departamento de {info['name']}.\n\n"
                f"Tarea original: {task_text}\n\n"
                f"Entregable:\n{result_text[:6000]}\n\n"
                "Decide:\n"
                "- Si está bien → di exactamente: APROBADO\n"
                "- Si está mal o incompleto → di exactamente: RECHAZADO y explica qué falta o qué está mal.\n"
                "Sé exigente pero justa. Solo aprueba trabajo de calidad."
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
        approved = "APROBADO" in review_result.upper() and "RECHAZADO" not in review_result.upper()[:20]

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