"""What Priya can ask the Coordinator, and how each request is answered from the student file.

YES/NO approvals are matched in code, so a misread message can never start a payroll call.
Everything else goes through Claude (agents/coordinator/brain.py): it classifies the message and
phrases the findings, and code checks the reply before it is shown. If Claude fails or its reply
fails a check, Priya gets "I couldn't check this, ask payroll." and no case is opened. Code adds the
verbatim quotes Claude cites and the disclaimer. Rules and cases are handled by the Tax and Caseworker agents over typed messages;
the Coordinator only reads the student file and talks to Priya.
"""

import asyncio
import json
import re
from datetime import date

from uagents import Context

from agents import messaging
from agents.coordinator import brain
from agents.coordinator.cards import Card, profile_form, refund_review
from agents.coordinator.profile_form import form_changes
from agents.coordinator.season import next_season
from agents.messages import (
    CaseDecision, CasesResult, DecisionResult, OpenCases, RulesResult, RunRules, address_of,
)
from agents.store import dollars, log, mutation, query
from seed.demo_data import SCHOOL_CALENDAR

AGENT = "coordinator"

HELP = (
    "I'm Docket. I check your pay and filings against official F-1 rules.\n\n"
    "Try:\n- **check my pay**: I read your paystubs and flag problems\n- **what's wrong?**: your open issues"
)

NOT_ADVICE = "This is not tax advice; confirm with your international student office."

COULD_NOT_CHECK = "I couldn't check this, ask payroll."

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
    # Simulated cohort profiles (seed/cohort.py) are never the student we talk to.
    return next((p for p in query("profiles:list") if not p.get("simulated")), None)


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
    """Send a typed message to another Docket agent and wait for its reply (None on failure). Both are logged."""
    reply, status = await messaging.ask(ctx, AGENT, agent, message, response_type,
                                        f"{type(message).__name__} for the student", timeout=90)
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
    return {"profile": profile, "paystubs": paystubs, "flags": flags}


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
    return {"profile": profile, "paystubs": paystubs, "flags": flags}


def facts_for(data: dict) -> dict:
    """The structured facts Claude may use. Every number here was computed by code."""
    p = data["profile"]
    return {
        "student": {k: p.get(k) for k in ("name", "visa", "arrivalDate", "school", "workAuth")},
        "paystubs": [{k: s[k] for k in ("employer", "periodStart", "periodEnd", "grossCents", "hoursByWeek",
                                        "ssCents", "medicareCents", "netCents")} for s in data["paystubs"]],
        "ruleResults": [{k: f.get(k) for k in ("ruleId", "amountCents", "detail", "caseState") if f.get(k) is not None}
                        for f in data["flags"]],
    }


def checked_reply(text: str, data: dict) -> brain.Reply | None:
    """Claude's reply if it passes every code check, else None (logged)."""
    flags = data["flags"]
    facts = facts_for(data)
    excerpts = {f["ruleId"]: {"quote": f["quote"], "title": f["title"], "url": f["url"]} for f in flags}
    sources = {}
    for f in flags:
        row = query("sources:getByUrl", {"url": f["url"]})
        if row is not None:
            sources[f["ruleId"]] = row["text"]
    reply = brain.write_reply(text, facts, excerpts)
    found = brain.problems(reply, facts, {f["ruleId"] for f in flags}, sources)
    if found:
        log(AGENT, "claude_reply_rejected", "; ".join(found))
        return None
    log(AGENT, "claude_reply_checked",
        f"{len(reply.findings)} findings, needs_human={reply.needs_human}; amounts and quotes verified")
    return reply


def compose(reply: brain.Reply, flags: list[dict], extra: list[str]) -> str:
    """Claude's words, then the verbatim quotes it cited (by source_quote_id), then code-owned text."""
    by_id = {f["ruleId"]: f for f in flags}
    cited = list(dict.fromkeys(f.source_quote_id for f in reply.findings if f.source_quote_id in by_id))
    parts = [reply.message_to_student.strip()]
    parts += [source_block(by_id[i]["quote"], by_id[i]["title"], by_id[i]["url"]) for i in cited]
    return "\n\n".join(parts + extra + [NOT_ADVICE])


def review_card(case: dict, data: dict) -> Card:
    fica = next((f for f in data["flags"] if f["ruleId"] == "FICA_EXEMPT_F1"), {})
    detail = fica.get("detail") or {}
    employer = data["paystubs"][0]["employer"] if data["paystubs"] else "your employer"
    return refund_review(employer, case["amountCents"], detail.get("ssCents"), detail.get("medicareCents"),
                         "likely refundable", case["_id"], case.get("flagId"),
                         "Here is the refund request. Approve it and I'll contact payroll; nothing happens until you do.")


