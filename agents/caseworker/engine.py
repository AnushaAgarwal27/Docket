"""Caseworker: turn refund flags into cases with a draft request, and act on the student's approval.

State changes happen in convex/cases.ts so every caller obeys the same state machine.
"""

from datetime import date, timedelta
from pathlib import Path

from agents.caseworker import cartesia, rehearsal
from agents.caseworker.letter import letter_paragraphs, render_pdf
from agents.convex_files import upload_and_attach
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
        attach_letter(profile, flag, paystubs)
    return awaiting_approval(profile_id)


def attach_letter(profile: dict, flag: dict, paystubs: list[dict]) -> None:
    """The refund request as a PDF on the flag's receipt, once per flag."""
    receipt = query("files:forFlag", {"flagId": flag["_id"]})
    if receipt is None or receipt["letters"]:
        return
    linked = [p for p in paystubs if p["_id"] in set(flag.get("paystubIds") or [])]
    if not linked or "ssCents" not in flag or "medicareCents" not in flag:
        log(AGENT, "letter_skipped", f"Flag {flag['_id']} has no linked paystubs or rule totals yet",
            inputIds=[flag["_id"]])
        return
    source = query("sources:cite", {"sourceId": flag["sourceId"]}) or {"title": "IRS Publication 519"}
    pdf = render_pdf(letter_paragraphs(profile, flag, linked, source["title"], date.today()))
    upload_and_attach(Path(f"refund_request_{profile['name'].split()[0].lower()}.pdf"), "letter",
                      agent=AGENT, data=pdf, flagId=flag["_id"])


def awaiting_approval(profile_id: str) -> list[dict]:
    return [c for c in query("cases:listByProfile", {"profileId": profile_id}) if c["state"] == "awaiting_approval"]


def request_call(case: dict) -> None:
    """Place the payroll call for an approved case, once. Safe to call from several places."""
    if not mutation("cases:claimCall", {"caseId": case["_id"]}):
        return  # already claimed by another trigger, or no longer contacting payroll
    if rehearsal.enabled():
        fresh = query("cases:get", {"caseId": case["_id"]})  # carries callAttempts and the rehearsal setting
        mutation("cases:recordCallStart", {"caseId": case["_id"], "callRequestId": rehearsal.start(fresh), "simulated": True})
        return
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


def long_date(d: date) -> str:
    return f"{d.strftime('%B')} {d.day}, {d.year}"


def draft_written_request(case: dict, profile: dict, paystubs: list[dict], flag: dict, source_title: str,
                          today: date | None = None) -> str:
    """The letter after a first stall or refusal. Every number comes from the student file; no hours, no visa history."""
    today = today or date.today()
    ss = sum(p["ssCents"] for p in paystubs)
    medicare = sum(p["medicareCents"] for p in paystubs)
    first = min(p["periodStart"] for p in paystubs)
    last = max(p["periodEnd"] for p in paystubs)
    year = int(last[:4]) - int(profile["arrivalDate"][:4]) + 1
    reply_by = today + timedelta(days=10)
    name, employer = profile["name"], paystubs[0]["employer"]
    return (
        f"{long_date(today)}\n\n"
        f"To: {employer} Payroll\n"
        f"Re: Refund of Social Security and Medicare withheld in error, {name}\n\n"
        f"Docket, an AI assistant acting for {name} with her permission, called payroll about this refund. "
        f"Payroll did not agree to refund it on that call, so this letter puts the request in writing.\n\n"
        f"{name} is a nonresident alien student in F-1 status, in calendar year {year} of 5 in the United States. "
        f"Social Security ({dollars(ss)}) and Medicare ({dollars(medicare)}) were withheld from {len(paystubs)} "
        f"paychecks for pay periods {first} to {last}, a total of {dollars(ss + medicare)}.\n\n"
        f"{source_title} states: \"{flag['quote']}\"\n\n"
        f"Please, by {long_date(reply_by)}, do one of the following:\n"
        f"1. Refund {dollars(case['amountCents'])} and stop withholding Social Security and Medicare "
        f"from her future paychecks; or\n"
        f"2. If you will not refund it, give her a written statement saying so. She needs that statement to claim the "
        f"refund from the IRS with Form 843 and Form 8316.\n\n"
        f"Docket will follow up by phone on {case['nextFollowUp']}.\n\n"
        f"Sent by {name}, prepared with Docket."
    )


def prepare_pending_letters() -> int:
    """Writes the letter for every case that moved to written_request. Returns how many it wrote."""
    pending = query("cases:awaitingLetter")
    for case in pending:
        profile = query("profiles:get", {"profileId": case["profileId"]})
        paystubs = query("paystubs:listByProfile", {"profileId": case["profileId"]})
        flag = next(f for f in query("flags:listByProfile", {"profileId": case["profileId"]}) if f["_id"] == case["flagId"])
        source = query("sources:cite", {"sourceId": flag["sourceId"]}) or {"title": "IRS Publication 519"}
        text = draft_written_request(case, profile, paystubs, flag, source["title"])
        mutation("cases:recordWrittenRequest", {"caseId": case["_id"], "text": text})
    return len(pending)


def approve(case: dict) -> None:
    mutation("cases:approve", {"caseId": case["_id"]})
    request_call(case)


def decline(case: dict) -> None:
    mutation("cases:decline", {"caseId": case["_id"]})
