import json
from pathlib import Path
from datetime import datetime
from crewai.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field

MEMORY_FILE = Path(__file__).parent.parent / "memory" / "lessons.json"
MEMORY_FILE.parent.mkdir(exist_ok=True)


def _load_memory() -> list:
    if MEMORY_FILE.exists():
        try:
            return json.loads(MEMORY_FILE.read_text(encoding="utf-8"))
        except Exception:
            return []
    return []


def _save_memory(data: list):
    MEMORY_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


class AddLessonInput(BaseModel):
    lesson: str = Field(..., description="Lección aprendida o error que no se debe repetir")
    context: str = Field("", description="Contexto breve de cuándo ocurrió")


class GetLessonsInput(BaseModel):
    topic: str = Field("", description="Filtrar lecciones por tema (opcional)")


class AddLessonTool(BaseTool):
    name: str = "add_lesson"
    description: str = (
        "Guarda una lección aprendida o un error que el equipo no debe volver a cometer. "
        "Úsala siempre que descubras algo importante o corrijas un fallo."
    )
    args_schema: Type[BaseModel] = AddLessonInput

    def _run(self, lesson: str, context: str = "") -> str:
        data = _load_memory()
        entry = {
            "id": len(data) + 1,
            "lesson": lesson,
            "context": context,
            "date": datetime.now().isoformat(timespec="seconds"),
        }
        data.append(entry)
        _save_memory(data)
        return f"✅ Lección guardada (#{entry['id']}): {lesson}"


class GetLessonsTool(BaseTool):
    name: str = "get_lessons"
    description: str = (
        "Recupera las lecciones aprendidas del equipo. "
        "Úsala al empezar una tarea para no repetir errores anteriores."
    )
    args_schema: Type[BaseModel] = GetLessonsInput

    def _run(self, topic: str = "") -> str:
        data = _load_memory()
        if not data:
            return "Todavía no hay lecciones registradas."
        
        if topic:
            filtered = [d for d in data if topic.lower() in d["lesson"].lower() or topic.lower() in d.get("context", "").lower()]
            if not filtered:
                return f"No se encontraron lecciones relacionadas con '{topic}'."
            data = filtered

        lines = [f"#{d['id']} ({d['date'][:10]}): {d['lesson']}" for d in data[-15:]]  # últimas 15
        return "Lecciones del equipo de Ingeniería:\n" + "\n".join(lines)


add_lesson_tool = AddLessonTool()
get_lessons_tool = GetLessonsTool()