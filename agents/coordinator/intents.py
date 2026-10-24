"""What Priya can ask the Coordinator, and how each request is answered from the student file.

Matching is plain keywords for now; anything unrecognised gets the help text.
Rules and cases are handled by the Tax and Caseworker agents over typed messages;
the Coordinator only reads the student file and talks to Priya.
"""

import asyncio
import json
import re

from uagents import Context

from agents.messages import (
    CaseDecision, CasesResult, DecisionResult, OpenCases, RulesResult, RunRules, address_of,
)
from agents.store import dollars, log, query

AGENT = "coordinator"

HELP = (
    "I'm Docket. I check your pay and filings against official F-1 rules.\n\n"
    "Try:\n- **check my pay**: I read your paystubs and flag problems\n- **what's wrong?**: your open issues"
)

CASE_STATUS = {
    "awaiting_approval": "waiting for your approval",
    "contacting_employer": "contacting payroll",
    "awaiting_response": "waiting on payroll",
    "refund_received": "refund received",
    "escalate_irs": "payroll refused; IRS claim checklist ready",
    "closed": "closed",
}


def demo_profile() -> dict | None:
    # One student in the demo; real multi-student lookup comes with onboarding.
    profiles = query("profiles:list")
    return profiles[0] if profiles else None


def format_flag(n: int, explanation: str, quote: str, title: str, url: str) -> str:
    return f"**{n}.** {explanation}\n> \"{quote}\"\n> {title}: {url}"


def approval_prompt(case: dict) -> str:
    draft = "\n".join(f"> {line}" if line else ">" for line in case["draft"].splitlines())
    return (f"Here is the refund request I'd send to payroll:\n\n{draft}\n\n"
            "Reply **YES** and I'll contact payroll with this request, or **NO** to hold off. "
            "On a call, I always say I'm an AI assistant acting with your permission.")


UNAVAILABLE = "Sorry, part of Docket isn't responding right now. Please try again in a moment."


async def ask(ctx: Context, agent: str, message, response_type):
    """Send a typed message to another Docket agent and wait for its reply (None on failure)."""
    reply, status = await ctx.send_and_receive(address_of(agent), message, response_type=response_type, timeout=25)
    if reply is None or getattr(reply, "error", ""):
        ctx.logger.error(f"{agent} failed: {getattr(reply, 'error', '') or status}")
        return None
    return reply


async def check_my_pay(ctx: Context) -> str:
    profile = await asyncio.to_thread(demo_profile)
    if profile is None:
        return "I don't have a student file yet. Run the reset script to seed the demo."
    paystubs = await asyncio.to_thread(query, "paystubs:listByProfile", {"profileId": profile["_id"]})
    await asyncio.to_thread(log, AGENT, "check_pay_requested",
                            f"{profile['name']} asked to check pay; {len(paystubs)} paystubs on file",
                            inputIds=[profile["_id"]])
    result = await ask(ctx, "TAX", RunRules(profile_id=profile["_id"]), RulesResult)
    if result is None:
        return UNAVAILABLE
    flags = json.loads(result.flags_json)
    if not flags:
        return f"I checked your {len(paystubs)} paystubs. I didn't find anything wrong."
    lines = [f"I checked your {len(paystubs)} paystubs from {paystubs[0]['employer']} and found "
             f"{len(flags)} likely issue{'s' if len(flags) > 1 else ''}:"]
    for i, f in enumerate(flags, 1):
        lines.append(format_flag(i, f["explanation"], f["quote"], f["sourceTitle"], f["source_url"]))
    cases = await ask(ctx, "CASEWORKER", OpenCases(profile_id=profile["_id"]), CasesResult)
    pending = json.loads(cases.awaiting_json) if cases else []
    if pending:
        lines.append(approval_prompt(pending[0]))
    return "\n\n".join(lines)


def whats_wrong() -> str:
    profile = demo_profile()
    if profile is None:
        return "I don't have a student file yet."
    flags = [f for f in query("flags:listByProfile", {"profileId": profile["_id"]}) if f["status"] != "resolved"]
    cases = {c["flagId"]: c for c in query("cases:listByProfile", {"profileId": profile["_id"]})}
    log(AGENT, "open_flags_listed", f"{len(flags)} unresolved flags for {profile['name']}", inputIds=[profile["_id"]])
    if not flags:
        return "Nothing open right now. Say **check my pay** and I'll look at your latest paystubs."
    lines = [f"You have {len(flags)} open issue{'s' if len(flags) > 1 else ''}:"]
    for i, f in enumerate(flags, 1):
        source = query("sources:cite", {"sourceId": f["sourceId"]})
        text = format_flag(i, f["explanation"], f["quote"], source["title"], source["url"])
        if f["_id"] in cases:
            text += f"\n> Case: {CASE_STATUS.get(cases[f['_id']]['state'], cases[f['_id']]['state'])}"
        lines.append(text)
    return "\n\n".join(lines)


async def respond_to_approval(ctx: Context, approved: bool) -> str:
    profile = await asyncio.to_thread(demo_profile)
    if profile is None:
        return "I don't have a student file yet."
    await asyncio.to_thread(log, AGENT, "approval_received" if approved else "approval_declined",
                            f"Student replied {'YES' if approved else 'NO'} to contacting payroll",
                            inputIds=[profile["_id"]])
    result = await ask(ctx, "CASEWORKER", CaseDecision(profile_id=profile["_id"], approved=approved), DecisionResult)
    if result is None:
        return UNAVAILABLE
    if not result.acted:
        return "There's nothing waiting for your approval right now. Say **check my pay** to look for issues."
    if approved:
        return (f"Approved. I'm contacting payroll about your **{dollars(result.amount_cents)}** refund. "
                "I'll log the call and tell you what they promise.")
    return "Okay, I won't contact payroll. The issue stays on your file; say **check my pay** any time to reopen it."


async def answer(ctx: Context, text: str) -> str:
    t = text.lower().strip()
    words = set(re.findall(r"[a-z']+", t))
    if words & {"yes", "approve", "approved"} or "contact payroll" in t:
        return await respond_to_approval(ctx, True)
    if t.rstrip(".!") in {"no", "nope", "no thanks", "don't", "dont", "hold off"}:
        return await respond_to_approval(ctx, False)
    if "pay" in t and ("check" in t or "look" in t):
        return await check_my_pay(ctx)
    if "wrong" in t or "issue" in t or "flag" in t:
        return await asyncio.to_thread(whats_wrong)
    return HELP
