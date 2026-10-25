"""Start one Cartesia call, to anyone, with the demo redirect applied.

Every outbound call in Docket goes through `place`. It does three things nothing else does:

  1. Applies the demo redirect. DEMO_CALL_NUMBER is the only phone that rings while
     DEMO_CALL_REDIRECT is on (it is on by default). The number the call is *about* still travels
     with the call as the `intended_number` variable, so the agent can say who it is calling for and
     the activity log records both. This is what keeps a research-found payroll or legal-aid number
     from being dialled by accident.

  2. Refuses to dial anything that is not E.164, before the request leaves the machine.

  3. Returns Cartesia's call id so the caller can tie the call to a case, a document or a student.

Env:
    CARTESIA_API_KEY            sk_car_...
    CARTESIA_FROM_NUMBER_ID     a phone number on the Cartesia account, used as the caller id
    DEMO_CALL_NUMBER            the only number that rings in demo mode (default below)
    DEMO_CALL_REDIRECT          0 to dial real numbers; anything else, or unset, keeps the redirect
Optional: CARTESIA_VERSION, CARTESIA_API_BASE (tests point it at a stub).
"""
from __future__ import annotations

import os
import re

import requests

DEFAULT_VERSION = "2026-08-14"
DEFAULT_DEMO_NUMBER = "+19259677432"
E164 = re.compile(r"^\+[1-9]\d{7,14}$")
RING_TIMEOUT_SECONDS = 45


class CallError(RuntimeError):
    pass


def normalise(number: str) -> str:
    """Strip the punctuation people write phone numbers with. Does not validate."""
    return re.sub(r"[\s\-().]", "", (number or "").strip())


def demo_number() -> str:
    return normalise(os.environ.get("DEMO_CALL_NUMBER") or DEFAULT_DEMO_NUMBER)


def redirecting() -> bool:
    """True while only the demo phone may ring. Off only with an explicit DEMO_CALL_REDIRECT=0."""
    return os.environ.get("DEMO_CALL_REDIRECT", "1").strip().lower() not in {"0", "false", "no"}


def destination(intended: str) -> tuple[str, str]:
    """(number that will ring, number the call is about). They differ while the demo redirect is on."""
    intended = normalise(intended)
    if not E164.match(intended):
        raise CallError(f"phone number must be E.164 like +14155550123, got {intended!r}")
    if not redirecting():
        return intended, intended
    dialled = demo_number()
    if not E164.match(dialled):
        raise CallError(f"DEMO_CALL_NUMBER must be E.164, got {dialled!r}")
    return dialled, intended


def missing_settings(agent_env: str = "CARTESIA_AGENT_ID") -> list[str]:
    """Which env vars still need setting before a call on this agent can be placed."""
    return [k for k in ("CARTESIA_API_KEY", agent_env, "CARTESIA_FROM_NUMBER_ID") if not os.environ.get(k)]


def headers(key: str) -> dict[str, str]:
    return {
        # Cartesia's docs show both header styles depending on the page; sending both is harmless.
        "X-API-Key": key,
        "Authorization": f"Bearer {key}",
        "Cartesia-Version": os.environ.get("CARTESIA_VERSION", DEFAULT_VERSION),
        "Content-Type": "application/json",
    }


def place(to_number: str, variables: dict[str, str], *, agent_env: str = "CARTESIA_AGENT_ID",
          session=requests) -> tuple[str, str]:
    """Start one outbound call. Returns (agent_call_id, the number that actually rang).

    `variables` are the agent's dynamic variables. `intended_number` is added for you.
    """
    missing = missing_settings(agent_env)
    if missing:
        raise CallError(f"Cartesia not configured: set {', '.join(missing)}")
    dialled, intended = destination(to_number)
    key = os.environ["CARTESIA_API_KEY"]
    base = os.environ.get("CARTESIA_API_BASE", "https://api.cartesia.ai").rstrip("/")
    body = {
        "agent_id": os.environ[agent_env],
        "from_number_id": os.environ["CARTESIA_FROM_NUMBER_ID"],
        "ringing_timeout_seconds": RING_TIMEOUT_SECONDS,
        "outbound_calls": [{
            "to_number": dialled,
            "dynamic_variables": {**{k: str(v) for k, v in variables.items()}, "intended_number": intended},
        }],
    }
    try:
        resp = session.post(f"{base}/agents/calls", json=body, headers=headers(key), timeout=20)
    except requests.RequestException as e:
        raise CallError(f"could not reach Cartesia: {e}") from e
    if resp.status_code >= 400:
        raise CallError(f"Cartesia returned {resp.status_code}: {resp.text[:300]}")
    calls = (resp.json() or {}).get("calls") or []
    if not calls:
        raise CallError(f"Cartesia returned no calls: {resp.text[:300]}")
    first = calls[0]
    if first.get("error") or not first.get("agent_call_id"):
        raise CallError(f"Cartesia did not start the call: {first.get('error') or first}")
    return first["agent_call_id"], dialled
