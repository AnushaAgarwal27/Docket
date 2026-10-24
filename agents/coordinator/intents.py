"""What Priya can ask the Coordinator, and how each request is answered from the student file.

YES/NO approvals are matched in code, so a misread message can never start a payroll call.
Everything else goes through Claude (agents/coordinator/brain.py): it classifies the message and
phrases the findings, and code checks the reply before it is shown. Any failure falls back to the
template reply. Rules and cases are handled by the Tax and Caseworker agents over typed messages;
the Coordinator only reads the student file and talks to Priya.
"""

import asyncio
import json
import re

from uagents import Context

from agents.coordinator import brain
from agents.messages import (
    CaseDecision, CasesResult, DecisionResult, OpenCases, RulesResult, RunRules, address_of,
)
from agents.store import dollars, log, query

AGENT = "coordinator"

HELP = (
    "I'm Docket. I check your pay and filings against official F-1 rules.\n\n"
    "Try:\n- **check my pay**: I read your paystubs and flag problems\n- **what's wrong?**: your open issues"
)

NOT_ADVICE = "This is not tax advice; confirm with your international student office."

CONFIRM_APPROVAL = ("To be sure: reply **YES** and I'll contact payroll with the request above, "
                    "or **NO** to hold off.")

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
    return f"**{n}.** {explanation}\n\n{source_block(quote, title, url)}"


def source_block(quote: str, title: str, url: str) -> str:
    # The source sits outside the blockquote, so chat apps don't wrap it in the quote marks.
    return f"> {quote}\n\n— {title}: {url}"


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


async def gather_check(ctx: Context) -> dict | str:
    """Runs the rules through the Tax agent. Returns the findings, or a reply string on failure."""
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
    flags = [{"ruleId": f["id"], "amountCents": f["hit"]["amountCents"], "explanation": f["explanation"],
              "quote": f["quote"], "title": f["sourceTitle"], "url": f["source_url"], "detail": f["hit"]}
             for f in json.loads(result.flags_json)]
    pending = []
    if flags:
        cases = await ask(ctx, "CASEWORKER", OpenCases(profile_id=profile["_id"]), CasesResult)
        pending = json.loads(cases.awaiting_json) if cases else []
    return {"profile": profile, "paystubs": paystubs, "flags": flags, "pending": pending}


def template_check(data: dict) -> str:
    paystubs, flags = data["paystubs"], data["flags"]
    if not flags:
        return f"I checked your {len(paystubs)} paystubs. I didn't find anything wrong."
    lines = [f"I checked your {len(paystubs)} paystubs from {paystubs[0]['employer']} and found "
             f"{len(flags)} likely issue{'s' if len(flags) > 1 else ''}:"]
    for i, f in enumerate(flags, 1):
        lines.append(format_flag(i, f["explanation"], f["quote"], f["title"], f["url"]))
    if data["pending"]:
        lines.append(approval_prompt(data["pending"][0]))
    return "\n\n".join(lines)


def gather_open() -> dict | str:
    """Unresolved flags already on file, with their case state."""
    profile = demo_profile()
    if profile is None:
        return "I don't have a student file yet."
    cases = {c["flagId"]: c for c in query("cases:listByProfile", {"profileId": profile["_id"]})}
    flags = []
    for f in query("flags:listByProfile", {"profileId": profile["_id"]}):
        if f["status"] == "resolved":
            continue
        source = query("sources:cite", {"sourceId": f["sourceId"]})
        case = cases.get(f["_id"])
        flags.append({"ruleId": f["ruleId"], "amountCents": f["amountCents"], "explanation": f["explanation"],
                      "quote": f["quote"], "title": source["title"], "url": source["url"],
                      "caseState": CASE_STATUS.get(case["state"], case["state"]) if case else None})
    log(AGENT, "open_flags_listed", f"{len(flags)} unresolved flags for {profile['name']}", inputIds=[profile["_id"]])
    paystubs = query("paystubs:listByProfile", {"profileId": profile["_id"]})
    return {"profile": profile, "paystubs": paystubs, "flags": flags, "pending": []}