async def explain_with_claude(ctx: Context, text: str, intent: str) -> list:
    data = await gather_check(ctx) if intent == "check_pay" else await asyncio.to_thread(gather_open)
    if isinstance(data, str):
        return [data]
    if not data["flags"]:
        return [f"I checked your {len(data['paystubs'])} paystubs and didn't find anything wrong.\n\n{NOT_ADVICE}"]
    try:
        reply = await asyncio.to_thread(checked_reply, text, data)
    except Exception as e:
        ctx.logger.warning(f"Claude reply failed: {e}")
        await asyncio.to_thread(log, AGENT, "claude_reply_failed", str(e)[:200])
        reply = None
    if reply is None:
        return [COULD_NOT_CHECK]
    unsure = brain.unsure(reply)
    hold_refund = any(u.rule == "FICA_EXEMPT_F1" for u in unsure)
    extra = [await asyncio.to_thread(hand_off, unsure, data, hold_refund)] if unsure else []
    if intent == "check_pay" and not hold_refund:
        await asyncio.to_thread(reopen_reviewed, data["profile"]["_id"])
        cases = await ask(ctx, "CASEWORKER", OpenCases(profile_id=data["profile"]["_id"]), CasesResult)
        pending = json.loads(cases.awaiting_json) if cases else []
        if pending:
            return [compose(reply, data["flags"], extra), review_card(pending[0], data)]
    return [compose(reply, data["flags"], extra)]


def reopen_reviewed(profile_id: str) -> None:
    """A confident check after a handoff puts held flags back, so the Caseworker can open the case."""
    for flag in query("flags:listByProfile", {"profileId": profile_id}):
        if flag["status"] == "needs_review":
            mutation("flags:setStatus", {"flagId": flag["_id"], "status": "open"})
            log(AGENT, "review_cleared", f"{flag['ruleId']} confident again; back to open", inputIds=[flag["_id"]])


def hand_off(unsure: list[brain.Finding], data: dict, hold_refund: bool) -> str:
    """Low or unknown confidence: point Priya to a person, and if the refund finding is unsure,
    hold its flag back from the Caseworker so no case is opened."""
    if hold_refund:
        for flag in query("flags:listByProfile", {"profileId": data["profile"]["_id"]}):
            if flag["ruleId"] == "FICA_EXEMPT_F1" and flag["status"] == "open":
                mutation("flags:setStatus", {"flagId": flag["_id"], "status": "needs_review"})
    reasons = "; ".join(dict.fromkeys(u.basis for u in unsure))
    log(AGENT, "handoff", f"Low/unknown confidence ({reasons}); "
        f"{'refund case held' if hold_refund else 'refund case not affected'}", inputIds=[data["profile"]["_id"]])
    if hold_refund:
        return (f"I'm not sure enough to contact payroll for you: {reasons}. Please check with your international "
                "student office or your payroll office first. Once they confirm, say **check my pay** and I'll "
                "take it from there.")
    return f"I'm not sure about this part, so please ask your international student office: {reasons}."


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


async def answer_selection(ctx: Context, selection: dict) -> str:
    """A card button or form. Approve/Decline on the review card are explicit choices, so they act directly."""
    action = selection["action"]
    await asyncio.to_thread(log, AGENT, "card_selection", f"{action}", inputIds=[str(v) for k, v in selection.items()
                                                                                  if k.endswith("_id")])
    if action == "approve_refund":
        return await respond_to_approval(ctx, True)
    if action == "decline_refund":
        return await respond_to_approval(ctx, False)
    if action == "submit_profile":
        return await asyncio.to_thread(save_profile, selection)
    return f"I got your {action.replace('_', ' ')} selection, but I can't act on it yet."


def save_profile(selection: dict) -> str:
    profile = demo_profile()
    if profile is None:
        return "I don't have a student file yet."
    changes, problems = form_changes(selection, date.today())
    if problems:
        log(AGENT, "profile_form_rejected", "; ".join(problems), inputIds=[profile["_id"]])
        return f"I didn't save that: {'; '.join(problems)}. Say **update my profile** to try again."
    if not changes:
        return "Nothing to save. Say **update my profile** to fill in the form."
    mutation("profiles:updateFromForm", {"profileId": profile["_id"], **changes})
    return "Saved your profile. Say **check my pay** and I'll check your paystubs with it."


async def answer(ctx: Context, text: str) -> str:
    t = text.lower().strip()
    words = set(re.findall(r"[a-z']+", t))
    if words & {"yes", "approve", "approved"} or "contact payroll" in t:
        return await respond_to_approval(ctx, True)
    if t.rstrip(".!") in {"no", "nope", "no thanks", "don't", "dont", "hold off"}:
        return await respond_to_approval(ctx, False)

    try:
        intent = (await asyncio.to_thread(brain.classify, text)).intent
    except Exception as e:
        ctx.logger.warning(f"classification failed: {e}")
        await asyncio.to_thread(log, AGENT, "claude_reply_failed", f"classification: {str(e)[:200]}")
        return COULD_NOT_CHECK
    await asyncio.to_thread(log, AGENT, "intent_classified", f"{intent}: {text[:80]!r}")

    if intent in ("approve", "decline"):
        return CONFIRM_APPROVAL  # only an explicit YES or NO acts
    if intent == "other":
        return HELP
    if intent == "profile":
        return [profile_form()]
    if intent == "next_season":
        return await asyncio.to_thread(season_reply)
    return await explain_with_claude(ctx, text, intent)


def season_reply() -> str:
    profile = demo_profile()
    if profile is None:
        return "I don't have a student file yet."
    paystubs = query("paystubs:listByProfile", {"profileId": profile["_id"]})
    log(AGENT, "next_season_explained", f"Next-season checklist for {profile['name']}", inputIds=[profile["_id"]])
    return f"{next_season(profile, paystubs, SCHOOL_CALENDAR, date.today())}\n\n{NOT_ADVICE}"
