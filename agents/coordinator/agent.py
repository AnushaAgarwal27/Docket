"""Coordinator: the only agent Priya talks to, through ASI:One.

Run from the repo root: .venv/bin/python -m agents.coordinator.agent
Wait for "registered as mailbox agent", then use Chat with Agent in ASI:One.

Besides answering, it messages Priya first when another agent reports news (Tax found issues on new
paystubs, a refund landed), using the ASI:One address she last chatted from.
"""

import asyncio
import json
import os
import re
from collections import defaultdict, deque
from datetime import datetime, timezone
from uuid import uuid4

from dotenv import load_dotenv
from uagents import Agent, Context, Protocol
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    EndSessionContent,
    TextContent,
    chat_protocol_spec,
)

from agents.coordinator.intents import answer
from agents.messages import PORTS, FindingsReady, LocalFirstResolver, RefundLanded, address_of
from agents.store import dollars, log

load_dotenv()

agent = Agent(name="docket-coordinator", seed=os.environ["COORDINATOR_SEED"], port=8001, mailbox=True,
              resolve=LocalFirstResolver())
chat = Protocol(spec=chat_protocol_spec)

# Echo guard: ASI:One sometimes sends our own reply back as a new request.
recent_replies: dict[str, deque] = defaultdict(lambda: deque(maxlen=5))

DOCKET_AGENTS = {address_of(name) for name in PORTS}
STUDENT_KEY = "student_address"  # where proactive messages go; kept in the agent's storage


def reply(text: str) -> ChatMessage:
    return ChatMessage(
        timestamp=datetime.now(timezone.utc),
        msg_id=uuid4(),
        content=[TextContent(type="text", text=text), EndSessionContent(type="end-session")],
    )


@chat.on_message(ChatMessage)
async def on_chat(ctx: Context, sender: str, msg: ChatMessage):
    await ctx.send(sender, ChatAcknowledgement(timestamp=datetime.now(timezone.utc), acknowledged_msg_id=msg.msg_id))
    if sender not in DOCKET_AGENTS:
        ctx.storage.set(STUDENT_KEY, sender)
    for item in msg.content:
        if not isinstance(item, TextContent):
            continue
        # ASI:One prefixes the text with "@agent1..." when the user mentions us.
        text = re.sub(r"@agent1\w+", "", item.text).strip()
        ctx.logger.info(f"from {sender[:16]}: {text!r}")
        # Echoes can come back wrapped as "[docket-coordinator]: <our reply>".
        if any(r in text for r in recent_replies[sender]) or text.startswith("[docket-coordinator]"):
            ctx.logger.info("echo ignored")
            continue
        response = await answer(ctx, text)
        recent_replies[sender].append(response)
        await ctx.send(sender, reply(response))


@chat.on_message(ChatAcknowledgement)
async def on_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    pass


async def tell_student(ctx: Context, text: str, action: str, detail: str, **ids) -> None:
    """Message Priya without being asked, or log why not."""
    to = ctx.storage.get(STUDENT_KEY)
    if to is None:
        await asyncio.to_thread(log, "coordinator", "proactive_message_skipped",
                                f"{detail}; Priya has not chatted with Docket yet", **ids)
        return
    await ctx.send(to, reply(text))
    recent_replies[to].append(text)
    await asyncio.to_thread(log, "coordinator", action, detail, **ids)


@agent.on_message(RefundLanded)
async def on_refund(ctx: Context, sender: str, msg: RefundLanded):
    if sender != address_of("LEDGER"):
        return  # only the Ledger can report a refund
    amount = dollars(msg.amount_cents)
    await tell_student(
        ctx,
        f"Good news: a **{amount}** deposit from {msg.counterparty} just landed in your account. "
        f"It matches your refund case, so I've closed it.",
        "proactive_message_sent", f"Told Priya her {amount} refund landed (case {msg.case_id})",
        inputIds=[msg.case_id])


@agent.on_message(FindingsReady)
async def on_findings(ctx: Context, sender: str, msg: FindingsReady):
    if sender != address_of("TAX"):
        return
    flags = json.loads(msg.flags_json)
    if not flags:
        text = f"I just read {msg.paystub_count} new paystubs. Nothing looks wrong."
    else:
        lines = [f"I just read {msg.paystub_count} new paystubs and noticed "
                 f"{len(flags)} likely issue{'s' if len(flags) > 1 else ''}:"]
        lines += [f"- {f['explanation']}" for f in flags]
        lines.append("Say **check my pay** to see the official rule behind each one and what I can do about it.")
        text = "\n".join(lines)
    await tell_student(ctx, text, "proactive_message_sent",
                       f"Told Priya about {len(flags)} issues found on {msg.paystub_count} new paystubs",
                       inputIds=[msg.profile_id])


agent.include(chat, publish_manifest=True)

if __name__ == "__main__":
    agent.run()
