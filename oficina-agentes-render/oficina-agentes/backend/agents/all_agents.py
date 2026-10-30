"""
Configuración de TODOS los agentes de la oficina.
La Asistente tiene autoridad superior: revisa y aprueba casi todo antes de que llegue al usuario.
"""
import os
from crewai import Agent
from langchain_groq import ChatGroq
from dotenv import load_dotenv

load_dotenv()


def get_llm(temperature: float = 0.3, dept_id: str = None):
    """
    Devuelve un LLM. Si pasas dept_id, usa un modelo distinto por departamento.
    """
    # Modelos por departamento (Groq – activos en free/developer)
    MODEL_BY_DEPT = {
        "ing":  "groq/openai/gpt-oss-120b",   # Ingeniería → más potente
        "mkt":  "groq/openai/gpt-oss-20b",    # Marketing → rápido/creativo
        "dis":  "groq/qwen/qwen3.8-27b",      # Diseño → estilo
        "ops":  "groq/openai/gpt-oss-20b",
        "rrhh": "groq/openai/gpt-oss-20b",
        "cont": "groq/openai/gpt-oss-20b",
        "adm":  "groq/openai/gpt-oss-20b",
    }

    # Asistente / por defecto
    default_model = os.getenv("GROQ_MODEL", "groq/openai/gpt-oss-20b")
    model = MODEL_BY_DEPT.get(dept_id, default_model) if dept_id else default_model

    # Por si alguien pone el modelo sin el prefijo groq/
    if model and "/" not in model:
        model = f"groq/{model}"

    return ChatGroq(
        model=model,
        api_key=os.getenv("GROQ_API_KEY"),
        temperature=temperature,
        max_tokens=4096,
    )

# ============================================================
#  ASISTENTE (Dirección) – Poder superior
# ============================================================
ef create_assistant(llm=None):
    llm = llm or get_llm(temperature=0.2)  # Asistente usa el default (puedes poner gpt-oss-120b si quieres)
    return Agent(
        role="Asistente de Dirección",
        goal=(
            "Ser el filtro de calidad y el punto de control de toda la oficina. "
            "Revisar entregables de los departamentos, aprobar o rechazar con criterio, "
            "coordinar reuniones y asegurar que solo llegue al usuario trabajo de calidad."
        ),
        backstory=(
            "Eres la Asistente de Dirección de IA Market Agents. "
            "Tienes autoridad superior a los jefes de departamento. "
            "Nada importante llega al usuario sin tu revisión previa. "
            "Eres exigente pero justa, clara y profesional. "
            "Cuando un entregable está mal, lo rechazas con feedback concreto. "
            "Cuando está bien, lo apruebas y lo presentas de forma ordenada."
        ),
        verbose=True,
        allow_delegation=False,
        llm=llm,
    )


# ============================================================
#  DEPARTAMENTOS
# ============================================================
DEPARTMENTS = {
    "ing": {
        "name": "Ingeniería",
        "color": "#8a63d2",
        "boss": "Iván",
        "members": ["Nora", "Sergio", "Clara"],
        "focus": "código, automatizaciones, sistemas, pruebas técnicas",
    },
    "mkt": {
        "name": "Marketing",
        "color": "#3a86ff",
        "boss": "Marco",
        "members": ["Sofía", "Camila", "Esteban"],
        "focus": "campañas, redes, contenido, análisis de audiencia",
    },
    "dis": {
        "name": "Diseño creativo",
        "color": "#ff6b8a",
        "boss": "Lía",
        "members": ["Tomás", "Valeria", "Bruno"],
        "focus": "diseño visual, portadas, identidad, piezas gráficas",
    },
    "ops": {
        "name": "Operaciones",
        "color": "#2bb3a3",
        "boss": "Raúl",
        "members": ["Inés", "Diego", "Marta"],
        "focus": "procesos, logística, proveedores, entregas",
    },
    "rrhh": {
        "name": "Recursos humanos",
        "color": "#e36bd1",
        "boss": "Paula",
        "members": ["Andrés", "Lucía", "Fabián"],
        "focus": "equipo, horarios, bienestar, selección",
    },
    "cont": {
        "name": "Contabilidad",
        "color": "#f4b942",
        "boss": "Ada",
        "members": ["Hugo", "Rosa", "Gabriel"],
        "focus": "facturas, presupuestos, reportes financieros, impuestos",
    },
    "adm": {
        "name": "Administrativo",
        "color": "#6c8cff",
        "boss": "Elena",
        "members": ["Mateo", "Julia", "Pablo"],
        "focus": "documentos, agenda, trámites, organización",
    },
}


def create_department_agents(dept_id: str, tools: list = None, llm=None):
    """Crea el jefe + 3 agentes de un departamento."""
    llm = llm or get_llm(dept_id=dept_id)
    tools = tools or []
    info = DEPARTMENTS[dept_id]

    boss = Agent(
        role=f"Jefe de {info['name']}",
        goal=f"Liderar el departamento de {info['name']} y entregar trabajo de alta calidad en: {info['focus']}.",
        backstory=(
            f"Eres {info['boss']}, jefe de {info['name']} en IA Market Agents. "
            f"Coordinas a tu equipo, revisas su trabajo y te aseguras de que todo "
            f"esté listo antes de enviarlo a la Asistente de Dirección para su aprobación."
        ),
        verbose=True,
        allow_delegation=False,
        llm=llm,
        tools=tools,
    )

    members = []
    roles = [
        f"Especialista senior de {info['name']}",
        f"Especialista de {info['name']}",
        f"Analista / apoyo de {info['name']}",
    ]
    for i, name in enumerate(info["members"]):
        members.append(Agent(
            role=roles[i],
            goal=f"Ejecutar tareas de {info['name']} con calidad y reportar al jefe.",
            backstory=(
                f"Eres {name}, miembro del equipo de {info['name']}. "
                f"Trabajas de forma autónoma pero siempre alineado con las indicaciones de {info['boss']}."
            ),
            verbose=True,
            allow_delegation=False,
            llm=llm,
            tools=tools,
        ))

    return boss, members, info


def get_department_ids():
    return list(DEPARTMENTS.keys())
