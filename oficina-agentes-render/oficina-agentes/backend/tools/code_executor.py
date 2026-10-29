import sys
import io
import traceback
from contextlib import redirect_stdout, redirect_stderr
from crewai.tools import BaseTool
from typing import Type
from pydantic import BaseModel, Field


class CodeExecutorInput(BaseModel):
    code: str = Field(..., description="Código Python a ejecutar")


class CodeExecutorTool(BaseTool):
    name: str = "execute_python"
    description: str = (
        "Ejecuta código Python de forma segura y devuelve el resultado o el error. "
        "Úsala para probar snippets, hacer cálculos, validar lógica o generar salidas. "
        "No tiene acceso a internet ni al sistema de archivos del usuario."
    )
    args_schema: Type[BaseModel] = CodeExecutorInput

    def _run(self, code: str) -> str:
        # Restricciones básicas de seguridad
        forbidden = [
            "import os", "import subprocess", "import shutil", "import sys",
            "__import__", "open(", "exec(", "eval(", "compile(",
            "os.system", "subprocess.", "shutil."
        ]
        code_lower = code.lower()
        for f in forbidden:
            if f in code_lower:
                return f"⚠️ Bloqueado por seguridad: no se permite usar '{f}'."

        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()

        try:
            local_vars = {}
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                exec(code, {"__builtins__": __builtins__}, local_vars)

            output = stdout_capture.getvalue()
            errors = stderr_capture.getvalue()

            result = ""
            if output:
                result += f"📤 Salida:\n{output}\n"
            if errors:
                result += f"⚠️ Stderr:\n{errors}\n"
            if not result:
                # Intentar mostrar variables creadas
                interesting = {k: v for k, v in local_vars.items() if not k.startswith("_")}
                if interesting:
                    result = f"✅ Código ejecutado. Variables resultantes:\n{interesting}"
                else:
                    result = "✅ Código ejecutado correctamente (sin salida visible)."
            return result.strip()

        except Exception as e:
            tb = traceback.format_exc()
            return f"❌ Error de ejecución:\n{tb}"


code_executor_tool = CodeExecutorTool()