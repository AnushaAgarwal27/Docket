"""Paystub transcription with Claude. Claude copies what is printed; code parses every number."""
from __future__ import annotations

import base64
import re
from pathlib import Path

from pydantic import BaseModel

from agents.ledger.ledger import to_cents, to_hours

MODEL = "claude-opus-5"

PROMPT = """Transcribe this paystub into the fields of the schema.
Copy every value exactly as printed, including "$" and commas. Do not calculate,
round, or infer anything. List weekly hours in the order printed. If a field is
not printed, use an empty string."""


class PaystubTranscript(BaseModel):
    employer: str
    periodStart: str  # as printed, expected YYYY-MM-DD
    periodEnd: str
    hoursByWeek: list[str]
    hourlyRate: str
    grossPay: str
    socialSecurityWithheld: str
    medicareWithheld: str
    federalIncomeTaxWithheld: str
    netPay: str


def transcribe_pdf(path: Path, client=None) -> PaystubTranscript:
    if client is None:
        import anthropic
        client = anthropic.Anthropic()
    data = base64.standard_b64encode(path.read_bytes()).decode("utf-8")
    response = client.messages.parse(
        model=MODEL,
        max_tokens=4000,
        output_config={"effort": "low"},
        messages=[{
            "role": "user",
            "content": [
                {"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": data}},
                {"type": "text", "text": PROMPT},
            ],
        }],
        output_format=PaystubTranscript,
    )
    if response.stop_reason == "refusal" or response.parsed_output is None:
        raise RuntimeError(f"no transcript for {path.name} (stop_reason={response.stop_reason})")
    return response.parsed_output


def transcript_to_paystub(t: PaystubTranscript, profile_id: str, source_file: str) -> tuple[dict, int | None, int]:
    """Returns (paystub row, hourly rate in cents or None, federal tax in cents)."""
    stub = {
        "profileId": profile_id,
        "periodStart": t.periodStart.strip(),
        "periodEnd": t.periodEnd.strip(),
        "employer": t.employer.strip(),
        "grossCents": to_cents(t.grossPay),
        "hoursByWeek": [to_hours(h) for h in t.hoursByWeek],
        "ssCents": to_cents(t.socialSecurityWithheld or "0"),
        "medicareCents": to_cents(t.medicareWithheld or "0"),
        "netCents": to_cents(t.netPay),
        "sourceFile": source_file,
    }
    # The hourly rate is printed with its unit — "$18.00 per hour" — and the prompt asks for values
    # exactly as printed, so that is what comes back. Strip the unit before parsing.
    #
    # It is also the one field here that may fail without costing anything. Every other value is
    # money owed; the rate is only used to check that hours × rate matches gross. Letting it raise
    # threw away the whole paystub — two of eight on one run, which quietly changed the refund
    # total. An unreadable rate just means that one cross-check is skipped.
    rate = None
    printed = re.sub(r"(?i)\s*(per|an|/)\s*(hour|hr)\.?$", "", t.hourlyRate.strip())
    if printed:
        try:
            rate = to_cents(printed)
        except ValueError:
            rate = None
    federal = to_cents(t.federalIncomeTaxWithheld or "0")
    return stub, rate, federal
