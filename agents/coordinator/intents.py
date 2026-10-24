"""What Priya can ask the Coordinator, and how each request is answered from the student file.

Matching is plain keywords for now; anything unrecognised gets the help text.
"""

from agents.store import dollars, log, query
from agents.tax import engine

AGENT = "coordinator"

HELP = (
    "I'm Docket. I check your pay and filings against official F-1 rules.\n\n"
    "Try:\n- **check my pay**: I read your paystubs and flag problems\n- **what's wrong?**: your open issues"
)


def demo_profile() -> dict | None:
    # One student in the demo; real multi-student lookup comes with onboarding.
    profiles = query("profiles:list")
    return profiles[0] if profiles else None


def format_flag(n: int, explanation: str, quote: str, title: str, url: str) -> str:
    return f"**{n}.** {explanation}\n> \"{quote}\"\n> {title}: {url}"


def check_my_pay() -> str:
    profile = demo_profile()
    if profile is None:
        return "I don't have a student file yet. Run the reset script to seed the demo."
    paystubs = query("paystubs:listByProfile", {"profileId": profile["_id"]})
    log(AGENT, "check_pay_requested", f"{profile['name']} asked to check pay; {len(paystubs)} paystubs on file",
        inputIds=[profile["_id"]])
    flags = engine.run(profile["_id"])
    if not flags:
        return f"I checked your {len(paystubs)} paystubs. I didn't find anything wrong."
    lines = [f"I checked your {len(paystubs)} paystubs from {paystubs[0]['employer']} and found "
             f"{len(flags)} likely issue{'s' if len(flags) > 1 else ''}:"]
    for i, f in enumerate(flags, 1):
        lines.append(format_flag(i, f["explanation"], f["quote"], f["sourceTitle"], f["source_url"]))
    refund = sum(f["hit"]["amountCents"] for f in flags if f["action"] == "open_refund_case")
    if refund:
        lines.append(f"I can draft a refund request to payroll for **{dollars(refund)}**. Nothing is sent without your approval.")
    return "\n\n".join(lines)


def whats_wrong() -> str:
    profile = demo_profile()
    if profile is None:
        return "I don't have a student file yet."
    flags = [f for f in query("flags:listByProfile", {"profileId": profile["_id"]}) if f["status"] == "open"]
    log(AGENT, "open_flags_listed", f"{len(flags)} open flags for {profile['name']}", inputIds=[profile["_id"]])
    if not flags:
        return "Nothing open right now. Say **check my pay** and I'll look at your latest paystubs."
    lines = [f"You have {len(flags)} open issue{'s' if len(flags) > 1 else ''}:"]
    for i, f in enumerate(flags, 1):
        source = query("sources:get", {"sourceId": f["sourceId"]})
        lines.append(format_flag(i, f["explanation"], f["quote"], source["title"], source["url"]))
    return "\n\n".join(lines)


def answer(text: str) -> str:
    t = text.lower()
    if "pay" in t and ("check" in t or "look" in t):
        return check_my_pay()
    if "wrong" in t or "issue" in t or "flag" in t:
        return whats_wrong()
    return HELP
