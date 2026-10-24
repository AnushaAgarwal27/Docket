"""Rehearsal mode: a stand-in payroll call that follows the case's rehearsal setting, with no phone.

Turn on with CARTESIA_SIMULATE=1. Instead of dialing through Cartesia, it plays the voice agent's two
webhook tools against our own Convex endpoints (convex/http.ts), so the whole path after the call
(state machine, written request, follow-up, dashboard) runs exactly as it would on a real call.

    first call:  cooperate -> promised | stall_once -> stalled | refuse_once -> refused
    later calls: promised

Needs CARTESIA_TOOL_TOKEN in .env (same value as on Convex). The webhook base is CONVEX_SITE_URL, or
CONVEX_URL with .convex.cloud -> .convex.site (a local backend's port 3210 -> 3211).
"""
from __future__ import annotations

import os
import threading
import time
import uuid
from datetime import date, timedelta

import requests

FIRST_CALL = {"cooperate": "promised", "stall_once": "stalled", "refuse_once": "refused"}
SAYS = {
    "promised": "Confirmed the F-1 status on file; will refund and stop withholding.",
    "stalled": "Said they would look into it but would not give a date.",
    "refused": "Said they cannot refund taxes already reported.",
}


def enabled() -> bool:
    return os.environ.get("CARTESIA_SIMULATE", "").strip().lower() in {"1", "true", "yes"}


def site_url() -> str:
    explicit = os.environ.get("CONVEX_SITE_URL")
    if explicit:
        return explicit.rstrip("/")
    url = os.environ["CONVEX_URL"].rstrip("/")
    if url.endswith(":3210"):
        return url[:-4] + "3211"
    return url.replace(".convex.cloud", ".convex.site")


def outcome_for(case: dict) -> str:
    attempt = case.get("callAttempts") or 1
    if attempt > 1:
        return "promised"
    return FIRST_CALL.get(case.get("payrollScript") or "cooperate", "promised")


def _tool(path: str, body: dict) -> tuple[int, str]:
    token = os.environ.get("CARTESIA_TOOL_TOKEN", "")
    r = requests.post(f"{site_url()}{path}", json=body, timeout=10, headers={"Authorization": f"Bearer {token}"})
    return r.status_code, r.text


def _play(case: dict, delay: float) -> None:
    time.sleep(delay)
    _tool("/cartesia/case-summary", {"case_id": case["_id"]})
    time.sleep(delay)
    result = outcome_for(case)
    body = {"case_id": case["_id"], "result": result, "answered_by": "Payroll office (rehearsal)", "summary": SAYS[result]}
    if result == "promised":
        body |= {"promised_by": (date.today() + timedelta(days=14)).isoformat(), "reference_number": "PR-REHEARSAL"}
    _tool("/cartesia/call-outcome", body)


def start(case: dict, delay: float = 1.5) -> str:
    """Start a simulated call in the background; returns a call id for the activity log."""
    threading.Thread(target=_play, args=(case, delay), daemon=True).start()
    return f"rehearsal-{uuid.uuid4().hex[:8]}"
