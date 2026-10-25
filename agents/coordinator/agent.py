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
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv
from uagents import Agent, Context, Protocol
from uagents_core.contrib.protocols.chat import (
    ChatAcknowledgement,
    ChatMessage,
    EndSessionContent,
    MetadataContent,
    TextContent,
    chat_protocol_spec,
)

from agents.coordinator.cards import Card, validate
from agents.coordinator.intents import answer, answer_selection
from agents.coordinator.selection import parse_selection
from agents.agentverse import add_mailbox_check
from agents.messages import (
    PORTS, CaseOpened, DocumentReady, FindingsReady, LocalFirstResolver, RefundMatched,
    address_of, configured,
)
from agents.messaging import heard
from agents.store import dollars, log, mutation, query

load_dotenv()

agent = Agent(name="docket-coordinator", seed=os.environ["COORDINATOR_SEED"], port=8001, mailbox=True,
              resolve=LocalFirstResolver(),
              # Shown on the agent's Agentverse page; ASI:One also uses it to route students to Docket.
              description="Caseworker for F-1 students: checks paychecks for wrongly withheld Social Security "
                          "and Medicare tax, proves each issue with the official clause, and gets payroll to refund it.",
              readme_path=str(Path(__file__).with_name("AGENTVERSE.md")),
              publish_agent_details=True)
add_mailbox_check(agent, "coordinator", PORTS["COORDINATOR"])
chat = Protocol(spec=chat_protocol_spec)

# Echo guard: ASI:One sometimes sends our own reply back as a new request.
recent_replies: dict[str, deque] = defaultdict(lambda: deque(maxlen=5))

DOCKET_AGENTS = {address_of(name) for name in configured()}
STUDENT_KEY = "student_address"  # where proactive messages go; kept in the agent's storage

# Per-session state, keyed by sender and chat session: when it was last active and what it asked last.
sessions: dict[str, dict] = {}

FAILED = ("Sorry, something went wrong on my side and I couldn't finish that. Nothing was sent and no one was "
          "contacted. Please try again in a minute.")


def reply(text: str) -> ChatMessage:
    return ChatMessage(
        timestamp=datetime.now(timezone.utc),
        msg_id=uuid4(),
        content=[TextContent(type="text", text=text), EndSessionContent(type="end-session")],
    )


def to_messages(parts: list) -> list[ChatMessage]:
    """One ChatMessage per part (text, or a card with its text). Only the last one ends the session.
    A card that fails validation is sent as its text alone, which is what ASI:One would show anyway."""
    messages = []
    for i, part in enumerate(parts):
        if isinstance(part, Card):
            content = [TextContent(type="text", text=part.text)]
            problems = validate(part)
            if problems:
                try:
                    log("coordinator", "card_invalid", f"{part.kind} card sent as text: {'; '.join(problems)}"[:300])
                except Exception:  # noqa: BLE001 - the text still goes out
                    pass
            else:
                content.append(MetadataContent(type="metadata", metadata=part.metadata()))
        else:
            content = [TextContent(type="text", text=part)]
        if i == len(parts) - 1:
            content.append(EndSessionContent(type="end-session"))
        messages.append(ChatMessage(timestamp=datetime.now(timezone.utc), msg_id=uuid4(), content=content))
    return messages


def part_text(part) -> str:
    return part.text if isinstance(part, Card) else part


def session_state(ctx: Context, sender: str) -> dict:
    key = f"{sender}:{ctx.session}"
    state = sessions.setdefault(key, {"sender": sender, "session": str(ctx.session), "turns": 0})
    state["turns"] += 1
    state["last_active"] = datetime.now(timezone.utc).isoformat()
    return state


@chat.on_message(ChatMessage)
async def on_chat(ctx: Context, sender: str, msg: ChatMessage):
    # Acknowledge first, always, so ASI:One knows the message arrived even if handling fails.
    await ctx.send(sender, ChatAcknowledgement(timestamp=datetime.now(timezone.utc), acknowledged_msg_id=msg.msg_id))
    if sender not in DOCKET_AGENTS:
        ctx.storage.set(STUDENT_KEY, sender)
    state = session_state(ctx, sender)
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
        parts = await handle(ctx, text, state)
        for part in parts:
            recent_replies[sender].append(part_text(part))
        for message in await asyncio.to_thread(to_messages, parts):
            await ctx.send(sender, message)


