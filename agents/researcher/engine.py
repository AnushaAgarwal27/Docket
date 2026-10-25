"""What the research agent actually does with its two jobs.

Both jobs send text to a third-party research service, so both go through the same two guards first:

  * the context is built from `guard.redact(facts, "public")`, which allows visa category, rule id
    and employer *kind* and nothing else. No name, no amounts, no employer name, no school.
  * the student's own question is scrubbed in code for her name, phone and employer before it
    leaves the machine. Code, not a model, does this: a redaction that is sometimes skipped is
    not a redaction.

What comes back is checked by athena.verify_sources, then written to Convex with its sources, then
turned into a message for the student by agents/guard.py. The student never sees raw engine output.
"""
from __future__ import annotations

import re

from agents import guard
from agents.researcher import athena
from agents.store import log, mutation, query

AGENT = "researcher"

# What the watch job asks about, built per student from what is actually on her file.
BASE_TOPICS = [
    ("FICA refunds for nonresident students",
     "Has the IRS changed anything recently about Social Security and Medicare tax refunds for "
     "nonresident alien students on F-1 visas, or about Form 843 and Form 8316?"),
    ("Form 8843 filing",
     "What is the current deadline and filing requirement for Form 8843 for F-1 students with no "
     "US income, and has it changed for the current tax year?"),
    ("F-1 employment rules",
     "Have there been recent changes to on-campus employment limits, OPT, or F-1 work authorisation "
     "rules that would affect a student's ability to work or their status?"),
]

RULE_TOPICS = {
    "ONCAMPUS_20_HOURS": ("On-campus hour limits",
                          "Have the rules on the 20-hour-per-week on-campus work limit for F-1 "
                          "students changed, including what counts as school being in session?"),
    "OPT_UNEMPLOYMENT_90": ("OPT unemployment days",
                            "Have the OPT unemployment day limits or reporting requirements for F-1 "
                            "students changed recently?"),
}


def scrub(text: str, profile: dict) -> str:
    """Remove the things that identify this student, in code, before anything leaves the machine."""
    out = text
    for part in (profile.get("name") or "").split():
        if len(part) > 2:
            out = re.sub(rf"\b{re.escape(part)}\b", "a student", out, flags=re.I)
    for key, replacement in (("employer", "her employer"), ("school", "her university")):
        value = profile.get(key)
        if value and len(str(value)) > 3:
            out = re.sub(re.escape(str(value)), replacement, out, flags=re.I)
    out = re.sub(r"\+?\d[\d\-.\s()]{7,}\d", "[number removed]", out)
    out = re.sub(r"[\w.+-]+@[\w-]+\.[\w.]+", "[email removed]", out)
    return out


def public_context(profile: dict, flags: list[dict]) -> str:
    """The only facts a third-party research service is given. Built by allow-list, not by trimming."""
    facts = {
        "visa": profile.get("visa"),
        "rule": ", ".join(sorted({f["ruleId"] for f in flags})) or None,
        "employer_kind": "on-campus university employer" if profile.get("employerIsSchool") else None,
        "state": "United States",
    }
    allowed = guard.redact(facts, "public")
    lines = [f"{k}: {v}" for k, v in allowed.items() if v]
    return ("Context (no identifying details):\n" + "\n".join(lines)) if lines else ""


# ---------------------------------------------------------------------------
# ask: a question from a phone call or chat
# ---------------------------------------------------------------------------

def answer_pending(limit: int = 5) -> int:
    """Research every question waiting on the agent and send the answer back. Returns how many."""
    requests_ = query("voice:pendingResearch", {"limit": limit})
    for request in requests_:
        _answer_one(request)
    return len(requests_)


def _answer_one(request: dict) -> None:
    profile = query("profiles:get", {"profileId": request["profileId"]})
    if profile is None:
        mutation("voice:resolveResearch", {"requestId": request["_id"], "error": "no such student"})
        return
    flags = query("flags:listByProfile", {"profileId": profile["_id"]})
    question = scrub(request["question"], profile)
    log(AGENT, "research_started", f"Researching: {question[:160]}", inputIds=[profile["_id"]])

    finding = athena.research(question, public_context(profile, flags))
    if not finding.ok:
        mutation("voice:resolveResearch", {"requestId": request["_id"], "error": finding.error[:300]})
        log(AGENT, "research_failed", finding.error[:300], inputIds=[profile["_id"]])
        notify(profile, "research",
               "Docket could not research your question",
               "I couldn't get a reliable answer to your question just now. I haven't guessed at one. "
               "Please ask your international student office, and I'll try again later.",
               refs=[request["_id"]])
        return

    research_id = store(profile["_id"], "ask", topic_for(question), finding,
                        question=request["question"], actionable=True)
    mutation("voice:resolveResearch", {"requestId": request["_id"], "researchId": research_id})
    notify(profile, "research", "Docket researched your question",
           message_for(profile, finding, request["question"]), refs=[research_id])


def topic_for(question: str) -> str:
    words = re.sub(r"[^\w\s]", "", question).split()
    return " ".join(words[:8]) + ("…" if len(words) > 8 else "")