def template_open(data: dict) -> str:
    flags = data["flags"]
    if not flags:
        return "Nothing open right now. Say **check my pay** and I'll look at your latest paystubs."
    lines = [f"You have {len(flags)} open issue{'s' if len(flags) > 1 else ''}:"]
    for i, f in enumerate(flags, 1):
        text = format_flag(i, f["explanation"], f["quote"], f["title"], f["url"])
        if f["caseState"]:
            text += f"\n\nCase: {f['caseState']}"
        lines.append(text)
    return "\n\n".join(lines)


def facts_for(data: dict) -> dict:
    """The structured facts Claude may use. Every number here was computed by code."""
    p = data["profile"]
    return {
        "student": {k: p.get(k) for k in ("name", "visa", "arrivalDate", "school", "workAuth")},
        "paystubs": [{k: s[k] for k in ("employer", "periodStart", "periodEnd", "grossCents", "hoursByWeek",
                                        "ssCents", "medicareCents", "netCents")} for s in data["paystubs"]],
        "ruleResults": [{k: f.get(k) for k in ("ruleId", "amountCents", "detail", "caseState") if f.get(k) is not None}
                        for f in data["flags"]],
        "caseAwaitingApproval": ({"amountCents": data["pending"][0]["amountCents"]} if data["pending"] else None),
    }


def claude_reply(text: str, language: str, data: dict) -> str | None:
    """Claude's wording with the verified sources attached, or None if any code check fails."""
    flags = data["flags"]
    if not flags:
        return None
    facts = facts_for(data)
    excerpts = {f["ruleId"]: {"quote": f["quote"], "title": f["title"], "url": f["url"]} for f in flags}
    sources = {}
    for f in flags:
        row = query("sources:getByUrl", {"url": f["url"]})
        if row is not None:
            sources[f["ruleId"]] = row["text"]
    reply = brain.write_reply(text, facts, excerpts, language)
    found = brain.problems(reply, facts, {f["ruleId"] for f in flags}, sources)
    if found:
        log(AGENT, "claude_reply_rejected", "; ".join(found))
        return None
    log(AGENT, "claude_reply_checked",
        f"{len(reply.findings)} findings, needs_human={reply.needs_human}; amounts and quotes verified")
    parts = [reply.message_to_student.strip()]
    parts += [source_block(f["quote"], f["title"], f["url"]) for f in flags]
    if data["pending"]:
        parts.append(approval_prompt(data["pending"][0]))
    if "not tax advice" not in reply.message_to_student.lower():
        parts.append(NOT_ADVICE)
    return "\n\n".join(parts)


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


def keyword_intent(t: str) -> str:
    if "pay" in t and ("check" in t or "look" in t):
        return "check_pay"
    if "wrong" in t or "issue" in t or "flag" in t:
        return "explain"
    return "other"


async def answer(ctx: Context, text: str) -> str:
    t = text.lower().strip()
    words = set(re.findall(r"[a-z']+", t))
    if words & {"yes", "approve", "approved"} or "contact payroll" in t:
        return await respond_to_approval(ctx, True)
    if t.rstrip(".!") in {"no", "nope", "no thanks", "don't", "dont", "hold off"}:
        return await respond_to_approval(ctx, False)

    language = "English"
    try:
        c = await asyncio.to_thread(brain.classify, text)
        intent, language = c.intent, c.language
    except Exception as e:
        ctx.logger.warning(f"classification failed, using keywords: {e}")
        intent = keyword_intent(t)
    await asyncio.to_thread(log, AGENT, "intent_classified", f"{intent} ({language}): {text[:80]!r}")

    if intent in ("approve", "decline"):
        return CONFIRM_APPROVAL  # only an explicit YES or NO acts
    if intent == "other":
        return HELP
    data = await gather_check(ctx) if intent == "check_pay" else await asyncio.to_thread(gather_open)
    if isinstance(data, str):
        return data
    try:
        reply = await asyncio.to_thread(claude_reply, text, language, data)
    except Exception as e:
        ctx.logger.warning(f"Claude reply failed, using template: {e}")
        reply = None
    if reply is not None:
        return reply
    return template_check(data) if intent == "check_pay" else template_open(data)
