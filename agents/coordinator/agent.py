"""Coordinator: the only agent Priya talks to, through ASI:One.

Hello-world step from the plan: chat protocol + mailbox, reachable in ASI:One.
Run it, wait for "registered as mailbox agent", then use Chat with Agent in ASI:One.
"""

import os
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

load_dotenv()

agent = Agent(name="docket-coordinator", seed=os.environ["COORDINATOR_SEED"], port=8001, mailbox=True)
chat = Protocol(spec=chat_protocol_spec)

# Echo guard: ASI:One sometimes sends our own reply back as a new request.
recent_replies: dict[str, deque] = defaultdict(lambda: deque(maxlen=5))


def reply(text: str) -> ChatMessage:
    return ChatMessage(
        timestamp=datetime.now(timezone.utc),
        msg_id=uuid4(),
        content=[TextContent(type="text", text=text), EndSessionContent(type="end-session")],
    )


@chat.on_message(ChatMessage)
async def on_chat(ctx: Context, sender: str, msg: ChatMessage):
    await ctx.send(sender, ChatAcknowledgement(timestamp=datetime.now(timezone.utc), acknowledged_msg_id=msg.msg_id))
    for item in msg.content:
        if not isinstance(item, TextContent):
            continue
        text = item.text.strip()
        if text in recent_replies[sender]:
            ctx.logger.info("echo ignored")
            continue
        # TODO: route intents (check my pay, what's wrong?, yes contact payroll, price, Hindi).
        answer = f"Docket here. You said: {text}"
        recent_replies[sender].append(answer)
        await ctx.send(sender, reply(answer))


@chat.on_message(ChatAcknowledgement)
async def on_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    pass


agent.include(chat, publish_manifest=True)

if __name__ == "__main__":
    agent.run()
