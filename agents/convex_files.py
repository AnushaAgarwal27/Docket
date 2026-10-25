"""Store PDFs beside SQLite and attach them to findings. Historical module name kept for agent imports."""
from __future__ import annotations

from pathlib import Path


from agents.store import log, mutation


def upload_and_attach(path: Path, kind: str, content_type: str = "application/pdf", *, agent: str,
                      data: bytes | None = None, **links: str) -> str | None:
    """Uploads `path` (or `data`, named after `path`) and attaches it as `kind` with `links`
    (paystubId=..., flagId=...). Returns the files row id, or None if anything failed."""
    filename = Path(path).name
    linked = [v for v in links.values() if v]
    try:
        from backend.store import files_path
        import uuid
        body = data if data is not None else Path(path).read_bytes()
        storage_id = uuid.uuid4().hex
        (files_path() / storage_id).write_bytes(body)
        file_id = mutation("files:attach", {"storageId": storage_id, "kind": kind, "filename": filename, **links})
    except Exception as e:  # noqa: BLE001 - any failure is logged, never raised into the agent loop
        try:
            log(agent, "file_upload_failed", f"{kind} {filename}: {e}"[:300], inputIds=linked)
        except Exception:
            pass  # Convex itself is unreachable; the agent's own logger has the error
        return None
    log(agent, "file_uploaded", f"{kind} {filename}", inputIds=linked, outputIds=[file_id])
    return file_id
