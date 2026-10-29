"""
Sistema de archivos simplificado:
  workspace/shared/  → carpeta única compartida
  - Tú subes archivos aquí
  - Los agentes los leen y los modifican EN EL MISMO SITIO (sobrescriben)
  - La Asistente solo marca el estado (aprobado/rechazado) sin mover el archivo
"""
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict

BASE = Path(__file__).parent.parent / "workspace"
SHARED = BASE / "shared"
META_FILE = BASE / "files_meta.json"

SHARED.mkdir(parents=True, exist_ok=True)


def _load_meta() -> Dict:
    if META_FILE.exists():
        try:
            return json.loads(META_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def _save_meta(data: Dict):
    META_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _now():
    return datetime.now().isoformat(timespec="seconds")


def register_file(filename: str, uploaded_by: str = "usuario", department: str = "", description: str = "") -> dict:
    meta = _load_meta()
    file_id = str(uuid.uuid4())[:8]
    entry = {
        "id": file_id,
        "filename": filename,
        "path": str(SHARED / filename),
        "department": department,
        "uploaded_by": uploaded_by,
        "description": description,
        "status": "available",          # available | pending_assistant | approved | rejected
        "created_at": _now(),
        "updated_at": _now(),
        "reviewed_by": None,
        "review_comment": None,
    }
    meta[file_id] = entry
    _save_meta(meta)
    return entry


def list_files(status: Optional[str] = None) -> List[dict]:
    meta = _load_meta()
    files = list(meta.values())
    if status:
        files = [f for f in files if f["status"] == status]
    files.sort(key=lambda x: x.get("updated_at") or x.get("created_at", ""), reverse=True)
    return files


def get_file(file_id: str) -> Optional[dict]:
    return _load_meta().get(file_id)


def save_shared_file(filename: str, content, uploaded_by: str = "usuario", department: str = "", description: str = "") -> dict:
    """
    Guarda o sobrescribe un archivo en shared/.
    content puede ser str o bytes.
    """
    safe_name = Path(filename).name
    path = SHARED / safe_name
    if isinstance(content, bytes):
        path.write_bytes(content)
    else:
        path.write_text(str(content), encoding="utf-8")

    # Si ya existe en meta, actualizar; si no, registrar
    meta = _load_meta()
    existing = None
    for e in meta.values():
        if e["filename"] == safe_name:
            existing = e
            break

    if existing:
        existing["updated_at"] = _now()
        existing["status"] = "pending_assistant" if uploaded_by != "usuario" else existing.get("status", "available")
        existing["department"] = department or existing.get("department", "")
        if description:
            existing["description"] = description
        meta[existing["id"]] = existing
        _save_meta(meta)
        return existing
    else:
        return register_file(safe_name, uploaded_by=uploaded_by, department=department, description=description)


def assistant_review(file_id: str, approve: bool, comment: str = "", reviewer: str = "Asistente") -> dict:
    meta = _load_meta()
    entry = meta.get(file_id)
    if not entry:
        return {"success": False, "error": "Archivo no encontrado"}

    entry["status"] = "approved" if approve else "rejected"
    entry["reviewed_by"] = reviewer
    entry["reviewed_at"] = _now()
    entry["review_comment"] = comment
    entry["updated_at"] = _now()
    # NO movemos el archivo. Se queda en shared/
    meta[file_id] = entry
    _save_meta(meta)
    return {"success": True, "file": entry}


def user_final_decision(file_id: str, approve: bool, comment: str = "") -> dict:
    meta = _load_meta()
    entry = meta.get(file_id)
    if not entry:
        return {"success": False, "error": "Archivo no encontrado"}
    entry["user_decision"] = "accepted" if approve else "denied"
    entry["user_comment"] = comment
    entry["user_decided_at"] = _now()
    entry["updated_at"] = _now()
    meta[file_id] = entry
    _save_meta(meta)
    return {"success": True, "file": entry}


def get_pending_for_assistant() -> List[dict]:
    return list_files(status="pending_assistant")


def get_approved_for_user() -> List[dict]:
    return list_files(status="approved")


# Compatibilidad con nombres antiguos
def save_incoming_file(filename: str, content: bytes, description: str = "") -> dict:
    return save_shared_file(filename, content, uploaded_by="usuario", description=description)


def save_outgoing_file(filename: str, content: str, department: str, task_id: str = "", description: str = "") -> dict:
    return save_shared_file(filename, content, uploaded_by=department, department=department, description=description)


# Carpetas (para el endpoint de descarga)
INCOMING = SHARED
OUTGOING = SHARED
APPROVED = SHARED
REJECTED = SHARED
