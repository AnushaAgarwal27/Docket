"""Talk to the running Coordinator over the real chat protocol, without ASI:One.

    .venv/bin/python -m scripts.chat_test "check my pay" "what's wrong?" "yes"

Starts a throwaway agent on port 8009, sends each message in order, prints each reply, then exits.
"""

import asyncio
import os
import sys
from datetime import datetime, timezone
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

load_dotenv()

COORDINATOR = os.environ.get(
    "COORDINATOR_ADDRESS", "agent1qwj0e7jf5gu6lw3tael5ld2v8xeg4jrzgs8wx7yg22a82du6dcqeqtr0686"
)
MESSAGES = sys.argv[1:] or ["check my pay", "what's wrong?", "yes, contact payroll"]
REPLY_TIMEOUT = 90  # Claude plus Convex round trips can be slow on venue Wi-Fi

tester = Agent(name="docket-tester", seed="docket-tester-local-only", port=8009,
               endpoint=["http://127.0.0.1:8009/submit"])
chat = Protocol(spec=chat_protocol_spec)
got_reply = asyncio.Event()


@chat.on_message(ChatMessage)
async def on_reply(ctx: Context, sender: str, msg: ChatMessage):
    await ctx.send(sender, ChatAcknowledgement(timestamp=datetime.now(timezone.utc), acknowledged_msg_id=msg.msg_id))
    for item in msg.content:
        if isinstance(item, TextContent):
            print(f"\n<<< docket-coordinator\n{item.text}\n", flush=True)
        elif isinstance(item, MetadataContent) and "card_kind" in item.metadata:
            print(f"[{item.metadata['card_kind']} card] {item.metadata['card_payload'][:300]}\n", flush=True)
    # A reply can be several messages; the last one ends the session.
    if any(isinstance(item, EndSessionContent) for item in msg.content):
        got_reply.set()


@chat.on_message(ChatAcknowledgement)
async def on_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    pass


@tester.on_event("startup")
async def run(ctx: Context):
    await asyncio.sleep(3)  # let the Almanac registration land so replies can find us
    failures = 0
    for text in MESSAGES:
        got_reply.clear()
        print(f">>> {text}", flush=True)
        started = asyncio.get_running_loop().time()
        await ctx.send(COORDINATOR, ChatMessage(timestamp=datetime.now(timezone.utc), msg_id=uuid4(),
                                                content=[TextContent(type="text", text=text)]))
        try:
            await asyncio.wait_for(got_reply.wait(), REPLY_TIMEOUT)
            print(f"(reply in {asyncio.get_running_loop().time() - started:.1f}s)", flush=True)
        except asyncio.TimeoutError:
            failures += 1
            print(f"!!! no reply within {REPLY_TIMEOUT}s", flush=True)
    os._exit(1 if failures else 0)


tester.include(chat)

if __name__ == "__main__":
    tester.run()
