"""Runs rules.yaml against a student's facts and produces flag candidates.

A candidate becomes a `flags` row only after the quote checker passes. Every decision,
including a rejection, comes back as an activity entry for the dashboard feed.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import yaml

from rules.quote_checker import check_quote
from rules.rules import CHECKS

RULES_PATH = Path(__file__).with_name("rules.yaml")
DISCLAIMER = "Confirm with your school's international office."


def load_rules(path: Path = RULES_PATH) -> list[dict]:
    rules = yaml.safe_load(path.read_text())["rules"]
    for r in rules:
        if r["check"] not in CHECKS:
            raise ValueError(f"rule {r['id']} names unknown check {r['check']!r}")
    return rules


@dataclass
class Evaluation:
    flags: list[dict] = field(default_factory=list)
    activity: list[dict] = field(default_factory=list)


def evaluate(
    profile: dict,
    paystubs: list[dict],
    calendar: dict,
    as_of: date,
    sources: dict[str, str],
    rules: list[dict] | None = None,
    quotes: dict[str, str] | None = None,
) -> Evaluation:
    """`sources` maps source_id to stored page text. `quotes` optionally overrides the clause a
    rule cites (the model's returned clause), so it goes through the same check."""
    out = Evaluation()
    for rule in rules if rules is not None else load_rules():
        hit = CHECKS[rule["check"]](profile, paystubs, calendar, as_of)
        if hit is None:
            out.activity.append(_activity(rule, "rule_not_triggered", "no match on student facts"))
            continue
        quote = (quotes or {}).get(rule["id"], rule["quote"])
        text = sources.get(rule["source_id"])
        result = check_quote(quote, text) if text is not None else None
        if result is None or not result.ok:
            reason = "source not fetched" if result is None else result.reason
            out.activity.append(_activity(rule, "flag_rejected", reason, quote=quote))
            continue
        out.flags.append({
            "ruleId": rule["id"],
            "action": rule["action"],
            "amountCents": hit["amountCents"],
            "detail": hit,
            "quote": quote,
            "sourceId": rule["source_id"],
            "status": "open",
        })
        out.activity.append(_activity(rule, "flag_raised", f"amountCents={hit['amountCents']}"))
    return out


def _activity(rule: dict, action: str, detail: str, **extra) -> dict:
    return {"agent": "tax", "action": action, "ruleId": rule["id"], "detail": detail,
            "sourceId": rule["source_id"], **extra}
