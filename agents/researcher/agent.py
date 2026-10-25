"""Athena research agent: answers what the student file cannot, and watches for what changes it.

    .venv/bin/python -m agents.researcher.agent

Three ways work arrives:

    a question she asked on the phone   the voice tool records it in researchRequests; the interval
                                        below picks it up, researches it, and messages her the answer
    a question she asked in chat        the Coordinator sends ResearchQuestion and waits for the answer
    nobody asked                        the watch interval reads the official pages and the news for
                                        the rules that actually fired on her file, and raises a
                                        finding only when one of them changed what she should do

Nothing it finds is stated as fact unless code fetched the page and found the claim on it
(agents/researcher/athena.py). An unverifiable answer is sent with its uncertainty attached.
"""

import asyncio
import json
import os
from pathlib import Path

from dotenv import load_dotenv
from uagents import Agent, Context

from agents.agentverse import add_mailbox_check
from agents.chat import add_chat, no_student, student
from agents.messages import (
    PORTS, LocalFirstResolver, ResearchAnswer, ResearchQuestion, address_of,
)
from agents.messaging import heard
from agents.researcher import athena, engine
from agents.store import log, query

load_dotenv()

agent = Agent(name="docket-researcher", seed=os.environ["RESEARCHER_SEED"], port=PORTS["RESEARCHER"],
              mailbox=True, resolve=LocalFirstResolver(),
              description="Researches F-1 pay, tax and status questions against official sources and the "
                          "news, and verifies every source in code before Docket repeats it.",
              readme_path=str(Path(__file__).with_name("AGENTVERSE.md")),
              publish_agent_details=True)
add_mailbox_check(agent, "researcher", PORTS["RESEARCHER"])

WATCH_SECONDS = float(os.environ.get("RESEARCH_WATCH_SECONDS", "900"))
ASK_SECONDS = float(os.environ.get("RESEARCH_ASK_SECONDS", "20"))


@agent.on_message(ResearchQuestion, replies=ResearchAnswer)
async def on_question(ctx: Context, sender: str, msg: ResearchQuestion):
    """A question from the Coordinator, answered inline so the chat can show it straight away."""
    await heard("researcher", sender, msg, f"question: {msg.question[:80]}", inputIds=[msg.profile_id])
    try:
        profile = await asyncio.to_thread(query, "profiles:get", {"profileId": msg.profile_id})
        if profile is None:
            await ctx.send(sender, ResearchAnswer(profile_id=msg.profile_id, answer="", error="no such student"))
            return
        flags = await asyncio.to_thread(query, "flags:listByProfile", {"profileId": msg.profile_id})
        question = engine.scrub(msg.question, profile)
        finding = await asyncio.to_thread(athena.research, question, engine.public_context(profile, flags))
        if not finding.ok:
            await ctx.send(sender, ResearchAnswer(profile_id=msg.profile_id, answer="", error=finding.error[:300]))
            return
        await asyncio.to_thread(engine.store, msg.profile_id, "ask", engine.topic_for(question),
                                finding, msg.question, True)
        await ctx.send(sender, ResearchAnswer(
            profile_id=msg.profile_id,
            answer=await asyncio.to_thread(engine.message_for, profile, finding, msg.question),
            sources_json=json.dumps([{"title": s.title, "url": s.url} for s in finding.sources if s.verified]),
            confidence=finding.confidence, engine=finding.engine))
    except Exception as e:
        ctx.logger.exception("research failed")
        await ctx.send(sender, ResearchAnswer(profile_id=msg.profile_id, answer="", error=str(e)[:300]))


@agent.on_interval(period=ASK_SECONDS)
async def answer_questions_from_calls(ctx: Context):
    """Questions taken on the phone. The call promised her an answer; this is what keeps that promise."""
    try:
        answered = await asyncio.to_thread(engine.answer_pending)
        if answered:
            ctx.logger.info(f"answered {answered} question(s) asked on a call")
        sent = await asyncio.to_thread(engine.notify_unsent)
        if sent:
            ctx.logger.info(f"sent {sent} research update(s)")
    except Exception:
        ctx.logger.exception("answering pending questions failed")


@agent.on_interval(period=WATCH_SECONDS)
async def watch(ctx: Context):
    """Nobody asked: read the official pages and the news for the rules that bear on this student."""
    if not (athena.asi_one_available() or os.environ.get("ANTHROPIC_API_KEY")):
        await asyncio.to_thread(log, "researcher", "watch_skipped",
                                "No research engine configured: set ASI_ONE_API_KEY or ANTHROPIC_API_KEY")
        return
    try:
        found = await asyncio.to_thread(engine.run_watch)
        if found:
            ctx.logger.info(f"{found} watch finding(s) worth telling the student about")
    except Exception:
        ctx.logger.exception("the watch run failed")


# --- ASI:One ------------------------------------------------------------------
# Research this agent has done. Every source was re-fetched and had to contain the claim's wording.
def answer(question: str) -> str:
    from agents.store import query
    p = student()
    rows = query("research:forProfile", {"profileId": p["_id"], "limit": 4}) if p else []
    out = ["I'm Athena, Docket's research agent. I answer what the student's own file can't, on "
           "ASI:One's agentic models, and then every source I cite is fetched again in code and "
           "has to actually contain what I said. One that doesn't is dropped, and an answer left "
           "with no surviving source is marked low confidence and never stated as fact.\n"]
    if not rows:
        out.append("I haven't been asked anything yet for this student.")
    else:
        for r in rows:
            out.append(f"**{(r.get('question') or 'a question')[:160]}**")
            out.append(f"{(r.get('answer') or '')[:320]}")
            srcs = r.get("sources") or []
            for s in srcs[:3]:
                url = s.get("url") if isinstance(s, dict) else str(s)
                out.append(f"- {url}")
            out.append(f"*confidence: {r.get('confidence', 'unknown')}, {len(srcs)} verified sources*\n")
    out.append("Ask **docket-coordinator** an F-1 pay, tax or status question and it reaches me.")
    return "\n".join(out)


add_chat(agent, "researcher", answer)


if __name__ == "__main__":
    agent.run()
