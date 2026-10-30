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
    - 1 agente
    - sin tools de CrewAI (evita error de Groq)
    - si la respuesta trae código/archivo, el backend lo guarda de verdad
    """
    import re
    from pathlib import Path

    if dept_id not in DEPARTMENTS:
        return {"success": False, "error": f"Departamento desconocido: {dept_id}"}

    llm = get_llm(dept_id=dept_id) if "dept_id" in get_llm.__code__.co_varnames else get_llm()
    llm_assistant = get_llm(temperature=0.2) if "dept_id" in get_llm.__code__.co_varnames else get_llm(temperature=0.2)

    try:
        boss, members, info = create_department_agents(dept_id, tools=[], llm=llm)
    except TypeError:
        boss, members, info = create_department_agents(dept_id, tools=[], llm=llm)

    assistant = create_assistant(llm=llm_assistant)

    if on_event:
        on_event({
            "type": "status",
            "department": dept_id,
            "message": f"{info['name']}: trabajando..."
        })

    work_task = Task(
        description=(
            f"Eres el jefe de {info['name']} ({info['boss']}). "
            f"Especialidad: {info['focus']}.\n\n"
            f"Tarea del usuario:\n{task_text}\n\n"
            "Responde en español de forma clara y útil.\n"
            "Si te piden crear código o un archivo, incluye el contenido completo "
            "dentro de un bloque markdown así:\n"
            "```python\n"
            "# archivo: nombre.py\n"
            "código aquí\n"
            "```\n"
            "o con el lenguaje que corresponda (javascript, html, markdown, etc.).\n"
            "Pon siempre en la primera línea del bloque: # archivo: nombre.ext"
        ),
        expected_output="Respuesta clara. Si hay archivos, código en bloques markdown con # archivo: nombre.ext",
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

        # --- Guardar archivos reales desde bloques de código ---
        workspace = Path(__file__).parent.parent / "workspace" / "shared"
        workspace.mkdir(parents=True, exist_ok=True)
        saved_files = []

        # Busca bloques ```lang ... ```
        blocks = re.findall(r"```(\w+)?\n(.*?)```", result_text, re.DOTALL)
        for i, (lang, content) in enumerate(blocks):
            content = content.strip()
            filename = None

            # Primera línea tipo: # archivo: hola.py
            first_line = content.split("\n", 1)[0].strip()
            m = re.search(r"#\s*archivo:\s*([^\s]+)", first_line, re.IGNORECASE)
            if m:
                filename = m.group(1).strip()
                # Quitar esa línea del contenido
                parts = content.split("\n", 1)
                content = parts[1].strip() if len(parts) > 1 else ""
            else:
                ext = {
                    "python": "py", "py": "py",
                    "javascript": "js", "js": "js",
                    "html": "html", "css": "css",
                    "markdown": "md", "md": "md",
                    "json": "json", "txt": "txt",
                }.get((lang or "").lower(), "txt")
                filename = f"entregable_{dept_id}_{i+1}.{ext}"

            # Seguridad: solo nombre de archivo, sin rutas
            filename = Path(filename).name
            path = workspace / filename
            path.write_text(content, encoding="utf-8")
            saved_files.append(filename)

        # También guardar el informe completo como .md
        report_name = f"informe_{dept_id}.md"
        (workspace / report_name).write_text(result_text, encoding="utf-8")
        if report_name not in saved_files:
            saved_files.append(report_name)

        file_entry = save_outgoing_file(
            filename=report_name,
            content=result_text,
            department=info["name"],
            description=f"Resultado de: {task_text[:80]}"
        )

        if on_event:
            msg = f"{info['name']} terminó."
            if saved_files:
                msg += f" Archivos: {', '.join(saved_files)}"
            on_event({
                "type": "status",
                "department": dept_id,
                "message": msg
            })

        # Revisión Asistente
        review_task = Task(
            description=(
                f"Revisa este entregable de {info['name']}.\n"
                f"Tarea: {task_text}\n\n"
                f"Entregable:\n{result_text[:4000]}\n\n"
                "Responde SOLO: APROBADO - comentario  O  RECHAZADO - motivo"
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
                "filename": report_name,
            })

        final_text = result_text
        if saved_files:
            final_text += "\n\n📁 Archivos guardados:\n- " + "\n- ".join(saved_files)

        return {
            "success": True,
            "department": info["name"],
            "result": final_text,
            "file_id": file_entry["id"],
            "filename": report_name,
            "saved_files": saved_files,
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
