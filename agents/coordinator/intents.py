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
from agents.coordinator import hearing_view
from agents.coordinator.cards import (
    Card, contact_form, document_review, group_invite, profile_form, refund_review,
)
from agents.coordinator.profile_form import form_changes
from agents.coordinator.season import next_season
from agents.messages import (
    CaseDecision, CasesResult, DecisionResult, OpenCases, ResearchAnswer, ResearchQuestion,
    RulesResult, RunRules, address_of,
)
from agents.store import dollars, log, mutation, query
from seed.demo_data import SCHOOL_CALENDAR

AGENT = "coordinator"

HELP = (
    "I'm Docket. I check your pay and filings against official F-1 rules.\n\n"
    "Try:\n"
    "- **check my pay**: I read your paystubs and flag problems\n"
    "- **what's wrong?**: your open issues\n"
    "- **my forms**: what I've filled in for you, and what needs your signature\n"
    "- **anyone else?**: other students at your employer with the same problem\n"
    "- **call me**: how I should reach you, and my phone line\n"
    "- ask me anything about F-1 pay, tax or status and I'll research it properly"
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
    return {"profile": profile, "paystubs": paystubs, "flags": flags, "hearings": json.loads(result.hearings_json)}


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


def review_card(data: dict, verdict: str, case: dict | None = None, flag_id: str | None = None, text: str = "") -> Card:
    fica = next((f for f in data["flags"] if f["ruleId"] == "FICA_EXEMPT_F1"), {})
    detail = fica.get("detail") or {}
    employer = data["paystubs"][0]["employer"] if data["paystubs"] else "your employer"
    amount = case["amountCents"] if case else fica.get("amountCents", 0)
    return refund_review(employer, amount, detail.get("ssCents"), detail.get("medicareCents"), verdict,
                         case["_id"] if case else None, flag_id or (case or {}).get("flagId"),
                         text or "Here is the refund request. Approve it and I'll contact payroll; nothing happens "
                                 "until you do.")


PROFILE_FACTS = {"visa": "visa type", "arrivalDate": "arrival date", "employmentType": "employee or contractor"}


async def check_pay(ctx: Context) -> list:
    """Run the rules, let Tax and the Auditor hold a Hearing on each claim, narrate it, then show the
    verdict as a detail card and, if a refund is possible, the review card."""
    data = await gather_check(ctx)
    if isinstance(data, str):
        return [data]
    profile = data["profile"]
    stored = {h["_id"]: h for h in await asyncio.to_thread(query, "hearings:latestForProfile",
                                                            {"profileId": profile["_id"], "limit": 10})}
    heard = [stored[h["hearing_id"]] for h in data["hearings"] if h.get("hearing_id") in stored]
    if not heard:
        if not data["flags"]:
            return [f"I checked your {len(data['paystubs'])} paystubs and didn't find anything wrong.\n\n{NOT_ADVICE}"]
        return [COULD_NOT_CHECK]
    flags_db = {f["_id"]: f for f in await asyncio.to_thread(query, "flags:listByProfile", {"profileId": profile["_id"]})}
    rules = {f["ruleId"]: f for f in data["flags"]}
    parts: list = []
    for h in sorted(heard, key=lambda h: h["ruleId"] != hearing_view.FICA):
        flag = flags_db.get(h.get("flagId"))
        r = rules.get(h["ruleId"], {})
        if h["ruleId"] == hearing_view.FICA:
            parts += hearing_view.narrate(h)
        parts.append(hearing_view.detail_card(h, flag, r.get("quote") or (flag or {}).get("quote"), r.get("title")))
        if h["ruleId"] != hearing_view.FICA:
            continue
        line = hearing_view.verdict_line_from(h)
        if h["verdict"] == "upheld":
            cases = await ask(ctx, "CASEWORKER", OpenCases(profile_id=profile["_id"]), CasesResult)
            pending = json.loads(cases.awaiting_json) if cases else []
            if pending:
                parts.append(review_card(data, line, case=pending[0]))
        elif h["verdict"] == "downgraded":
            parts.append(review_card(data, line, flag_id=h.get("flagId"), text=(
                "This one needs your OK before I do anything, because an exception may apply. Approve and I'll "
                "contact payroll for the full amount; payroll decides what it can refund.")))
        elif h["verdict"] == "needs_human":
            missing = [label for key, label in PROFILE_FACTS.items() if not profile.get(key)]
            parts.append(profile_form(missing) if missing else
                         f"I can't act on this yet: {h['reason']}. Please ask your payroll office or international "
                         "student office, then say **check my pay** again.")
        else:
            parts.append(hearing_view.defeated_message(h))
    return parts


async def replay_hearing(flag_id: str | None = None) -> list:
    """'why?': the stored Hearing again, from Convex. No new Claude call."""
    profile = await asyncio.to_thread(demo_profile)
    if profile is None:
        return ["I don't have a student file yet."]
    hearings = await asyncio.to_thread(query, "hearings:latestForProfile", {"profileId": profile["_id"], "limit": 10})
    pick = next((h for h in hearings if flag_id and h.get("flagId") == flag_id), None) or next(
        (h for h in hearings if h["ruleId"] == hearing_view.FICA), None) or (hearings[0] if hearings else None)
    await asyncio.to_thread(log, AGENT, "hearing_replayed", f"{pick['ruleId']}: {pick['verdict']}" if pick else "none")
    if pick is None:
        return ["There's no Hearing on file yet. Say **check my pay** and I'll hold one."]
    return hearing_view.narrate(pick)


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
    return [compose(reply, data["flags"], [])]


async def respond_to_approval(ctx: Context, approved: bool) -> str:
    profile = await asyncio.to_thread(demo_profile)
    if profile is None:
        return "I don't have a student file yet."
    await asyncio.to_thread(log, AGENT, "approval_received" if approved else "approval_declined",
                            f"Student replied {'YES' if approved else 'NO'} to contacting payroll",
                            inputIds=[profile["_id"]])
    result = await ask(ctx, "CASEWORKER", CaseDecision(profile_id=profile["_id"], approved=approved), DecisionResult)
    if result is not None and not result.acted and approved and await asyncio.to_thread(give_ok, profile["_id"]):
        # The Hearing downgraded the claim, so no case was opened; this approval is the student's explicit OK.
        await ask(ctx, "CASEWORKER", OpenCases(profile_id=profile["_id"]), CasesResult)
        result = await ask(ctx, "CASEWORKER", CaseDecision(profile_id=profile["_id"], approved=True), DecisionResult)
    if result is None:
        return UNAVAILABLE
    if not result.acted:
        return "There's nothing waiting for your approval right now. Say **check my pay** to look for issues."
    if approved:
        return (f"Approved. I'm contacting payroll about your **{dollars(result.amount_cents)}** refund. "
                "I'll log the call and tell you what they promise.")
    return "Okay, I won't contact payroll. The issue stays on your file; say **check my pay** any time to reopen it."


def latest_news() -> str:
    """'any update?': the same news a proactive message would have carried, read from Convex, so it works
    even if the chat never showed the unprompted message."""
    profile = demo_profile()
    if profile is None:
        return "I don't have a student file yet."
    cases = query("cases:listByProfile", {"profileId": profile["_id"]})
    log(AGENT, "update_requested", f"{len(cases)} cases on file", inputIds=[profile["_id"]])
    if not cases:
        return "No open cases. Say **check my pay** and I'll look at your latest paystubs."
    case = max(cases, key=lambda c: c["_creationTime"])
    amount = dollars(case["amountCents"])
    if case["state"] == "closed" and case.get("outcome") == "refunded":
        return (f"Good news: your **{amount}** refund landed in your account. It matched your refund case, "
                "so I've closed it.")
    if case["state"] == "awaiting_response":
        return f"Payroll promised your **{amount}** refund by {case['nextFollowUp']}. I'm watching your bank for it."
    return f"Your **{amount}** refund case is {CASE_STATUS.get(case['state'], case['state'])}."


def give_ok(profile_id: str) -> bool:
    """A downgraded refund finding waits for the student's OK; record it so the Caseworker can open the case."""
    for flag in query("flags:listByProfile", {"profileId": profile_id}):
        if flag["ruleId"] == "FICA_EXEMPT_F1" and flag["status"] == "needs_student_ok":
            mutation("flags:setStatus", {"flagId": flag["_id"], "status": "open"})
            log(AGENT, "student_ok_given", "Student approved going ahead despite the downgraded verdict",
                inputIds=[flag["_id"]])
            return True
    return False


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
    if action == "show_hearing":
        return await replay_hearing(selection.get("flag_id"))
    if action in ("join_group", "decline_group"):
        return await asyncio.to_thread(answer_group, selection.get("group_id"), action == "join_group")
    if action in ("approve_document", "decline_document"):
        return await asyncio.to_thread(decide_document, selection.get("document_id"),
                                       action == "approve_document")
    if action == "save_contact":
        return await asyncio.to_thread(save_contact, selection)
    return f"I got your {action.replace('_', ' ')} selection, but I can't act on it yet."


# ---------- group cases, documents and how Docket reaches her ----------

def answer_group(group_id: str | None, join: bool) -> str:
    profile = demo_profile()
    if profile is None:
        return "I don't have a student file yet."
    pending = query("groups:pendingInvite", {"profileId": profile["_id"]})
    group_id = group_id or (pending or {}).get("group", {}).get("_id")
    if not group_id:
        return "There's no group request waiting for your answer right now."
    mutation("groups:respond", {"groupId": group_id, "profileId": profile["_id"], "join": join,
                                "via": "ASI:One"})
    if join:
        return ("You're in. I'll add you to the combined request and keep your own case running "
                "exactly as it is. I'll tell you what payroll says.")
    return "No problem, I've left you out of the group. Your own case isn't affected."


def group_status() -> list:
    """'what about other students?': the invitation if one is waiting, else where the group stands."""
    profile = demo_profile()
    if profile is None:
        return ["I don't have a student file yet."]
    pending = query("groups:pendingInvite", {"profileId": profile["_id"]})
    if pending:
        group, count = pending["group"], pending["inviteeCount"]
        log(AGENT, "group_invite_shown", f"Showed the {group['employer']} group invitation",
            inputIds=[profile["_id"], group["_id"]])
        return [group_invite(group["employer"], count, group["_id"],
                             f"{count} students at {group['employer']} have the same problem you do.")]
    mine = query("groups:forProfile", {"profileId": profile["_id"]})
    if not mine:
        return ["No one else on Docket has the same problem at your employer yet. If that changes, "
                "I'll ask whether you want to join them."]
    lines = []
    for row in mine:
        group, state = row["group"], row["membership"]["state"]
        if state == "joined":
            lines.append(f"You're in the {group['employer']} group request: {group['joinedCount']} "
                         f"students, **{dollars(group['joinedCents'])}** between them.")
        elif state == "declined":
            lines.append(f"You chose not to join the {group['employer']} group. Say **join the group** "
                         f"if you change your mind.")
    return ["\n".join(lines) or "Nothing to report on group requests."]


def decide_document(document_id: str | None, approved: bool) -> str:
    profile = demo_profile()
    if profile is None:
        return "I don't have a student file yet."
    if not document_id:
        waiting = query("documents:nextAwaitingApproval", {"profileId": profile["_id"]})
        document_id = (waiting or {}).get("_id")
    if not document_id:
        return "There's no document waiting for your approval."
    document = query("documents:get", {"documentId": document_id})
    mutation("documents:decide", {"documentId": document_id, "approved": approved, "via": "ASI:One"})
    if not approved:
        return (f"Okay, I won't send your {document['title']}. It stays on your file; "
                f"say **my forms** when you want to look at it again.")
    if document["submitTo"] == "IRS":
        return (f"Approved. Your {document['title']} is signed off and the PDF is on your file. "
                f"I can't file with the IRS for you, so print it, sign it and post it to the address "
                f"in the instructions. I'll remind you if it's still unsent.")
    return f"Approved. I'm sending your {document['title']} to {document['submitTo']}."


def documents_reply() -> list:
    """'my forms': what's filled in, what's waiting on her, what's done."""
    profile = demo_profile()
    if profile is None:
        return ["I don't have a student file yet."]
    documents = query("documents:forProfile", {"profileId": profile["_id"]})
    log(AGENT, "documents_listed", f"{len(documents)} documents on file", inputIds=[profile["_id"]])
    if not documents:
        return ["I haven't filled in any forms for you yet. Say **check my pay** and I'll look at "
                "what you need."]
    waiting = next((d for d in documents if d["state"] == "awaiting_approval"), None)
    parts: list = []
    if waiting:
        parts.append(document_review(
            waiting["title"], waiting["submitTo"], waiting["fields"], waiting["_id"],
            f"I've filled in your {waiting['title']} from your file. Every value shows where it came "
            f"from. Nothing goes to {waiting['submitTo']} until you approve it."))
    done = [d for d in documents if d["state"] in ("approved", "submitted")]
    if done:
        parts.append("Already signed off:\n" + "\n".join(
            f"- {d['title']}" + (f" (reference {d['submissionRef']})" if d.get("submissionRef") else "")
            for d in done))
    if not parts:
        parts.append("Nothing is waiting on you. I'll tell you when a form is due.")
    return parts


def save_contact(selection: dict) -> str:
    profile = demo_profile()
    if profile is None:
        return "I don't have a student file yet."
    phone = str(selection.get("phone") or "").strip()
    changes: dict = {}
    if phone:
        cleaned = re.sub(r"[\s\-().]", "", phone)
        if not re.fullmatch(r"\+[1-9]\d{7,14}", cleaned):
            return (f"I didn't save that: {phone!r} isn't a full number with a country code. "
                    "It should look like +14155550123. Say **update my contact details** to try again.")
        changes["phone"] = cleaned
    for key, field in (("voiceConsent", "voice_consent"), ("smsConsent", "sms_consent")):
        if field in selection:
            changes[key] = str(selection[field]).strip().lower() in {"1", "true", "yes", "on"}
    preference = selection.get("group_preference")
    if preference in ("ask", "always", "never"):
        changes["groupPreference"] = preference
    if not changes:
        return "Nothing to save. Say **update my contact details** to fill in the form."
    mutation("profiles:setContact", {"profileId": profile["_id"], **changes})
    calling = changes.get("voiceConsent", profile.get("voiceConsent"))
    texting = changes.get("smsConsent", profile.get("smsConsent"))
    how = ", ".join(filter(None, ["call you" if calling else None, "text you" if texting else None]))
    return (f"Saved. I'll {how} when something needs you." if how
            else "Saved. I won't call or text you; I'll keep everything here in chat.")


async def research_reply(ctx: Context, text: str) -> list:
    """A question the file can't answer goes to the Athena research agent."""
    profile = await asyncio.to_thread(demo_profile)
    if profile is None:
        return ["I don't have a student file yet."]
    await asyncio.to_thread(log, AGENT, "research_requested", f"Question for the researcher: {text[:120]}",
                            inputIds=[profile["_id"]])
    reply = await ask(ctx, "RESEARCHER", ResearchQuestion(profile_id=profile["_id"], question=text,
                                                          asked_via="chat"), ResearchAnswer)
    if reply is None or not reply.answer:
        return ["I couldn't research that reliably just now, and I'd rather not guess. "
                "Please ask your international student office, and I'll keep trying."]
    return [f"{reply.answer}\n\n{NOT_ADVICE}"]


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
    if re.fullmatch(r"(why|why\?|why is that\??|explain the hearing)", t):
        return await replay_hearing()
    if re.search(r"\bany (update|news)s?\b|\bwhat'?s new\b|\bcase status\b|\bstatus of my (case|refund)\b", t):
        return await asyncio.to_thread(latest_news)
    # Matched in code, not by Claude: these change consent or send a document, so a misread
    # message must not be able to trigger them.
    if re.search(r"\bjoin the group\b|\bjoin them\b|\bcount me in\b", t):
        return await asyncio.to_thread(answer_group, None, True)
    if re.search(r"\bleave the group\b|\bnot the group\b|\bdon'?t join\b", t):
        return await asyncio.to_thread(answer_group, None, False)
    if re.search(r"\bmy forms?\b|\bmy documents?\b|\bwhat do i (need to )?file\b", t):
        return await asyncio.to_thread(documents_reply)
    if re.search(r"\banyone else\b|\bother students?\b|\bgroup (case|request)\b", t):
        return await asyncio.to_thread(group_status)
    if re.search(r"\bcall me\b|\btext me\b|\bmy (phone|number)\b|\bcontact details\b|\bstop (calling|texting)\b", t):
        return [await asyncio.to_thread(contact_card)]

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
    if intent == "check_pay":
        return await check_pay(ctx)
    if intent == "contact":
        return [await asyncio.to_thread(contact_card)]
    if intent == "documents":
        return await asyncio.to_thread(documents_reply)
    if intent == "group":
        return await asyncio.to_thread(group_status)
    if intent == "research":
        return await research_reply(ctx, text)
    return await explain_with_claude(ctx, text, intent)


def contact_card() -> Card:
    profile = demo_profile()
    return contact_form((profile or {}).get("phone"))


def season_reply() -> str:
    profile = demo_profile()
    if profile is None:
        return "I don't have a student file yet."
    paystubs = query("paystubs:listByProfile", {"profileId": profile["_id"]})
    log(AGENT, "next_season_explained", f"Next-season checklist for {profile['name']}", inputIds=[profile["_id"]])
    return f"{next_season(profile, paystubs, SCHOOL_CALENDAR, date.today())}\n\n{NOT_ADVICE}"
