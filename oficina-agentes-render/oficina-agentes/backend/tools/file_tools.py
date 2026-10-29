import os
from pathlib import Path
from crewai_tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field

# Carpeta segura donde los agentes pueden leer/escribir
WORKSPACE = Path(__file__).parent.parent / "workspace" / "shared"
WORKSPACE.mkdir(exist_ok=True)


class ReadFileInput(BaseModel):
    filename: str = Field(..., description="Nombre del archivo a leer (solo dentro del workspace)")


class WriteFileInput(BaseModel):
    filename: str = Field(..., description="Nombre del archivo a crear o sobrescribir")
    content: str = Field(..., description="Contenido completo del archivo")


class ListFilesInput(BaseModel):
    pass


class ReadFileTool(BaseTool):
    name: str = "read_file"
    description: str = "Lee el contenido de un archivo del workspace del equipo de Ingeniería."
    args_schema: Type[BaseModel] = ReadFileInput

    def _run(self, filename: str) -> str:
        try:
            path = (WORKSPACE / filename).resolve()
            if not str(path).startswith(str(WORKSPACE.resolve())):
                return "❌ Acceso denegado: solo se puede leer dentro del workspace."
            if not path.exists():
                return f"❌ El archivo '{filename}' no existe."
            return path.read_text(encoding="utf-8")
        except Exception as e:
            return f"❌ Error al leer: {e}"


class WriteFileTool(BaseTool):
    name: str = "write_file"
    description: str = (
        "Crea o sobrescribe un archivo en el workspace. "
        "Úsala para guardar código, reportes, planes o cualquier entregable."
    )
    args_schema: Type[BaseModel] = WriteFileInput

    def _run(self, filename: str, content: str) -> str:
        try:
            path = (WORKSPACE / filename).resolve()
            if not str(path).startswith(str(WORKSPACE.resolve())):
                return "❌ Acceso denegado."
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            return f"✅ Archivo guardado: {filename} ({len(content)} caracteres)"
        except Exception as e:
            return f"❌ Error al escribir: {e}"


class ListFilesTool(BaseTool):
    name: str = "list_files"
    description: str = "Lista todos los archivos disponibles en el workspace del equipo."
    args_schema: Type[BaseModel] = ListFilesInput

    def _run(self) -> str:
        files = list(WORKSPACE.rglob("*"))
        files = [f.relative_to(WORKSPACE) for f in files if f.is_file()]
        if not files:
            return "El workspace está vacío."
        return "Archivos en el workspace:\n" + "\n".join(f"- {f}" for f in sorted(files))


read_file_tool = ReadFileTool()
write_file_tool = WriteFileTool()
list_files_tool = ListFilesTool()
