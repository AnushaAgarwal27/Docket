"""The refund request as a PDF, for the finding's receipt.

Every value comes from the student file as stored: the rule's own Social Security, Medicare and total
amounts on the flag, the linked paystubs' pay periods, and the verified quote (inserted by code). No sums
are computed here.
"""
from __future__ import annotations

import io
from datetime import date
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

from agents.store import dollars

DISCLAIMER = "This is not tax advice; confirm with your international student office."


def letter_paragraphs(profile: dict, flag: dict, stubs: list[dict], source_title: str, today: date) -> list[str]:
    """`stubs` are the paystubs linked to the flag (flag.paystubIds)."""
    employer = stubs[0]["employer"]
    first = min(p["periodStart"] for p in stubs)
    last = max(p["periodEnd"] for p in stubs)
    name = profile["name"]
    return [
        today.strftime("%B %-d, %Y"),
        f"To: {employer} Payroll<br/>Re: Refund of Social Security and Medicare withheld in error, {name}",
        f"This request is sent on behalf of {name}, with her permission, by Docket, an AI assistant.",
        f"{name} is an {profile['visa']} student. Social Security ({dollars(flag['ssCents'])}) and Medicare "
        f"({dollars(flag['medicareCents'])}) were withheld from {len(stubs)} paychecks for pay periods "
        f"{first} to {last}, a total of {dollars(flag['amountCents'])}.",
        f"{source_title} states: “{flag['quote']}”",
        f"Please refund {dollars(flag['amountCents'])} and stop withholding Social Security and Medicare from her "
        f"future paychecks. If you cannot refund it, please give her a written statement saying so.",
        f"Prepared with Docket for {name}.",
        DISCLAIMER,
    ]


def render_pdf(paragraphs: list[str]) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, leftMargin=inch, rightMargin=inch, topMargin=inch,
                            bottomMargin=inch, title="Refund request", author="Docket")
    styles = getSampleStyleSheet()
    body = styles["BodyText"]
    story = [Paragraph("Refund request", styles["Heading2"])]
    for i, text in enumerate(paragraphs):
        # Line breaks we add ourselves are kept; everything from the student file is escaped.
        safe = "<br/>".join(escape(part) for part in text.split("<br/>"))
        story += [Paragraph(safe, styles["Italic"] if text == DISCLAIMER else body), Spacer(1, 10)]
    doc.build(story)
    return buf.getvalue()
