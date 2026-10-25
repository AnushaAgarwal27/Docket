"""Record what payroll said by reading Cartesia's own call record, not by waiting to be told.

The voice agent is supposed to report the outcome itself through the log_call_outcome webhook.
When that does not arrive — a mistyped tool URL, a dropped request, the other side hanging up a
beat early — the call still happened, payroll still answered, and the promise is still real. It is
simply lost, and the case sits in contacting_employer forever.

Cartesia keeps a record of every call with a written summary of what was agreed:

    "The representative confirmed the refund will be issued on November 16th with no reference
     number, and agreed to stop future withholding."

So this reads that record and records the outcome from our side. The call id is already on the
case (callRequestId), and the case id is on the call's own dynamic variables, so the two can be
matched without guessing.

Claude turns the summary into one of the four outcomes; code decides everything that follows. The
result must be one of the four the state machine accepts, a date must parse as a real date before
it is stored, and anything Claude is unsure of becomes "stalled", which is the outcome that asks a
human to follow up rather than claiming a promise nobody made. Overstating a refund date is the one
error here that would actually hurt the student.
"""
from __future__ import annotations

import os
import re
from datetime import date
from typing import Literal

import requests
from pydantic import BaseModel

from agents.store import log, mutation, query

AGENT = "caseworker"
API = "https://api.cartesia.ai"
MODEL = "claude-opus-5"

Result = Literal["promised", "stalled", "refused", "needs_student"]

SYSTEM = """You read the summary of a phone call that an AI assistant made to an employer's payroll
office, asking for a refund of tax withheld in error from a student's pay. Report what payroll
actually said.

- promised: payroll agreed to refund it.
- stalled: payroll will look into it but did not commit.
- refused: payroll said no.
- needs_student: payroll needs to speak to the student directly, or needs documents from her.

Rules:
- Report only what the summary says. If it does not say payroll agreed, the answer is not promised.
- promised_by: only a date payroll actually gave. Format YYYY-MM-DD. Null if none was given.
  The call happened on the date you are told; a bare "November 16th" means the next November 16th
  on or after that date.
- reference_number: only if one was given. Null otherwise. "No reference number" means null.
- If the summary is unclear or the call did not reach payroll, answer stalled with a null date.
  A wrong promise is worse than an uncertain one: the student would stop chasing it."""


class Outcome(BaseModel):
    result: Result
    summary: str
    answered_by: str | None
    promised_by: str | None
    reference_number: str | None


def headers() -> dict[str, str]:
    key = os.environ["CARTESIA_API_KEY"]
    return {"Authorization": f"Bearer {key}", "X-API-Key": key,
            "Cartesia-Version": os.environ.get("CARTESIA_VERSION", "2026-08-14")}


def recent_calls(limit: int = 20, session=requests) -> list[dict]:
    """Cartesia's record of this agent's recent calls, newest first."""
    agent_id = os.environ.get("CARTESIA_AGENT_ID", "")
    if not agent_id:
        return []
    try:
        r = session.get(f"{API}/agents/calls", params={"agent_id": agent_id, "limit": limit},
                        headers=headers(), timeout=25)
        r.raise_for_status()
    except Exception:  # noqa: BLE001 - nothing to record if we cannot read
        return []
    return (r.json() or {}).get("data") or []


def classify(summary: str, call_day: date) -> Outcome | None:
    """Claude reads the summary; the checks below decide what is stored."""
    import anthropic
    try:
        response = anthropic.Anthropic().messages.parse(
            model=MODEL,
            max_tokens=4000,
            output_config={"effort": "low"},
            system=SYSTEM,
            messages=[{"role": "user", "content":
                       f"The call happened on {call_day.isoformat()}.\n\nSummary:\n{summary}"}],
            output_format=Outcome,
        )
    except Exception as e:  # noqa: BLE001
        log(AGENT, "call_record_unreadable", f"Could not read the call summary: {e}"[:300])
        return None
    return response.parsed_output


def valid_date(value: str | None, on_or_after: date) -> str | None:
    """A promised date is stored only if it is a real date and not in the past. Payroll cannot
    promise a refund for last week, and a misread date would set a follow-up that never fires."""
    if not value or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return None
    try:
        parsed = date.fromisoformat(value)
    except ValueError:
        return None
    return value if parsed >= on_or_after else None


def record_finished_calls(session=requests) -> int:
    """Record any completed call whose outcome never arrived. Returns how many were recorded."""
    recorded = 0
    for call in recent_calls(session=session):
        if call.get("status") != "completed":
            continue
        case_id = (call.get("dynamic_variables") or {}).get("case_id")
        if not case_id:
            continue
        # Re-read the case per call rather than from a snapshot taken up front. Several calls can
        # share one case — every redial during a rehearsal does — and recording the first moves it
        # out of contacting_employer. A stale snapshot would let the rest through, each one
        # re-recording the same outcome.
        case = query("cases:get", {"caseId": case_id})
        if case is None or case["state"] != "contacting_employer":
            continue  # no such case, or its outcome is already recorded
        summary = (call.get("summary") or "").strip()
        if not summary:
            continue
        call_day = date.fromisoformat(call["start_time"][:10])
        outcome = classify(summary, call_day)
        if outcome is None:
            continue

        promised = valid_date(outcome.promised_by, call_day)
        if outcome.result == "promised" and promised is None:
            # Payroll agreed but gave no usable date. That is still a promise; the case just needs
            # a human follow-up date rather than one we invented.
            log(AGENT, "call_outcome_no_date",
                f"Payroll agreed on call {call['id']} but gave no usable date", inputIds=[case_id])
        try:
            mutation("cases:logCallOutcome", {
                "caseId": case_id,
                "result": outcome.result,
                "summary": outcome.summary[:400],
                "answeredBy": outcome.answered_by or "Payroll office",
                **({"promisedBy": promised} if promised else {}),
                **({"referenceNo": outcome.reference_number} if outcome.reference_number else {}),
            })
        except Exception as e:  # noqa: BLE001
            log(AGENT, "call_outcome_rejected", f"Call {call['id']}: {e}"[:300], inputIds=[case_id])
            continue
        log(AGENT, "call_outcome_recovered",
            f"Recorded \"{outcome.result}\" for case {case_id} from Cartesia's record of call "
            f"{call['id']}, because the log_call_outcome webhook never arrived",
            inputIds=[case_id])
        recorded += 1
    return recorded
