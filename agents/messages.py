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
    hearings_json: str = "[]"  # [{rule_id, flag_id, hearing_id, verdict, reason}] for each claim heard
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


class RefundMatched(Model):
    """Ledger -> Caseworker: a deposit matches a case's refund. Caseworker -> Coordinator: the case is closed."""
    profile_id: str
    case_id: str
    transaction_id: str
    amount_cents: int  # the case amount, from Convex
    counterparty: str


class NewPaystub(Model):
    """Ledger -> Tax: new paystubs are in the student file, so run the rules."""
    profile_id: str
    count: int


class FindingsReady(Model):
    """Tax -> Coordinator: the rules ran on their own (not because Priya asked)."""
    profile_id: str
    paystub_count: int
    flags_json: str  # flags written this run


# ---------- The Hearing (Tax as Advocate vs. Auditor) and the case that follows ----------
# Lists of objections and answers travel as JSON, like the other results, so rows pass through unchanged.

class Claim(Model):
    """Tax -> Auditor: a finding Tax will argue for, with the facts it rests on (computed in code)."""
    profile_id: str
    rule_id: str
    flag_id: str  # "" when the rule did not fire and Tax argues the claim anyway (it can lose)
    claim_json: str


class Objection(Model):
    """Auditor -> Tax: every reason the claim might be wrong."""
    profile_id: str
    rule_id: str
    objections_json: str  # [{id, severity, part, evidence_ids, message_facts}]


class Rebuttal(Model):
    """Tax -> Auditor: an answer to each objection from the facts: rebutted, conceded or unresolved."""
    profile_id: str
    rule_id: str
    flag_id: str
    claim_json: str
    objections_json: str
    rebuttals_json: str  # [{objection_id, outcome, argument, evidence_ids}]


class Verdict(Model):
    """Auditor -> Tax and Caseworker: the outcome, decided in code and stored in the hearings table."""
    profile_id: str
    rule_id: str
    flag_id: str
    hearing_id: str
    verdict: str  # upheld | downgraded | needs_human | defeated
    reason: str
    amount_cents: int


class CaseOpened(Model):
    """Caseworker -> Coordinator: an upheld refund finding now has a case waiting for the student's approval."""
    profile_id: str
    case_id: str
    flag_id: str
    amount_cents: int


class WatchRefund(Model):
    """Caseworker -> Ledger: payroll was asked for this refund, so watch the bank for it."""
    profile_id: str
    case_id: str
    amount_cents: int
