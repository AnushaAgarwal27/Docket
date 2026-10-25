"""The chat protocol for Docket's specialist agents, so each one is reachable in ASI:One.

ASI:One can only find and talk to an agent that speaks the chat protocol. The Coordinator always
has: it is the one the student talks to, and it owns the conversation, the cards and the approvals.
The other seven spoke only typed messages to each other, so searching "docket-" in ASI:One returned
the Coordinator and nothing else -- the agents were registered, running and talking, but invisible.

This gives each specialist a chat protocol of its own, answering for the one thing it owns: ask the
Ledger what it read, the Tax agent which rules fired, the Auditor what it objected to. The answers
are read from the shared student file, which is the same place the agent's own work goes, so an
agent cannot describe work it did not do.

What they deliberately do not do is act. A specialist will not open a case, approve anything, or
place a call from chat, no matter how it is asked: those decisions belong to the student, through
the Coordinator, where the approval is recorded. Asking here gets you pointed back there.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Callable
from uuid import uuid4

from uagents import Agent, Context, Protocol
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    EndSessionContent,
    TextContent,
    chat_protocol_spec,
)

from agents.store import log

# Said when the specialist is asked to do something only the student can authorise.
ONLY_THE_STUDENT = (
    "I can tell you what I found, but I can't act on it. Opening a case, contacting an employer or "
    "sending anything needs the student's own approval, which happens with **docket-coordinator** "
    "in ASI:One. Ask it to \"check my pay\"."
)

# Words that mean "go do it" rather than "tell me". Matched in code: a specialist must not be
# talked into acting by phrasing, so this never reaches a model.
ACTIONS = ("approve", "call payroll", "contact payroll", "place the call", "submit", "file it",
           "send it", "open a case", "do it for me", "go ahead")


def wants_action(text: str) -> bool:
    low = text.lower()
    return any(word in low for word in ACTIONS)


def add_chat(agent: Agent, name: str, answer: Callable[[str], str]) -> None:
    """Give `agent` the chat protocol. `answer(question) -> str` reports what this agent owns.

    It runs in a thread because every answer reads the student file over HTTP, and a specialist
    that blocks its event loop stops answering its own agent-to-agent messages too.
    """
    chat = Protocol(spec=chat_protocol_spec)

    @chat.on_message(ChatMessage)
    async def on_chat(ctx: Context, sender: str, msg: ChatMessage):
        # Acknowledge first, so ASI:One knows it arrived even if answering fails.
        await ctx.send(sender, ChatAcknowledgement(
            timestamp=datetime.now(timezone.utc), acknowledged_msg_id=msg.msg_id))
        for item in msg.content:
            if not isinstance(item, TextContent):
                continue
            question = item.text.strip()
            if wants_action(question):
                await ctx.send(sender, _reply(ONLY_THE_STUDENT))
                return
            try:
                text = await asyncio.to_thread(answer, question)
            except Exception as e:  # noqa: BLE001 - a specialist must still reply
                ctx.logger.exception("answering a chat message failed")
                text = (f"I couldn't read the student file just now ({type(e).__name__}), so I'd "
                        f"rather say nothing than guess.")
            try:
                await asyncio.to_thread(log, name, "chat_answered", question[:200])
            except Exception:  # noqa: BLE001 - never fail the reply over the activity log
                pass
            await ctx.send(sender, _reply(text))
            return

    @chat.on_message(ChatAcknowledgement)
    async def on_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
        ctx.logger.debug(f"ack from {sender[:18]} for {msg.acknowledged_msg_id}")

    agent.include(chat, publish_manifest=True)


def _reply(text: str) -> ChatMessage:
    return ChatMessage(
        timestamp=datetime.now(timezone.utc),
        msg_id=uuid4(),
        content=[TextContent(type="text", text=text), EndSessionContent(type="end-session")],
    )


def student() -> dict | None:
    """The one real student file. Simulated cohort profiles are never it."""
    from agents.store import query
    return next((p for p in query("profiles:list") if not p.get("simulated")), None)


def no_student() -> str:
    return ("There's no student file on this deployment yet, so I have nothing to report. "
            "Whoever is running Docket needs to seed one first.")
