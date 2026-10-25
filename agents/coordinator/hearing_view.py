"""How the Coordinator shows a Hearing in chat: short narration messages, then a detail card.

Built only from the hearing stored in Convex (rounds, verdict, reason) and the claim's stored facts, so
"why?" can replay it later without calling Claude.
"""
from __future__ import annotations

import os

from agents.auditor.verdict import OBJECTION_LABEL, PART_LABEL, verdict_line
from agents.coordinator.cards import Card, finding_detail
from agents.store import dollars

FICA = "FICA_EXEMPT_F1"
HOURS = "ONCAMPUS_20_HOURS"
TITLE = {FICA: "Social Security and Medicare withheld", HOURS: "Over 20 hours in a school week"}
CONFIDENCE = {"upheld": "high confidence", "downgraded": "medium confidence: an exception may apply",
              "needs_human": "low confidence: a person needs to check", "defeated": "not owed back"}
OUTCOME_MARK = {"rebutted": "rebutted", "conceded": "conceded", "unresolved": "unresolved"}


def single_message() -> bool:
    """HEARING_STYLE=single sends the narration as one message, for chats that show only one reply."""
    return os.environ.get("HEARING_STYLE", "multi").lower() == "single"


def narrate(hearing: dict) -> list[str]:
    """4-6 short messages: the claim, each objection with its answer, the verdict reason."""
    rounds = hearing["rounds"]
    title = TITLE.get(hearing["ruleId"], hearing["ruleId"])
    messages = [f"**The Hearing: {title}**\nAdvocate (Tax agent): {rounds[0]['argument']}"]
    answers = {r.get("objectionId"): r for r in rounds[1:] if r["side"] == "advocate"}
    objections = [r for r in rounds[1:] if r["side"] == "auditor"]
    lines = []
    for o in objections:
        a = answers.get(o.get("objectionId"))
        label = OBJECTION_LABEL.get(o.get("objectionId"), "Objection")
        text = f"**Auditor, {label}** {o['argument']}"
        if a:
            text += f"\nAdvocate: {a['argument']}"
        lines.append(text)
    # Keep the whole Hearing at 4-6 messages: group objections when there are many.
    while len(lines) > 4:
        lines[-2:] = ["\n\n".join(lines[-2:])]
    messages += lines
    messages.append(f"**Verdict: {verdict_line_from(hearing)}.** {hearing['reason']}")
    return ["\n\n".join(messages)] if single_message() else messages


def verdict_line_from(hearing: dict) -> str:
    parts = parts_from(hearing)
    return verdict_line({"verdict": hearing["verdict"], "parts": parts})


def parts_from(hearing: dict) -> dict:
    """Per-part verdicts, recovered from the stored rounds (conceded Medicare objection -> Medicare downgraded)."""
    if hearing["ruleId"] != FICA or hearing["verdict"] in ("defeated", "needs_human"):
        return {}
    parts = {"social_security": "upheld", "medicare": "upheld"}
    for r in hearing["rounds"]:
        if r["side"] == "advocate" and r.get("objectionId") and r["argument"].endswith("[conceded]"):
            if r["objectionId"] == "medicare_recovery_uncertain":
                parts["medicare"] = "downgraded"
            elif r["objectionId"] == "student_exception_applies":
                parts = {p: "downgraded" for p in parts}
    return parts


def detail_card(hearing: dict, flag: dict | None, quote: str | None, source_title: str | None) -> Card:
    """The finding with its verdict: Social Security and Medicare as separate rows with their own confidence."""
    rid = hearing["ruleId"]
    parts = parts_from(hearing)
    rows = []
    if rid == FICA and flag is not None and "ssCents" in flag:
        for part, cents in (("social_security", flag["ssCents"]), ("medicare", flag["medicareCents"])):
            rows.append((PART_LABEL[part], f"{dollars(cents)} · {CONFIDENCE[parts.get(part, hearing['verdict'])]}"))
        rows.append(("Total withheld", dollars(flag["amountCents"])))
    elif rid == FICA:
        rows.append(("Social Security and Medicare", CONFIDENCE[hearing["verdict"]]))
    elif rid == HOURS:
        rows.append(("Finding", flag["explanation"].split(". Confirm")[0] if flag else "A week over 20 hours"))
    text = {"upheld": "The Hearing is over: the claim was upheld.",
            "downgraded": "The Hearing is over: the claim stands, with an exception you should know about.",
            "needs_human": "The Hearing is over, but I need more facts before I can act.",
            "defeated": "The Hearing is over: the Auditor won, so there is no claim."}[hearing["verdict"]]
    return finding_detail(TITLE.get(rid, rid), rows, quote, source_title, verdict_line_from(hearing),
                          hearing.get("flagId"), f"{text} Confirm with your school's international office.")


def defeated_message(hearing: dict) -> str:
    conceded = next((r["argument"].removesuffix(" [conceded]") for r in hearing["rounds"]
                     if r["side"] == "advocate" and r["argument"].endswith("[conceded]")), hearing["reason"])
    return f"No refund claim. {conceded} Confirm with your school's international office."
