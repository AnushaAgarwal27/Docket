"""ASI:One Interactive Cards: builders for Docket's form, detail and review cards, and a validator.

A card is a ChatMessage with TextContent (shown above the card, and the fallback if the card is rejected)
and one MetadataContent whose values are all strings: card_protocol_version "1",
requires_card_interaction "true", card_kind, and card_payload (JSON, at most 64 KB, payload at the top
level). Source: innovationlab.fetch.ai/resources/docs/interactive-cards/asi-interactive-cards.
Every number on a card comes from the student file; nothing here computes money.
"""
from __future__ import annotations

import json
from dataclasses import dataclass

from agents.store import dollars

MAX_PAYLOAD_BYTES = 64 * 1024
FORM_FIELD_KINDS = {"text", "number", "email", "select", "checkbox"}


@dataclass
class Card:
    text: str  # narration above the card; also the whole message if the card is rejected
    kind: str  # "form" | "detail" | "review"
    payload: dict
    terminal: bool = False  # informational card, no input expected

    def metadata(self) -> dict[str, str]:
        meta = {
            "card_protocol_version": "1",
            "requires_card_interaction": "true",  # the docs require exactly "true", even for terminal cards
            "card_kind": self.kind,
            "card_payload": json.dumps(self.payload, separators=(",", ":")),
        }
        if self.terminal:
            meta["is_terminal"] = "true"
        return meta


def _cta_problems(cta, where: str) -> list[str]:
    if not isinstance(cta, dict) or not isinstance(cta.get("label"), str) or not isinstance(cta.get("selection"), dict):
        return [f"{where} needs a label and a selection object"]
    return []


def _rows_problems(rows) -> list[str]:
    if not isinstance(rows, list) or not rows:
        return ["summary_rows must be a non-empty list"]
    return [f"summary_rows[{i}] needs string label and value" for i, r in enumerate(rows)
            if not (isinstance(r, dict) and isinstance(r.get("label"), str) and isinstance(r.get("value"), str))]


def validate(card: Card) -> list[str]:
    """Problems that would make ASI:One drop the card (empty when it is valid)."""
    problems = []
    meta = card.metadata()
    if not all(isinstance(v, str) for v in meta.values()):
        problems.append("every metadata value must be a string")
    if len(meta["card_payload"].encode()) > MAX_PAYLOAD_BYTES:
        problems.append("card_payload is over 64 KB")
    p = card.payload
    if not isinstance(p.get("title"), str) or not p["title"]:
        problems.append("title is required")
    if card.kind == "form":
        fields = p.get("fields")
        if not isinstance(fields, list) or not fields:
            problems.append("form needs fields")
        for i, f in enumerate(fields or []):
            if not isinstance(f.get("name"), str) or not isinstance(f.get("label"), str):
                problems.append(f"fields[{i}] needs name and label")
            if f.get("kind") not in FORM_FIELD_KINDS:
                problems.append(f"fields[{i}] kind must be one of {sorted(FORM_FIELD_KINDS)}")
            if f.get("kind") == "select" and not (isinstance(f.get("options"), list) and f["options"] and all(
                    isinstance(o, dict) and "value" in o and "label" in o for o in f["options"])):
                problems.append(f"fields[{i}] select needs non-empty {{value, label}} options")
        problems += _cta_problems(p.get("submit_cta"), "submit_cta")
    elif card.kind == "detail":
        problems += _rows_problems(p.get("summary_rows"))
        for i, c in enumerate(p.get("ctas", [])):
            problems += _cta_problems(c, f"ctas[{i}]")
    elif card.kind == "review":
        problems += _rows_problems(p.get("summary_rows"))
        problems += _cta_problems(p.get("approve_cta"), "approve_cta")
        problems += _cta_problems(p.get("reject_cta"), "reject_cta")
    else:
        problems.append(f"unsupported card_kind {card.kind!r}")
    return problems


# ---------- Docket's cards ----------

VISA_OPTIONS = [{"value": "F-1", "label": "F-1"}, {"value": "J-1", "label": "J-1"}, {"value": "other", "label": "Other"}]
EMPLOYMENT_OPTIONS = [{"value": "employee", "label": "Employee (W-2, on payroll)"},
                      {"value": "contractor", "label": "Contractor (1099)"}]


def profile_form(missing: list[str] | None = None) -> Card:
    """Onboarding: the facts the rules and the Hearing need. Written to the profiles table on submit."""
    why = (f"I need a few facts before I can check this: {', '.join(missing)}." if missing
           else "Tell me a few facts about your visa and job so I can check your pay.")
    return Card(text=why, kind="form", payload={
        "title": "Your student profile",
        "fields": [
            {"name": "arrival_date", "kind": "text", "label": "First arrived in the US (YYYY-MM-DD)", "required": True},
            {"name": "visa_type", "kind": "select", "label": "Visa type", "required": True, "options": VISA_OPTIONS},
            {"name": "employer", "kind": "text", "label": "On-campus employer", "required": True},
            {"name": "employment_type", "kind": "select", "label": "How are you paid?", "required": True,
             "options": EMPLOYMENT_OPTIONS},
            {"name": "employer_is_school", "kind": "checkbox", "label": "My employer is my school"},
            {"name": "enrolled", "kind": "checkbox", "label": "I'm enrolled this term"},
        ],
        "submit_cta": {"label": "Save profile", "selection": {"action": "submit_profile"}},
    })


CONFIDENCE_LABEL = {"high": "high confidence", "medium": "medium confidence: an exception may apply",
                    "low": "low confidence: needs a person to confirm"}


def finding_detail(title: str, rows: list[tuple[str, str]], quote: str | None, source_title: str | None,
                   verdict_line: str, flag_id: str | None, text: str) -> Card:
    """One finding: amounts and confidence per part, the verified clause, and the Hearing's verdict."""
    summary = [{"label": label, "value": value} for label, value in rows]
    summary.append({"label": "Verdict", "value": verdict_line})
    if quote:
        summary.append({"label": f"The rule ({source_title})" if source_title else "The rule", "value": f"“{quote}”"})
    selection = {"action": "show_hearing"}
    if flag_id:
        selection["flag_id"] = flag_id
    return Card(text=text, kind="detail", payload={
        "title": title,
        "summary_rows": summary,
        "ctas": [{"label": "Why? Replay the Hearing", "selection": selection}],
    })


def refund_review(employer: str, amount_cents: int, ss_cents: int | None, medicare_cents: int | None,
                  verdict_line: str, case_id: str | None, flag_id: str | None, text: str) -> Card:
    """Approval: Approve contacts payroll; Not now does not. Nothing is called without the approve selection."""
    rows = [{"label": "To", "value": f"{employer} payroll"},
            {"label": "Refund requested", "value": dollars(amount_cents)}]
    if ss_cents is not None and medicare_cents is not None:
        rows += [{"label": "Social Security", "value": dollars(ss_cents)},
                 {"label": "Medicare", "value": dollars(medicare_cents)}]
    rows += [{"label": "Hearing verdict", "value": verdict_line},
             {"label": "How", "value": "A call from Docket's AI assistant, which says it is an AI acting with your "
                                       "permission, plus a written request"}]
    ids = {k: v for k, v in (("case_id", case_id), ("flag_id", flag_id)) if v}
    return Card(text=text, kind="review", payload={
        "title": "Contact payroll about your refund?",
        "summary_rows": rows,
        "approve_cta": {"label": "Approve and contact payroll", "selection": {"action": "approve_refund", **ids},
                        "primary": True},
        "reject_cta": {"label": "Not now", "selection": {"action": "decline_refund", **ids}},
    })