async def handle(ctx: Context, text: str, state: dict) -> list:
    """Answer one message as a list of parts (text or cards). Never raises: a Claude or Convex failure
    becomes a plain fallback reply, and the failure is logged to activity."""
    try:
        selection = parse_selection(text)
        state["last_selection"] = selection
        out = await (answer_selection(ctx, selection) if selection is not None else answer(ctx, text))
        return out if isinstance(out, list) else [out]
    except Exception as e:  # noqa: BLE001 - the student always gets a reply
        ctx.logger.exception("handling a chat message failed")
        try:
            await asyncio.to_thread(log, "coordinator", "chat_failed", f"{type(e).__name__}: {e}"[:300])
        except Exception:  # noqa: BLE001 - Convex itself may be the failure
            ctx.logger.warning("could not log chat_failed to activity")
        return [FAILED]


@chat.on_message(ChatAcknowledgement)
async def on_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    # Did the student's chat acknowledge a message we sent unprompted? Log it, so we know whether
    # ASI:One delivers proactive messages at all.
    pending = ctx.storage.get("proactive_pending") or {}
    detail = pending.pop(str(msg.acknowledged_msg_id), None)
    if detail:
        ctx.storage.set("proactive_pending", pending)
        await asyncio.to_thread(log, "coordinator", "proactive_message_acknowledged", detail)


async def tell_student(ctx: Context, text: str, action: str, detail: str, **ids) -> None:
    """Message Priya without being asked, or log why not."""
    to = ctx.storage.get(STUDENT_KEY)
    if to is None:
        await asyncio.to_thread(log, "coordinator", "proactive_message_skipped",
                                f"{detail}; Priya has not chatted with Docket yet", **ids)
        return
    message = reply(text)
    await ctx.send(to, message)
    recent_replies[to].append(text)
    pending = ctx.storage.get("proactive_pending") or {}
    pending[str(message.msg_id)] = detail
    ctx.storage.set("proactive_pending", pending)
    await asyncio.to_thread(log, "coordinator", action, detail, **ids)


@agent.on_message(CaseOpened)
async def on_case_opened(ctx: Context, sender: str, msg: CaseOpened):
    if sender == address_of("CASEWORKER"):
        await heard("coordinator", sender, msg, f"case {msg.case_id} waiting for approval", inputIds=[msg.case_id])


@agent.on_message(RefundMatched)
async def on_refund(ctx: Context, sender: str, msg: RefundMatched):
    if sender != address_of("CASEWORKER"):
        return  # only the Caseworker closes a case
    await heard("coordinator", sender, msg, f"case {msg.case_id} closed, refund received", inputIds=[msg.case_id])
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
    await heard("coordinator", sender, msg, f"rules ran on {msg.paystub_count} new paystubs")
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


@agent.on_message(DocumentReady)
async def on_document_ready(ctx: Context, sender: str, msg: DocumentReady):
    if sender != address_of("FILER"):
        return
    await heard("coordinator", sender, msg, f"{msg.title} waiting for approval", inputIds=[msg.document_id])


@agent.on_interval(period=float(os.environ.get("NOTIFY_POLL_SECONDS", "10")))
async def deliver_queued_messages(ctx: Context):
    """Send the messages other agents queued for the student on the chat channel.

    Every agent writes to notifications rather than reaching for ASI:One itself, so there is one
    place that knows how to talk to her and one record of what she was actually told. A message
    that cannot be delivered (she has not chatted with Docket yet) stays queued rather than
    being dropped, and the activity log says why.
    """
    to = ctx.storage.get(STUDENT_KEY)
    try:
        pending = await asyncio.to_thread(query, "notifications:pending", {"channel": "chat", "limit": 5})
    except Exception:
        ctx.logger.warning("could not read the message queue")
        return
    if not pending:
        return
    if to is None:
        ctx.logger.info(f"{len(pending)} message(s) waiting; Priya has not chatted with Docket yet")
        return
    for note in pending:
        message = reply(note["body"])
        try:
            await ctx.send(to, message)
        except Exception:
            ctx.logger.exception("sending a queued message failed")
            continue
        recent_replies[to].append(note["body"])
        pending_acks = ctx.storage.get("proactive_pending") or {}
        pending_acks[str(message.msg_id)] = note["title"]
        ctx.storage.set("proactive_pending", pending_acks)
        await asyncio.to_thread(mutation, "notifications:markSent", {"notificationId": note["_id"]})


agent.include(chat, publish_manifest=True)

if __name__ == "__main__":
    agent.run()
