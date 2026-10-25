"""Send and receive Docket's agent-to-agent messages with an activity row for each, so the dashboard
feed shows the conversation between agents (kind "message", sender, receiver, summary)."""
from __future__ import annotations

import asyncio

from uagents import Context, Model

from agents.messages import PORTS, address_of
from agents.store import log

NAMES = {address_of(key): key.lower() for key in PORTS}


def name_of(address: str) -> str:
    return NAMES.get(address, "student" if address.startswith("agent1") or address.startswith("user") else address[:16])


async def record(me: str, sender: str, receiver: str, msg: Model, summary: str, direction: str, **ids) -> None:
    try:
        await asyncio.to_thread(
            log, me, f"message_{direction}", f"{type(msg).__name__}: {summary}"[:300],
            kind="message", sender=sender, receiver=receiver, summary=summary[:300], **ids)
    except Exception:  # noqa: BLE001 - a logging failure never stops a message
        pass


async def tell(ctx: Context, me: str, to: str, msg: Model, summary: str, **ids) -> None:
    """Send `msg` to agent `to` (e.g. "TAX") and log it."""
    await ctx.send(address_of(to), msg)
    await record(me, me, to.lower(), msg, summary, "sent", **ids)


async def heard(me: str, sender_address: str, msg: Model, summary: str, **ids) -> None:
    """Log a message this agent received."""
    await record(me, name_of(sender_address), me, msg, summary, "received", **ids)


async def ask(ctx: Context, me: str, to: str, msg: Model, response_type, summary: str, timeout: int = 60):
    """Send and wait for the typed reply; both directions are logged. Returns (reply or None, status)."""
    reply, status = await ctx.send_and_receive(address_of(to), msg, response_type=response_type, timeout=timeout)
    await record(me, me, to.lower(), msg, summary, "sent")
    if reply is not None:
        await record(me, to.lower(), me, reply, f"reply to {type(msg).__name__}", "received")
    return reply, status
