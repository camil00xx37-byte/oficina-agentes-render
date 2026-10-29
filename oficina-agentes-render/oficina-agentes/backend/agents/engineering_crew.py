import os
import sys
from pathlib import Path

# Asegura que el directorio backend esté en el path
sys.path.insert(0, str(Path(__file__).parent.parent))

from crewai import Agent, Task, Crew, Process
from langchain_groq import ChatGroq
from dotenv import load_dotenv

from tools.web_search import web_search_tool
from tools.code_executor import code_executor_tool
from tools.file_tools import read_file_tool, write_file_tool, list_files_tool
from tools.memory_tool import add_lesson_tool, get_lessons_tool

load_dotenv()

# ========== MODELO ==========
def get_llm():
    model = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    return ChatGroq(
        model=model,
        api_key=os.getenv("GROQ_API_KEY"),
        temperature=0.3,
        max_tokens=4096,
    )


# ========== AGENTES ==========
def create_engineering_agents(llm):
    common_tools = [
        web_search_tool,
        code_executor_tool,
        read_file_tool,
        write_file_tool,
        list_files_tool,
        get_lessons_tool,
        add_lesson_tool,
    ]

    ivan = Agent(
        role="Jefe de Ingeniería",
        goal="Coordinar al equipo, asegurar calidad técnica y entregar soluciones sólidas y bien documentadas.",
        backstory=(
            "Eres Iván, jefe del departamento de Ingeniería de IA Market Agents. "
            "Tienes experiencia liderando equipos de desarrollo. Eres claro, orientado a resultados "
            "y te aseguras de que el equipo aprenda de cada error. Siempre revisas las lecciones "
            "anteriores antes de empezar una tarea nueva."
        ),
        verbose=True,
        allow_delegation=True,
        llm=llm,
        tools=common_tools,
    )

    nora = Agent(
        role="Ingeniera de Software Senior",
        goal="Diseñar e implementar soluciones de código limpias, eficientes y bien estructuradas.",
        backstory=(
            "Eres Nora, ingeniera senior. Te especializas en arquitectura, buenas prácticas y "
            "código mantenible. Siempre pruebas lo que escribes y documentas decisiones importantes."
        ),
        verbose=True,
        allow_delegation=False,
        llm=llm,
        tools=common_tools,
    )

    sergio = Agent(
        role="Ingeniero de Automatización e Integraciones",
        goal="Crear automatizaciones, scripts y conexiones entre sistemas que ahorren tiempo al equipo.",
        backstory=(
            "Eres Sergio. Te encanta automatizar procesos repetitivos y conectar herramientas. "
            "Eres práctico y buscas la solución más simple que funcione de forma fiable."
        ),
        verbose=True,
        allow_delegation=False,
        llm=llm,
        tools=common_tools,
    )

    clara = Agent(
        role="Ingeniera de Calidad y Documentación",
        goal="Probar soluciones, encontrar fallos y generar documentación e informes claros.",
        backstory=(
            "Eres Clara. Te enfocas en calidad, pruebas y en que todo quede bien documentado. "
            "Generas reportes claros de lo que se hizo, qué funcionó y qué se puede mejorar."
        ),
        verbose=True,
        allow_delegation=False,
        llm=llm,
        tools=common_tools,
    )

    return ivan, nora, sergio, clara


# ========== CREW ==========
def run_engineering_task(task_description: str, on_event=None) -> dict:
    """
    Ejecuta una tarea real con el equipo de Ingeniería.
    on_event es una función opcional que recibe eventos para enviar al frontend.
    """
    llm = get_llm()
    ivan, nora, sergio, clara = create_engineering_agents(llm)

    # Tarea principal
    main_task = Task(
        description=(
            f"Tarea recibida del usuario / dirección:\n\n"
            f"{task_description}\n\n"
            "Instrucciones para el equipo:\n"
            "1. Primero consulta las lecciones aprendidas (get_lessons) para no repetir errores.\n"
            "2. Investiga lo necesario en internet si hace falta.\n"
            "3. Divide el trabajo entre los miembros del equipo de forma lógica.\n"
            "4. Escribe y prueba código cuando sea necesario.\n"
            "5. Guarda los entregables importantes con write_file.\n"
            "6. Al final, genera un informe claro de lo realizado, resultados y posibles mejoras.\n"
            "7. Si descubriste algo importante o corregiste un error, regístralo con add_lesson."
        ),
        expected_output=(
            "Un informe final estructurado que incluya:\n"
            "- Resumen de lo realizado\n"
            "- Archivos generados (si los hay)\n"
            "- Resultados de pruebas\n"
            "- Lecciones aprendidas en esta tarea\n"
            "- Recomendaciones"
        ),
        agent=ivan,
    )

    crew = Crew(
        agents=[ivan, nora, sergio, clara],
        tasks=[main_task],
        process=Process.hierarchical,  # Iván coordina
        manager_llm=llm,
        verbose=True,
    )

    if on_event:
        on_event({"type": "status", "message": "El equipo de Ingeniería está analizando la tarea..."})

    try:
        result = crew.kickoff()
        final_output = str(result)

        if on_event:
            on_event({
                "type": "completed",
                "message": "Tarea completada por el equipo de Ingeniería",
                "result": final_output
            })

        return {
            "success": True,
            "result": final_output,
            "agents_involved": ["Iván", "Nora", "Sergio", "Clara"]
        }
    except Exception as e:
        error_msg = f"Error en el equipo de Ingeniería: {str(e)}"
        if on_event:
            on_event({"type": "error", "message": error_msg})
        return {"success": False, "error": error_msg}