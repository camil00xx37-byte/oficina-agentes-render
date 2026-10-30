import os
import json
from typing import Type, Optional
from pydantic import BaseModel, Field
from crewai_tools import BaseTool
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload, MediaIoBaseDownload
import io

# ========== CONFIGURACIÓN ==========
SCOPES = ["https://www.googleapis.com/auth/drive"]

def get_drive_service():
    """Crea el servicio de Google Drive usando la Service Account."""
    try:
        # Leemos el JSON desde la variable de entorno
        sa_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
        if not sa_json:
            raise ValueError("Falta la variable GOOGLE_SERVICE_ACCOUNT_JSON")

        # Convertimos el string JSON a diccionario
        credentials_info = json.loads(sa_json)
        credentials = service_account.Credentials.from_service_account_info(
            credentials_info, scopes=SCOPES
        )
        service = build("drive", "v3", credentials=credentials)
        return service
    except Exception as e:
        raise Exception(f"Error al conectar con Google Drive: {e}")


def get_folder_id():
    folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
    if not folder_id:
        raise ValueError("Falta la variable GOOGLE_DRIVE_FOLDER_ID")
    return folder_id


# ========== INPUTS ==========
class ListDriveFilesInput(BaseModel):
    pass


class ReadDriveFileInput(BaseModel):
    filename: str = Field(..., description="Nombre exacto del archivo a leer en Google Drive")


class WriteDriveFileInput(BaseModel):
    filename: str = Field(..., description="Nombre del archivo a crear o sobrescribir")
    content: str = Field(..., description="Contenido completo del archivo (texto)")


# ========== TOOLS ==========
class ListDriveFilesTool(BaseTool):
    name: str = "list_drive_files"
    description: str = (
        "Lista todos los archivos que hay dentro de la carpeta compartida de Google Drive. "
        "Úsala para ver qué archivos existen antes de leer o escribir."
    )
    args_schema: Type[BaseModel] = ListDriveFilesInput

    def _run(self) -> str:
        try:
            service = get_drive_service()
            folder_id = get_folder_id()

            results = service.files().list(
                q=f"'{folder_id}' in parents and trashed=false",
                fields="files(id, name, mimeType, modifiedTime, size)",
                pageSize=50
            ).execute()

            files = results.get("files", [])
            if not files:
                return "La carpeta de Google Drive está vacía."

            lines = ["Archivos en Google Drive:"]
            for f in files:
                size = f.get("size", "—")
                lines.append(f"- {f['name']}  (id: {f['id']}, tamaño: {size})")
            return "\n".join(lines)
        except Exception as e:
            return f"❌ Error al listar archivos de Drive: {e}"


class ReadDriveFileTool(BaseTool):
    name: str = "read_drive_file"
    description: str = (
        "Lee el contenido de un archivo de texto que está en la carpeta de Google Drive. "
        "Pasa el nombre exacto del archivo."
    )
    args_schema: Type[BaseModel] = ReadDriveFileInput

    def _run(self, filename: str) -> str:
        try:
            service = get_drive_service()
            folder_id = get_folder_id()

            # Buscar el archivo por nombre dentro de la carpeta
            results = service.files().list(
                q=f"name='{filename}' and '{folder_id}' in parents and trashed=false",
                fields="files(id, name, mimeType)"
            ).execute()

            files = results.get("files", [])
            if not files:
                return f"❌ No se encontró el archivo '{filename}' en Google Drive."

            file_id = files[0]["id"]
            mime_type = files[0].get("mimeType", "")

            # Si es un Google Doc, exportamos como texto plano
            if "google-apps.document" in mime_type:
                request = service.files().export_media(fileId=file_id, mimeType="text/plain")
            else:
                request = service.files().get_media(fileId=file_id)

            buffer = io.BytesIO()
            downloader = MediaIoBaseDownload(buffer, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()

            content = buffer.getvalue().decode("utf-8")
            return content
        except Exception as e:
            return f"❌ Error al leer el archivo de Drive: {e}"


class WriteDriveFileTool(BaseTool):
    name: str = "write_drive_file"
    description: str = (
        "Crea o sobrescribe un archivo de texto en la carpeta de Google Drive. "
        "Úsala para guardar reportes, código, planes, lecciones, etc."
    )
    args_schema: Type[BaseModel] = WriteDriveFileInput

    def _run(self, filename: str, content: str) -> str:
        try:
            service = get_drive_service()
            folder_id = get_folder_id()

            # Verificar si el archivo ya existe
            results = service.files().list(
                q=f"name='{filename}' and '{folder_id}' in parents and trashed=false",
                fields="files(id)"
            ).execute()

            files = results.get("files", [])
            media = MediaIoBaseUpload(
                io.BytesIO(content.encode("utf-8")),
                mimetype="text/plain",
                resumable=True
            )

            if files:
                # Actualizar archivo existente
                file_id = files[0]["id"]
                service.files().update(
                    fileId=file_id,
                    media_body=media
                ).execute()
                return f"✅ Archivo actualizado en Google Drive: {filename}"
            else:
                # Crear nuevo archivo
                file_metadata = {
                    "name": filename,
                    "parents": [folder_id]
                }
                service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields="id"
                ).execute()
                return f"✅ Archivo creado en Google Drive: {filename}"
        except Exception as e:
            return f"❌ Error al escribir en Drive: {e}"


# ========== INSTANCIAS ==========
list_drive_files_tool = ListDriveFilesTool()
read_drive_file_tool = ReadDriveFileTool()
write_drive_file_tool = WriteDriveFileTool()
