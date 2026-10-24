"""Place the payroll call through a Cartesia managed voice agent.

The agent (set up once in the Cartesia dashboard, see docs/CARTESIA.md) reads the case through the
get_case_summary webhook and records the result through log_call_outcome, both served by convex/http.ts.
This module only starts the call and hands the agent the case id as a dynamic variable.

Env (all four needed, else the call is skipped and logged):
    CARTESIA_API_KEY         sk_car_...
    CARTESIA_AGENT_ID        the managed agent that makes the call
    CARTESIA_FROM_NUMBER_ID  a phone number on the Cartesia account
    PAYROLL_PHONE            who to call, E.164 (+14155550123). For the demo: the teammate playing payroll.
Optional: CARTESIA_VERSION (default below), CARTESIA_API_BASE (tests point it at a local stub).
"""
from __future__ import annotations

import os
import re

import requests

DEFAULT_VERSION = "2026-08-14"
REQUIRED = ("CARTESIA_API_KEY", "CARTESIA_AGENT_ID", "CARTESIA_FROM_NUMBER_ID", "PAYROLL_PHONE")
E164 = re.compile(r"^\+[1-9]\d{7,14}$")


class CallError(RuntimeError):
    pass


def missing_settings() -> list[str]:
    return [k for k in REQUIRED if not os.environ.get(k)]


def dollars(cents: int) -> str:
    return f"${cents // 100:,}.{cents % 100:02d}"


def call_variables(case: dict, profile: dict, paystubs: list[dict]) -> dict:
    """Dynamic variables for the agent's prompt and webhook bodies. Text only; numbers are pre-formatted in code."""
    return {
        "case_id": case["_id"],
        "student_name": profile["name"],
        "employer": paystubs[0]["employer"] if paystubs else "the employer",
        "refund_amount": dollars(case["amountCents"]),
        "paycheck_count": str(len(paystubs)),
    }


def place_call(case: dict, profile: dict, paystubs: list[dict], session=requests) -> str:
    """Start one outbound call. Returns Cartesia's agent_call_id; raises CallError with a readable reason."""
    missing = missing_settings()
    if missing:
        raise CallError(f"Cartesia not configured: set {', '.join(missing)}")
    to_number = os.environ["PAYROLL_PHONE"].replace(" ", "").replace("-", "")
    if not E164.match(to_number):
        raise CallError(f"PAYROLL_PHONE must be E.164 like +14155550123, got {os.environ['PAYROLL_PHONE']!r}")
    key = os.environ["CARTESIA_API_KEY"]
    base = os.environ.get("CARTESIA_API_BASE", "https://api.cartesia.ai").rstrip("/")
    body = {
        "agent_id": os.environ["CARTESIA_AGENT_ID"],
        "from_number_id": os.environ["CARTESIA_FROM_NUMBER_ID"],
        "ringing_timeout_seconds": 45,
        "outbound_calls": [{"to_number": to_number, "dynamic_variables": call_variables(case, profile, paystubs)}],
    }
    headers = {
        # Cartesia's docs show both header styles depending on the page; sending both is harmless.
        "X-API-Key": key,
        "Authorization": f"Bearer {key}",
        "Cartesia-Version": os.environ.get("CARTESIA_VERSION", DEFAULT_VERSION),
        "Content-Type": "application/json",
    }
    try:
        resp = session.post(f"{base}/agents/calls", json=body, headers=headers, timeout=20)
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
    return first["agent_call_id"]
