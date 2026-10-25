"""Place the payroll call through a Cartesia managed voice agent.

The agent (set up once in the Cartesia dashboard, see docs/CARTESIA.md) reads the case through the
get_case_summary webhook and records the result through log_call_outcome, both served by convex/http.ts.
This module only decides what the call is about and hands the agent the case id as a dynamic variable;
agents/voice/calls.py starts it and applies the demo redirect.

Env (all four needed, else the call is skipped and logged):
    CARTESIA_API_KEY         sk_car_...
    CARTESIA_AGENT_ID        the managed agent that makes the call
    CARTESIA_FROM_NUMBER_ID  a phone number on the Cartesia account
    PAYROLL_PHONE            who the request is for, E.164 (+14155550123)
Optional: CARTESIA_VERSION, CARTESIA_API_BASE (tests point it at a local stub),
    DEMO_CALL_NUMBER / DEMO_CALL_REDIRECT (agents/voice/calls.py): while the redirect is on, the
    payroll number travels with the call but only the demo phone rings.
"""
from __future__ import annotations

import os

import requests

from agents.voice.calls import CallError, missing_settings as _missing, place

DEFAULT_VERSION = "2026-08-14"
REQUIRED = ("CARTESIA_API_KEY", "CARTESIA_AGENT_ID", "CARTESIA_FROM_NUMBER_ID", "PAYROLL_PHONE")

__all__ = ["CallError", "REQUIRED", "call_variables", "dollars", "missing_settings", "place_call"]


def missing_settings() -> list[str]:
    missing = _missing("CARTESIA_AGENT_ID")
    if not os.environ.get("PAYROLL_PHONE"):
        missing.append("PAYROLL_PHONE")
    return [k for k in REQUIRED if k in missing]


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


def case_brief(case: dict, session=requests) -> str:
    """The same sentences get_case_summary serves, fetched over our own webhook.

    The voice agent is supposed to fetch these itself mid-call. When that does not work — and
    whether it works depends on a response contract Cartesia does not document publicly — the agent
    has no facts and says so, which ends the call. Sending the brief along as a dynamic variable
    means the call still carries the right figures even if the tool never answers.

    Deliberately read from the webhook rather than rebuilt here: one wording, one source, and
    nothing about what the agent says depends on which path delivered it. Returns "" on any
    failure, and the call goes ahead without it.
    """
    from agents.caseworker.rehearsal import site_url  # local: only needed when a call is placed
    token = os.environ.get("CARTESIA_TOOL_TOKEN", "")
    if not token:
        return ""
    try:
        resp = session.post(f"{site_url()}/cartesia/case-summary", json={"case_id": case["_id"]},
                            headers={"Authorization": f"Bearer {token}",
                                     "Content-Type": "application/json"}, timeout=15)
        if resp.status_code != 200:
            return ""
        body = resp.json()
        return body.get("result", "") if isinstance(body, dict) else str(body)
    except Exception:  # noqa: BLE001 - the call is worth placing without the brief
        return ""


def place_call(case: dict, profile: dict, paystubs: list[dict], session=requests) -> str:
    """Start one outbound call to payroll. Returns Cartesia's agent_call_id; raises CallError with a
    readable reason. While the demo redirect is on, DEMO_CALL_NUMBER rings instead of PAYROLL_PHONE."""
    missing = missing_settings()
    if missing:
        raise CallError(f"Cartesia not configured: set {', '.join(missing)}")
    variables = call_variables(case, profile, paystubs)
    brief = case_brief(case, session=session)
    if brief:
        variables["case_brief"] = brief
    call_id, _dialled = place(os.environ["PAYROLL_PHONE"], variables,
                              agent_env="CARTESIA_AGENT_ID", session=session)
    return call_id
