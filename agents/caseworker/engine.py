"""Caseworker: turn refund flags into cases with a draft request, and act on the student's approval.

State changes happen in convex/cases.ts so every caller obeys the same state machine.
"""

from agents.caseworker import cartesia
from agents.store import dollars, log, mutation, query

AGENT = "caseworker"


def draft_request(profile: dict, paystubs: list[dict], flag: dict) -> str:
    ss = sum(p["ssCents"] for p in paystubs)
    medicare = sum(p["medicareCents"] for p in paystubs)
    periods = sorted(p["periodStart"] for p in paystubs)
    last_end = max(p["periodEnd"] for p in paystubs)
    return (
        f"To {paystubs[0]['employer']} payroll:\n\n"
        f"This request is sent on behalf of {profile['name']}, with her permission, by Docket, an AI assistant. "
        f"{profile['name']} is a nonresident alien student in F-1 status. Social Security ({dollars(ss)}) and "
        f"Medicare ({dollars(medicare)}) taxes were withheld from {len(paystubs)} paychecks for pay periods "
        f"{periods[0]} to {last_end}, a total of {dollars(ss + medicare)}.\n\n"
        f"IRS Publication 519 states: \"{flag['quote']}\"\n\n"
        f"Please refund {dollars(ss + medicare)} and stop withholding these taxes from future paychecks. "
        f"If you cannot refund it, please provide a written statement saying so, so she can claim it from the IRS."
    )


def open_refund_cases(profile_id: str) -> list[dict]:
    """Open one case per refund flag that does not have one yet. Returns the cases awaiting approval."""
    profile = query("profiles:get", {"profileId": profile_id})
    paystubs = query("paystubs:listByProfile", {"profileId": profile_id})
    for flag in query("flags:listByProfile", {"profileId": profile_id}):
        if flag["ruleId"] != "FICA_EXEMPT_F1" or flag["status"] != "open":
            continue
        mutation("cases:open", {
            "flagId": flag["_id"],
            "profileId": profile_id,
            "amountCents": flag["amountCents"],
            "draft": draft_request(profile, paystubs, flag),
        })
    return awaiting_approval(profile_id)


def awaiting_approval(profile_id: str) -> list[dict]:
    return [c for c in query("cases:listByProfile", {"profileId": profile_id}) if c["state"] == "awaiting_approval"]


def request_call(case: dict) -> None:
    """Place the payroll call for an approved case, once. Safe to call from several places."""
    if not mutation("cases:claimCall", {"caseId": case["_id"]}):
        return  # already claimed by another trigger, or no longer contacting payroll
    missing = cartesia.missing_settings()
    if missing:
        mutation("cases:recordCallStart", {"caseId": case["_id"], "error": f"Cartesia not configured: set {', '.join(missing)}"})
        return
    profile = query("profiles:get", {"profileId": case["profileId"]})
    paystubs = query("paystubs:listByProfile", {"profileId": case["profileId"]})
    try:
        call_id = cartesia.place_call(case, profile, paystubs)
    except cartesia.CallError as e:
        mutation("cases:recordCallStart", {"caseId": case["_id"], "error": str(e)})
        return
    mutation("cases:recordCallStart", {"caseId": case["_id"], "callRequestId": call_id})


def place_pending_calls() -> int:
    """Calls every approved case nobody has called yet (covers dashboard approvals). Returns how many it tried."""
    pending = query("cases:awaitingCall")
    for case in pending:
        request_call(case)
    return len(pending)


def approve(case: dict) -> None:
    mutation("cases:approve", {"caseId": case["_id"]})
    request_call(case)


def decline(case: dict) -> None:
    mutation("cases:decline", {"caseId": case["_id"]})
