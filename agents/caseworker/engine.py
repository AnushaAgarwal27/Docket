"""Caseworker: turn refund flags into cases with a draft request, and act on the student's approval.

State changes happen in convex/cases.ts so every caller obeys the same state machine.
"""

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
    # Person 3 replaces this with the Cartesia Managed Agent outbound call; its
    # log_call_outcome webhook then calls cases:logCallOutcome.
    log(AGENT, "call_requested", f"Payroll call requested for case {case['_id']} ({dollars(case['amountCents'])}); "
        "Cartesia not wired yet", inputIds=[case["_id"]])


def approve(case: dict) -> None:
    mutation("cases:approve", {"caseId": case["_id"]})
    request_call(case)


def decline(case: dict) -> None:
    mutation("cases:decline", {"caseId": case["_id"]})