# ---------------------------------------------------------------------------
# watch: news and official pages, on an interval
# ---------------------------------------------------------------------------

def topics_for(profile: dict, flags: list[dict]) -> list[tuple[str, str]]:
    topics = list(BASE_TOPICS)
    for flag in flags:
        extra = RULE_TOPICS.get(flag["ruleId"])
        if extra and extra not in topics:
            topics.append(extra)
    return topics


def run_watch(profile_id: str | None = None) -> int:
    """Research each watch topic for the student and record anything that changes what she should do."""
    profile = (query("profiles:get", {"profileId": profile_id}) if profile_id
               else next((p for p in query("profiles:list") if not p.get("simulated")), None))
    if profile is None:
        return 0
    flags = query("flags:listByProfile", {"profileId": profile["_id"]})
    seen = {r["topic"] for r in query("research:forProfile", {"profileId": profile["_id"], "limit": 50})}
    found = 0
    for topic, question in topics_for(profile, flags):
        if topic in seen:
            continue  # already looked into; the interval re-run is for new topics, not repeats
        finding = athena.research(question, public_context(profile, flags))
        if not finding.ok:
            log(AGENT, "watch_failed", f"{topic}: {finding.error[:200]}")
            continue
        # Only a finding with a verified source is worth interrupting someone over.
        actionable = finding.confidence in {"high", "medium"}
        store(profile["_id"], "watch", topic, finding, actionable=actionable)
        found += actionable
    return found


def notify_unsent(limit: int = 5) -> int:
    """Text the student about watch findings nobody has told her about yet."""
    rows = query("research:unnotified", {"limit": limit})
    sent = 0
    for row in rows:
        if not row.get("profileId"):
            continue
        profile = query("profiles:get", {"profileId": row["profileId"]})
        if profile is None:
            continue
        finding = athena.Finding(
            answer=row["answer"], engine=row["engine"], confidence=row["confidence"],
            sources=[athena.Source(title=s["title"], url=s["url"], excerpt=s.get("excerpt", ""),
                                   verified=True) for s in row["sources"]])
        notify(profile, "research", f"Update: {row['topic']}", message_for(profile, finding))
        mutation("research:markNotified", {"researchId": row["_id"]})
        sent += 1
    return sent


# ---------------------------------------------------------------------------
# Storing and telling
# ---------------------------------------------------------------------------

def store(profile_id: str | None, kind: str, topic: str, finding: athena.Finding,
          question: str | None = None, actionable: bool = True) -> str:
    """`profile_id` is None for a finding that applies to every F-1 student, not just this one.
    The key is left out entirely in that case: Convex treats an absent optional field and an
    explicit null differently, and the validator wants it absent."""
    return mutation("research:record", {
        **({"profileId": profile_id} if profile_id else {}),
        "kind": kind,
        "topic": topic,
        "answer": finding.answer,
        "sources": [{"title": s.title, "url": s.url,
                     **({"excerpt": s.excerpt} if s.excerpt else {}),
                     **({"publishedAt": s.published_at} if s.published_at else {})}
                    for s in finding.sources if s.verified],
        "engine": finding.engine,
        "confidence": finding.confidence,
        "actionable": actionable,
        **({"question": question} if question else {}),
    })


def message_for(profile: dict, finding: athena.Finding, question: str | None = None) -> str:
    """The research answer turned into something worth reading, through the guardrail.

    The fallback is the engine's own answer trimmed in code, so a Claude outage degrades to a
    plainer message rather than to nothing.
    """
    verified = [s for s in finding.sources if s.verified]
    hedge = ("" if finding.confidence == "high" else
             " This one isn't certain, so please confirm it with your international student office.")
    fallback = guard.for_sms(finding.answer.split("\n\n")[0] + hedge, limit=guard.LIMITS["chat"])
    facts = {
        "research_topic": question or "your question",
        "research_sources": [s.title for s in verified],
        "visa": profile.get("visa"),
        "name": profile.get("name"),
    }
    rendered = guard.speak(
        purpose=("Tell the student what the research found, in a few plain sentences. "
                 "Summarise this finding faithfully and add nothing to it:\n\n" + finding.answer),
        facts=facts, channel="chat", audience="student", fallback=fallback,
        log_fn=log, agent=AGENT)
    body = rendered.text
    if verified:
        body += "\n\n" + "\n".join(f"— {s.title}: {s.url}" for s in verified[:3])
    return body + ("\n\n" + hedge.strip() if hedge else "")


def notify(profile: dict, kind: str, title: str, body: str, refs: list[str] | None = None) -> None:
    """Queue the message on every channel the student has turned on."""
    for channel in channels_for(profile):
        mutation("notifications:queue", {
            "profileId": profile["_id"], "channel": channel, "kind": kind,
            "title": title,
            "body": guard.for_sms(body) if channel == "sms" else body,
            "refs": refs or [], "awaiting": "none",
        })


def channels_for(profile: dict) -> list[str]:
    """Chat always (it is where she already talks to Docket); SMS only with consent."""
    channels = ["chat"]
    if profile.get("smsConsent") and profile.get("phone"):
        channels.append("sms")
    return channels
