"""
Backend completo de la Oficina de Agentes.
- Todos los departamentos
- Flujo de archivos con aprobación de la Asistente
- Reuniones con informes
- WebSocket en tiempo real
"""
import os
import json
import asyncio
from typing import List, Optional
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

load_dotenv()

from agents.task_runner import run_department_task, run_meeting_reports
from agents.all_agents import DEPARTMENTS, get_department_ids
from tools.file_manager import (
    list_files, get_file, assistant_review, user_final_decision,
    get_pending_for_assistant, get_approved_for_user,
    save_incoming_file, INCOMING, OUTGOING, APPROVED, REJECTED
)

app = FastAPI(title="Oficina de Agentes – Backend completo")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Carpeta de archivos estáticos (frontend)
STATIC_DIR = Path(__file__).parent / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


class ConnectionManager:
    def __init__(self):
        self.active: List[WebSocket] = []

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)

    async def broadcast(self, data: dict):
        msg = json.dumps(data, ensure_ascii=False)
        dead = []
        for ws in self.active:
            try:
                await ws.send_text(msg)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


manager = ConnectionManager()


def _event_sender():
    def on_event(event: dict):
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.run_coroutine_threadsafe(manager.broadcast(event), loop)
        except Exception:
            pass
    return on_event


@app.get("/")
async def root():
    """Sirve la oficina 3D (frontend) o JSON de estado si no hay static."""
    index = STATIC_DIR / "index.html"
    if index.exists():
        return FileResponse(index, media_type="text/html")
    return {
        "status": "ok",
        "departments": list(DEPARTMENTS.keys()),
        "message": "Oficina de Agentes lista. La Asistente tiene autoridad de aprobación."
    }


@app.get("/api")
async def api_status():
    return {
        "status": "ok",
        "departments": list(DEPARTMENTS.keys()),
        "message": "Oficina de Agentes lista. La Asistente tiene autoridad de aprobación."
    }


@app.get("/health")
async def health():
    return {
        "status": "healthy" if os.getenv("GROQ_API_KEY") else "missing_api_key",
        "groq_configured": bool(os.getenv("GROQ_API_KEY")),
        "model": os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),
        "departments": get_department_ids(),
    }


@app.get("/departments")
async def departments():
    return {
        k: {"name": v["name"], "boss": v["boss"], "members": v["members"], "color": v["color"]}
        for k, v in DEPARTMENTS.items()
    }


@app.get("/files")
async def files(status: Optional[str] = None, direction: Optional[str] = None):
    return {"files": list_files(status=status, direction=direction)}


@app.get("/files/pending-assistant")
async def pending_assistant():
    return {"files": get_pending_for_assistant()}


@app.get("/files/approved")
async def approved_files():
    return {"files": get_approved_for_user()}


@app.post("/files/upload")
async def upload_file(file: UploadFile = File(...), description: str = Form("")):
    content = await file.read()
    entry = save_incoming_file(file.filename, content, description)
    await manager.broadcast({
        "type": "file_uploaded",
        "file": entry,
        "message": f"Archivo subido: {entry['filename']}"
    })
    return {"success": True, "file": entry}


@app.post("/files/{file_id}/assistant-review")
async def do_assistant_review(file_id: str, approve: bool = True, comment: str = ""):
    result = assistant_review(file_id, approve=approve, comment=comment)
    if result.get("success"):
        await manager.broadcast({
            "type": "assistant_review",
            "approved": approve,
            "file": result["file"],
            "message": f"Asistente {'aprobó' if approve else 'rechazó'}: {result['file']['filename']}"
        })
    return result


@app.post("/files/{file_id}/user-decision")
async def do_user_decision(file_id: str, approve: bool = True, comment: str = ""):
    result = user_final_decision(file_id, approve=approve, comment=comment)
    if result.get("success"):
        await manager.broadcast({
            "type": "user_decision",
            "approved": approve,
            "file": result["file"],
            "message": f"Usuario {'aceptó' if approve else 'denegó'}: {result['file']['filename']}"
        })
    return result


@app.get("/files/download/{folder}/{filename}")
async def download_file(folder: str, filename: str):
    folders = {
        "incoming": INCOMING,
        "outgoing": OUTGOING,
        "approved": APPROVED,
        "rejected": REJECTED,
    }
    if folder not in folders:
        return JSONResponse({"error": "Carpeta inválida"}, status_code=400)
    path = folders[folder] / filename
    if not path.exists():
        return JSONResponse({"error": "Archivo no encontrado"}, status_code=404)
    return FileResponse(path, filename=filename)


@app.post("/meeting/start")
async def start_meeting():
    result = await asyncio.get_event_loop().run_in_executor(
        None, lambda: run_meeting_reports(on_event=_event_sender())
    )
    await manager.broadcast({
        "type": "meeting_started",
        "report": result.get("report", ""),
        "message": "Reunión iniciada. Informe listo para la pantalla."
    })
    return result


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        await websocket.send_text(json.dumps({
            "type": "connected",
            "message": "Conectado. Asistente y departamentos listos.",
            "departments": get_department_ids(),
        }, ensure_ascii=False))

        while True:
            raw = await websocket.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({"type": "error", "message": "JSON inválido"}))
                continue

            msg_type = data.get("type")

            if msg_type == "task":
                text = (data.get("text") or "").strip()
                dept = data.get("department", "ing")
                if not text:
                    await websocket.send_text(json.dumps({"type": "error", "message": "Tarea vacía"}))
                    continue

                await manager.broadcast({
                    "type": "task_started",
                    "department": dept,
                    "text": text,
                    "message": f"Tarea enviada a {DEPARTMENTS.get(dept, {}).get('name', dept)}"
                })

                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None,
                    lambda: run_department_task(dept, text, on_event=_event_sender())
                )

                await manager.broadcast({
                    "type": "task_finished",
                    "department": dept,
                    "success": result.get("success", False),
                    "result": result.get("result") or result.get("error"),
                    "assistant_approved": result.get("assistant_approved"),
                    "file_id": result.get("file_id"),
                    "filename": result.get("filename"),
                    "assistant_comment": result.get("assistant_comment", "")[:500],
                })

            elif msg_type == "meeting":
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None,
                    lambda: run_meeting_reports(on_event=_event_sender())
                )
                await manager.broadcast({
                    "type": "meeting_report",
                    "report": result.get("report", ""),
                    "approved": result.get("approved", []),
                    "pending": result.get("pending", []),
                    "message": "Informe de reunión listo"
                })

            elif msg_type == "assistant_review":
                file_id = data.get("file_id")
                approve = data.get("approve", True)
                comment = data.get("comment", "")
                result = assistant_review(file_id, approve=approve, comment=comment)
                await manager.broadcast({
                    "type": "assistant_review",
                    "approved": approve,
                    "file": result.get("file"),
                    "message": result.get("error") or f"Asistente {'aprobó' if approve else 'rechazó'} el archivo"
                })

            elif msg_type == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))

            else:
                await websocket.send_text(json.dumps({
                    "type": "info",
                    "message": f"Tipo no reconocido: {msg_type}"
                }))

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print(f"WS error: {e}")
        manager.disconnect(websocket)


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=False)
