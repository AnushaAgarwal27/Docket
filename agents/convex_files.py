"""Upload a file to Convex file storage and link it to a paystub or flag, from any agent.

Convex's upload is two steps: a mutation hands out a short-lived upload URL, the bytes are POSTed
there, and the response carries the storageId; files:attach then records the row. The Python client
has no upload helper, so the POST goes through requests. Every upload, and every failure, is logged
to activity.
"""
from __future__ import annotations

from pathlib import Path

import requests

from agents.store import log, mutation

UPLOAD_TIMEOUT = 30


def upload_and_attach(path: Path, kind: str, content_type: str = "application/pdf", *, agent: str,
                      data: bytes | None = None, **links: str) -> str | None:
    """Uploads `path` (or `data`, named after `path`) and attaches it as `kind` with `links`
    (paystubId=..., flagId=...). Returns the files row id, or None if anything failed."""
    filename = Path(path).name
    linked = [v for v in links.values() if v]
    try:
        upload_url = mutation("files:generateUploadUrl")
        body = data if data is not None else Path(path).read_bytes()
        resp = requests.post(upload_url, data=body, headers={"Content-Type": content_type}, timeout=UPLOAD_TIMEOUT)
        resp.raise_for_status()
        storage_id = resp.json()["storageId"]
        file_id = mutation("files:attach", {"storageId": storage_id, "kind": kind, "filename": filename, **links})
    except Exception as e:  # noqa: BLE001 - any failure is logged, never raised into the agent loop
        try:
            log(agent, "file_upload_failed", f"{kind} {filename}: {e}"[:300], inputIds=linked)
        except Exception:
            pass  # Convex itself is unreachable; the agent's own logger has the error
        return None
    log(agent, "file_uploaded", f"{kind} {filename}", inputIds=linked, outputIds=[file_id])
    return file_id
