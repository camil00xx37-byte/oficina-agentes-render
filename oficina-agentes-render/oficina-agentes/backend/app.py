import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from crewai import Agent, Task, Crew, Process
from crewai_tools import DuckDuckGoSearchTool
from langchain_groq import ChatGroq
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# 1. Configurar la Herramienta de Búsqueda (Autonomía para investigar)
search_tool = DuckDuckGoSearchTool()

# 2. Configurar el Modelo (Groq)
# Asegúrate de tener GROQ_API_KEY en las variables de entorno de Render
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

llm = ChatGroq(
    temperature=0.5,
    groq_api_key=GROQ_API_KEY,
    model_name="llama3-70b-8192"
)

class TareaRequest(BaseModel):
    tema: str

@app.get("/")
def read_root():
    return {"status": "Agentes listos", "motor": "Groq Llama 3"}

@app.post("/ejecutar")
async def ejecutar_agentes(request: TareaRequest):
    try:
        # 3. Definir el Agente con capacidad de búsqueda
        investigador = Agent(
            role='Investigador de Mercado',
            goal=f'Encontrar las últimas noticias y datos reales sobre {request.tema}',
            backstory="""Eres un experto analista digital. Tu especialidad es navegar 
            por la web buscando información veraz y actualizada para tomar decisiones.""",
            tools=[search_tool], # AQUÍ ESTÁ LA AUTONOMÍA DE ACCIÓN
            verbose=True,
            llm=llm,
            allow_delegation=False
        )

        escritor = Agent(
            role='Estratega de Contenido',
            goal=f'Redactar un informe ejecutivo basado en la investigación de {request.tema}',
            backstory="""Eres un experto en comunicación. Tomas datos crudos y los 
            conviertes en estrategias accionables y reportes profesionales.""",
            verbose=True,
            llm=llm,
            allow_delegation=False
        )

        # 4. Definir las Tareas
        tarea_busqueda = Task(
            description=f"Busca en internet los 3 eventos más importantes recientes sobre {request.tema}.",
            agent=investigador,
            expected_output="Un informe con fuentes y puntos clave encontrados en la web."
        )

        tarea_escritura = Task(
            description=f"Crea un resumen ejecutivo para un jefe basado en la investigación.",
            agent=escritor,
            expected_output="Un documento de texto profesional con introducción, nudo y conclusiones."
        )

        # 5. Ejecutar el equipo
        crew = Crew(
            agents=[investigador, escritor],
            tasks=[tarea_busqueda, tarea_escritura],
            process=Process.sequential
        )

        resultado = crew.kickoff()

        return {
            "resultado": str(resultado)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
