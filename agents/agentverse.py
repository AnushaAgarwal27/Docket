"""Agentverse registration helpers shared by every Docket agent.

The startup check asks Agentverse for the agent's own mailbox, signed by the agent (the same request
uAgents' mailbox client polls), and logs whether it exists, so a missing Connect -> Mailbox click shows
up in the logs and the activity feed instead of as a silent ASI:One failure. The Almanac listing alone
is not proof: a mailbox=True agent is listed as a mailbox agent before its mailbox is created.
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
    "RESEARCHER": ("docket-researcher", "Athena: researches what the file cannot answer and watches the rules that fired, verifying every source in code"),
    "ORGANIZER": ("docket-organizer", "Finds employers where several students share a finding and runs the combined request for the ones who opt in"),
    "FILER": ("docket-filer", "Fills in the student's forms from stored records and submits only what she approves"),
}
CHECK_DELAY_SECONDS = 20  # let registration land first


def inspector_url(address: str, port: int) -> str:
    return f"https://agentverse.ai/inspect/?uri=http%3A//127.0.0.1%3A{port}&address={address}"


def listed(address: str) -> str:
    """How the Almanac lists this address: e.g. 'mailbox', 'local', or 'not listed'. Not proof of a mailbox."""
    try:
        r = requests.get(ALMANAC.format(address=address), timeout=15)
    except requests.RequestException as e:
        return f"unknown ({type(e).__name__})"
    if r.status_code == 404:
        return "not listed"
    return r.json().get("type", "unknown") if r.ok else f"unknown (HTTP {r.status_code})"


def mailbox_status(agent: Agent) -> str:
    """'connected', 'not connected', or 'unknown (<reason>)', from the agent's own signed mailbox request."""
    client = getattr(agent, "_mailbox_client", None)
    if client is None:
        return "not connected (mailbox=False)"
    try:
        r = requests.get(f"{client._agentverse.agents_api}/{agent.address}/mailbox",
                         headers={"Authorization": f"Agent {client.attestation}"}, timeout=15)
    except requests.RequestException as e:
        return f"unknown ({type(e).__name__})"
    if r.status_code == 200:
        return "connected"
    if r.status_code == 404:
        return "not connected"
    return f"unknown (HTTP {r.status_code})"


def add_mailbox_check(agent: Agent, name: str, port: int) -> None:
    """Log once at startup whether this agent's Agentverse mailbox is connected."""

    @agent.on_event("startup")
    async def check_mailbox(ctx: Context):
        await asyncio.sleep(CHECK_DELAY_SECONDS)
        status = await asyncio.to_thread(mailbox_status, agent)
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
