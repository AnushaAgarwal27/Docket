"""Typed messages between Docket's agents. Results carry JSON so rows pass through unchanged."""

import os

from dotenv import load_dotenv
from uagents import Model
from uagents.crypto import Identity
from uagents.resolver import GlobalResolver, Resolver

load_dotenv()

PORTS = {"COORDINATOR": 8001, "LEDGER": 8002, "TAX": 8003, "CASEWORKER": 8004, "AUDITOR": 8006}


def address_of(name: str) -> str:
    """Agent address derived from its seed in .env, e.g. address_of("TAX")."""
    return Identity.from_seed(os.environ[f"{name}_SEED"], 0).address


def local_endpoint(name: str) -> list[str]:
    return [f"http://127.0.0.1:{PORTS[name]}/submit"]


class LocalFirstResolver(Resolver):
    """Docket's agents run on one machine, so they reach each other directly instead of
    round-tripping through Agentverse. Every other address (ASI:One users) resolves normally."""

    def __init__(self):
        self._local = {address_of(name): local_endpoint(name) for name in PORTS}
        self._global = GlobalResolver()

    async def resolve(self, destination: str) -> tuple[str | None, list[str]]:
        if destination in self._local:
            return destination, self._local[destination]
        return await self._global.resolve(destination)


class RunRules(Model):
    profile_id: str


class RulesResult(Model):
    flags_json: str  # list of flags written this run
    error: str = ""


class OpenCases(Model):
    profile_id: str


class CasesResult(Model):
    awaiting_json: str  # cases waiting for the student's approval
    error: str = ""


class CaseDecision(Model):
    profile_id: str
    approved: bool


class DecisionResult(Model):
    acted: bool  # False when nothing was waiting for approval
    amount_cents: int = 0
    error: str = ""


class RefundLanded(Model):
    """Ledger -> Coordinator: a deposit matched an open refund case, which is now closed."""
    profile_id: str
    case_id: str
    amount_cents: int  # the case amount, from Convex
    counterparty: str


class PaystubsRecorded(Model):
    """Ledger -> Tax: new paystubs are in the student file, so run the rules."""
    profile_id: str
    count: int


class FindingsReady(Model):
    """Tax -> Coordinator: the rules ran on their own (not because Priya asked)."""
    profile_id: str
    paystub_count: int
    flags_json: str  # flags written this run
