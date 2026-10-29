from duckduckgo_search import DDGS
from crewai.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field


class WebSearchInput(BaseModel):
    query: str = Field(..., description="La consulta de búsqueda en internet")


class WebSearchTool(BaseTool):
    name: str = "web_search"
    description: str = (
        "Busca información actualizada en internet. "
        "Úsala cuando necesites datos recientes, documentación, ejemplos de código, "
        "mejores prácticas o investigar un tema técnico."
    )
    args_schema: Type[BaseModel] = WebSearchInput

    def _run(self, query: str) -> str:
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=6))
            if not results:
                return "No se encontraron resultados relevantes."
            
            formatted = []
            for i, r in enumerate(results, 1):
                formatted.append(
                    f"{i}. {r.get('title', 'Sin título')}\n"
                    f"   {r.get('body', '')[:280]}...\n"
                    f"   Fuente: {r.get('href', '')}"
                )
            return "\n\n".join(formatted)
        except Exception as e:
            return f"Error en la búsqueda: {str(e)}"


web_search_tool = WebSearchTool()