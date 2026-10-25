"""Typed messages between Docket's agents. Results carry JSON so rows pass through unchanged."""

import os

from dotenv import load_dotenv
from uagents import Model
from uagents.crypto import Identity
from uagents.resolver import GlobalResolver, Resolver

load_dotenv()

PORTS = {"COORDINATOR": 8001, "LEDGER": 8002, "TAX": 8003, "CASEWORKER": 8004,
         "RESEARCHER": 8005, "AUDITOR": 8006, "ORGANIZER": 8007, "FILER": 8008}


def address_of(name: str) -> str:
    """Agent address derived from its seed in .env, e.g. address_of("TAX")."""
    seed = os.environ.get(f"{name}_SEED")
    if not seed:
        raise KeyError(f"{name}_SEED is not set; add it to .env (see scripts/make_seeds.py)")
    return Identity.from_seed(seed, 0).address


def configured() -> list[str]:
    """The agents this machine has a seed for. An agent nobody is running yet is simply absent,
    so adding one to PORTS never breaks the agents that are running."""
    return [name for name in PORTS if os.environ.get(f"{name}_SEED")]


def local_endpoint(name: str) -> list[str]:
    return [f"http://127.0.0.1:{PORTS[name]}/submit"]


def local_routing() -> bool:
    """Whether agents on this machine talk to each other directly. Set DOCKET_LOCAL_ROUTING=0 to
    send every message through Agentverse instead.

    Direct is the better default: it is faster and it keeps the agents working when Agentverse is
    slow or unreachable, which during a demo matters more than anything. The cost is that
    Agentverse cannot count what never reaches it, so every agent except the Coordinator shows
    "0 interactions" on the My Agents page -- the agents are talking, but only the Coordinator's
    ASI:One traffic goes through a mailbox. Turn this off when you want those counts to move,
    for a judge looking at the page or a screenshot of it.
    """
    return os.environ.get("DOCKET_LOCAL_ROUTING", "1").strip().lower() not in ("0", "false", "no")


class LocalFirstResolver(Resolver):
    """Docket's agents run on one machine, so they reach each other directly instead of
    round-tripping through Agentverse. Every other address (ASI:One users) resolves normally.

    With DOCKET_LOCAL_ROUTING=0 there are no local shortcuts and everything resolves globally,
    so agent-to-agent messages travel through Agentverse mailboxes and show up in its counts."""

    def __init__(self):
        self._local = ({address_of(name): local_endpoint(name) for name in configured()}
                       if local_routing() else {})
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


# ---------- Athena research, group cases and filled-in documents ----------

class ResearchQuestion(Model):
    """Coordinator -> Researcher: the student asked something the file cannot answer."""
    profile_id: str
    question: str
    asked_via: str = "chat"  # voice | chat | dashboard


class ResearchAnswer(Model):
    """Researcher -> Coordinator: the answer, with the sources code could verify."""
    profile_id: str
    answer: str
    sources_json: str = "[]"
    confidence: str = "low"
    engine: str = ""
    error: str = ""


class PatternFound(Model):
    """Tax -> Organizer: several students at one employer have the same finding."""
    employer: str
    rule_id: str
    flagged: int


class GroupInvite(Model):
    """Organizer -> Coordinator: ask this student whether she wants to join the group case."""
    profile_id: str
    group_id: str
    employer: str
    members: int
    total_cents: int


class GroupDecision(Model):
    """Coordinator -> Organizer: her answer."""
    profile_id: str
    group_id: str
    join: bool


class FillDocument(Model):
    """Caseworker or Coordinator -> Filer: fill this form in from the student file."""
    profile_id: str
    kind: str  # form_8843 | form_843 | form_8316 | refund_letter | group_request
    flag_id: str = ""
    group_id: str = ""


class DocumentReady(Model):
    """Filer -> Coordinator: the document is filled in and waiting for the student to approve it."""
    profile_id: str
    document_id: str
    kind: str
    title: str
    submit_to: str
