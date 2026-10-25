"""Runs rules.yaml against a student's facts and produces flag candidates.

A candidate becomes a `flags` row only after the quote checker passes. Every decision,
including a rejection, comes back as an activity entry for the dashboard feed.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import yaml

from rules.quote_checker import check_quote, source_status
from rules.rules import DECISIONS, NoFlag

RULES_PATH = Path(__file__).with_name("rules.yaml")
SOURCES_DIR = Path(__file__).resolve().parents[1] / "sources"
DISCLAIMER = "Confirm with your school's international office."


def load_rules(path: Path = RULES_PATH) -> list[dict]:
    loaded = yaml.safe_load(path.read_text())
    rules = loaded["rules"] if isinstance(loaded, dict) else loaded
    for r in rules:
        r.setdefault("source_id", r["id"])
        if r["check"] not in DECISIONS:
            raise ValueError(f"rule {r['id']} names unknown check {r['check']!r}")
    return rules


def load_local_sources(rules: list[dict], directory: Path = SOURCES_DIR) -> dict[str, str]:
    """source_id -> page text downloaded by `python -m rules.download_sources`."""
    return {r["source_id"]: (directory / f"{r['source_id']}.txt").read_text()
            for r in rules if (directory / f"{r['source_id']}.txt").exists()}


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
    rule cites (the model's returned clause), so it goes through the same check.

    No flag is produced unless the quote is found word for word in the stored page. A source
    outside the allow-list still produces its flag, marked `sourceStatus: "unverified"`.
    """
    out = Evaluation()
    for rule in rules if rules is not None else load_rules():
        decision = DECISIONS[rule["check"]](profile, paystubs, calendar, as_of)
        if isinstance(decision, NoFlag):
            out.activity.append(_activity(rule, "rule_not_triggered", decision.reason))
            continue
        hit = decision.detail
        quote = (quotes or {}).get(rule["id"], rule["quote"])
        text = sources.get(rule["source_id"])
        result = check_quote(quote, text) if text is not None else None
        if result is None or not result.ok:
            reason = "source not fetched" if result is None else result.reason
            out.activity.append(_activity(rule, "flag_rejected", reason, quote=quote))
            continue
        status = source_status(rule["source_url"])
        out.flags.append({
            "ruleId": rule["id"],
            "action": rule["action"],
            "severity": hit.get("severity", "flag"),
            "amountCents": hit["amountCents"],
            "detail": hit,
            "quote": quote,
            "sourceId": rule["source_id"],
            "sourceUrl": rule["source_url"],
            "sourceStatus": status,
            "status": "open",
        })
        note = "" if status == "verified" else f"; source {rule['source_url']} is not on the allow-list"
        out.activity.append(_activity(rule, "flag_raised", f"amountCents={hit['amountCents']}{note}"))
    return out


def _activity(rule: dict, action: str, detail: str, **extra) -> dict:
    return {"agent": "tax", "action": action, "ruleId": rule["id"], "detail": detail,
            "sourceId": rule["source_id"], **extra}
