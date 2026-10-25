"""Organizer agent: notices when several students have the same problem, and gets them asking together.

    .venv/bin/python -m agents.organizer.agent

It watches the flags the rules engine wrote. When enough students at one employer carry the same
finding, it opens a group case, asks each of them whether they want to join, and — for the ones who
said yes, and only those — prepares the combined request.
"""

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
from uagents import Agent, Context

from agents.agentverse import add_mailbox_check
from agents.chat import add_chat, no_student, student
from agents.messages import PORTS, GroupDecision, LocalFirstResolver, PatternFound, address_of
from agents.messaging import heard
from agents.organizer import engine
from agents.store import log, mutation

load_dotenv()

agent = Agent(name="docket-organizer", seed=os.environ["ORGANIZER_SEED"], port=PORTS["ORGANIZER"],
              mailbox=True, resolve=LocalFirstResolver(),
              description="Finds employers where several F-1 students have the same withholding error "
                          "and runs one combined refund request for the students who opt in.",
              readme_path=str(Path(__file__).with_name("AGENTVERSE.md")),
              publish_agent_details=True)
add_mailbox_check(agent, "organizer", PORTS["ORGANIZER"])

SWEEP_SECONDS = float(os.environ.get("ORGANIZER_POLL_SECONDS", "60"))


@agent.on_message(PatternFound)
async def on_pattern(ctx: Context, sender: str, msg: PatternFound):
    """The Tax agent saw the same finding land on another student at an employer it already knows."""
    await heard("organizer", sender, msg, f"{msg.flagged} flagged at {msg.employer} ({msg.rule_id})")
    try:
        await asyncio.to_thread(engine.find_and_invite)
    except Exception:
        ctx.logger.exception("forming the group after a pattern report failed")


@agent.on_message(GroupDecision)
async def on_decision(ctx: Context, sender: str, msg: GroupDecision):
    """The student answered in chat. The dashboard and the phone write the same mutation directly."""
    await heard("organizer", sender, msg, f"{'joined' if msg.join else 'declined'} group {msg.group_id}",
                inputIds=[msg.profile_id, msg.group_id])
    try:
        await asyncio.to_thread(mutation, "groups:respond", {
            "groupId": msg.group_id, "profileId": msg.profile_id, "join": msg.join, "via": "chat"})
    except Exception as e:
        ctx.logger.exception("recording the group decision failed")
        await asyncio.to_thread(log, "organizer", "group_decision_failed", str(e)[:200],
                                inputIds=[msg.profile_id, msg.group_id])


@agent.on_interval(period=SWEEP_SECONDS)
async def sweep(ctx: Context):
    """Look for new patterns, and act for the groups that have enough people in them."""
    try:
        invited = await asyncio.to_thread(engine.find_and_invite)
        if invited:
            ctx.logger.info(f"invited {invited} student(s) to a group case")
        acted = await asyncio.to_thread(engine.act_on_open_groups)
        if acted:
            ctx.logger.info(f"prepared the combined request for {acted} group(s)")
    except Exception:
        ctx.logger.exception("the organizer sweep failed")


# --- ASI:One ------------------------------------------------------------------
# Group cases. Counts only ever include students who said yes; no name or amount crosses between them.
def answer(question: str) -> str:
    from agents.store import query
    p = student()
    groups = query("groups:forProfile", {"profileId": p["_id"]}) if p else []
    out = ["I'm Docket's Organizer. When several students at one employer hit the same problem, I "
           "ask each of them whether they want to go in together. One student is easy to put off; "
           "four is a payroll configuration error.\n"]
    if not groups:
        out.append("No group has formed for this student yet.")
    else:
        for g in groups:
            out.append(f"**{g.get('employer', 'an employer')} - {g.get('state', 'forming').replace('_', ' ')}**")
            out.append(f"- {g.get('joinedCount', 0)} joined, {g.get('invitedCount', 0)} invited")
    out.append("\n**Nobody is counted until they say yes.** An invited student's amount is not in "
               "the total and their name is not in the letter. The invitation carries a count and "
               "an employer, never another student's name or what they are owed. Joining never "
               "pauses or weakens anyone's own case.")
    return "\n".join(out)


add_chat(agent, "organizer", answer)


if __name__ == "__main__":
    agent.run()
