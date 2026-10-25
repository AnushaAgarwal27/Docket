"""Agentverse registration helpers shared by every Docket agent.

The startup check asks Agentverse's public Almanac API how each agent is registered and logs
whether its mailbox is connected, so a missing Connect -> Mailbox click shows up in the logs
and the activity feed instead of as a silent ASI:One failure.
"""
from __future__ import annotations

import asyncio

import requests
from uagents import Agent, Context

from agents.store import log

ALMANAC = "https://agentverse.ai/v1/almanac/agents/{address}"

# Every Docket agent: .env key -> (agent name, role). Ports live in agents/messages.py.
ROSTER = {
    "COORDINATOR": ("docket-coordinator", "Talks to the student in ASI:One (chat protocol), sends cards, narrates the Hearing"),
    "LEDGER": ("docket-ledger", "Reads paystub PDFs and the Nessie bank feed; matches refund deposits"),
    "TAX": ("docket-tax", "Runs the rules in code and argues the student's side in the Hearing (Advocate)"),
    "AUDITOR": ("docket-auditor", "Argues the employer's side in the Hearing and issues the verdict in code"),
    "CASEWORKER": ("docket-caseworker", "Refund case state machine, approvals, payroll calls and letters"),
}
CHECK_DELAY_SECONDS = 20  # let registration land first


def inspector_url(address: str, port: int) -> str:
    return f"https://agentverse.ai/inspect/?uri=http%3A//127.0.0.1%3A{port}&address={address}"


def mailbox_status(address: str) -> str:
    """'connected', 'not connected', or 'unknown (<reason>)'."""
    try:
        r = requests.get(ALMANAC.format(address=address), timeout=15)
    except requests.RequestException as e:
        return f"unknown ({type(e).__name__})"
    if r.status_code == 404:
        return "not connected"
    if not r.ok:
        return f"unknown (HTTP {r.status_code})"
    info = r.json()
    return "connected" if info.get("type") == "mailbox" and info.get("status") == "active" else "not connected"


def add_mailbox_check(agent: Agent, name: str, port: int) -> None:
    """Log once at startup whether this agent's Agentverse mailbox is connected."""

    @agent.on_event("startup")
    async def check_mailbox(ctx: Context):
        await asyncio.sleep(CHECK_DELAY_SECONDS)
        status = await asyncio.to_thread(mailbox_status, agent.address)
        if status == "connected":
            ctx.logger.info("Agentverse mailbox: connected")
        else:
            ctx.logger.warning(f"Agentverse mailbox: {status}. Open {inspector_url(agent.address, port)} "
                               "and click Connect, then Mailbox.")
        try:
            await asyncio.to_thread(log, name, "mailbox_check", f"Agentverse mailbox {status}",
                                    inputIds=[agent.address])
        except Exception:  # noqa: BLE001 - a Convex outage must not stop the agent starting
            ctx.logger.warning("could not log the mailbox check to activity")
