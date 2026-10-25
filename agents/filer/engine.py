"""Fill, show, and submit — with the student's approval as the only thing that moves the last step."""
from __future__ import annotations

import io
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.lib import colors

from agents import guard
from agents.convex_files import upload_and_attach
from agents.filer import forms
from agents.researcher import engine as research
from agents.store import log, mutation, query

AGENT = "filer"

# Which forms Docket offers to fill in on its own, and when it is worth offering.
# `today` is passed in rather than read from the clock so the decision is testable and so a run
# cannot straddle midnight and change its mind halfway through.
AUTO = {
    # Everyone files this every year; it is the thing students most often do not know about.
    "form_8843": lambda profile, flags, cases, today: needs_8843(profile, today),
    # The IRS route, only once payroll has actually refused.
    "form_843": lambda profile, flags, cases, today: any(c["state"] == "escalate_irs" for c in cases),
    "form_8316": lambda profile, flags, cases, today: any(c["state"] == "escalate_irs" for c in cases),
}


def needs_8843(profile: dict, today: date | None = None) -> bool:
    year = forms.tax_year(today or date.today())
    filed = set(profile.get("filed8843Years") or [])
    filed |= {f["year"] for f in (profile.get("filings") or []) if f.get("form") == "8843"}
    arrived = int(str(profile.get("arrivalDate") or "9999")[:4])
    return arrived <= year and year not in filed


# ---------------------------------------------------------------------------
# Render
# ---------------------------------------------------------------------------

def render_pdf(title: str, fields: list[dict], body: str) -> bytes:
    """The filled form as a PDF: the fields table first, with the source of every value, then the text."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter, leftMargin=inch, rightMargin=inch,
                            topMargin=inch, bottomMargin=inch, title=title, author="Docket")
    styles = getSampleStyleSheet()
    small = styles["BodyText"].clone("small")
    small.fontSize = 8
    small.leading = 10
    story = [Paragraph(escape(title), styles["Heading2"]), Spacer(1, 6),
             Paragraph("Every value below was taken from your file. The third column says where from.",
                       small), Spacer(1, 10)]
    rows = [["Field", "Value", "Taken from"]]
    rows += [[Paragraph(escape(f["label"]), small), Paragraph(escape(str(f["value"])), small),
              Paragraph(escape(f["source"]), small)] for f in fields]
    table = Table(rows, colWidths=[1.7 * inch, 2.6 * inch, 2.2 * inch])
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#999999")),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EEEAE2")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
    ]))
    story += [table, Spacer(1, 16)]
    for para in body.split("\n\n"):
        safe = "<br/>".join(escape(line) for line in para.split("\n"))
        story += [Paragraph(safe, styles["BodyText"]), Spacer(1, 8)]
    doc.build(story)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Fill and show
# ---------------------------------------------------------------------------

def fill(profile_id: str, kind: str, flag_id: str = "", group_id: str = "") -> str | None:
    """Fill one form in and leave it waiting for the student. Returns the document id, or None."""
    profile = query("profiles:get", {"profileId": profile_id})
    if profile is None:
        return None
    paystubs = query("paystubs:listByProfile", {"profileId": profile_id})
    flags = query("flags:listByProfile", {"profileId": profile_id})
    flag = next((f for f in flags if f["_id"] == flag_id), None) if flag_id else \
        next((f for f in flags if f["ruleId"] == "FICA_EXEMPT_F1"), None)

    try:
        built = forms.build(kind, profile, paystubs, flag)
    except forms.MissingFact as e:
        log(AGENT, "document_not_filled", f"{kind}: {e}", inputIds=[profile_id])
        return None

    document_id = mutation("documents:draft", {
        "profileId": profile_id,
        "kind": built["kind"],
        "title": built["title"],
        "fields": [{"label": a, "value": str(b), "source": c} for a, b, c in built["fields"]],
        "body": built["body"],
        "submitTo": built["submitTo"],
        **({"flagId": flag["_id"]} if flag else {}),
        **({"groupId": group_id} if group_id else {}),
    })
    attach_pdf(document_id, profile, built, flag["_id"] if flag else None)
    tell_student(profile, document_id, built["title"], built["submitTo"])
    return document_id


def attach_pdf(document_id: str, profile: dict, built: dict, flag_id: str | None = None) -> None:
    pdf = render_pdf(built["title"], [{"label": a, "value": str(b), "source": c}
                                      for a, b, c in built["fields"]], built["body"])
    name = profile["name"].split()[0].lower()
    upload_and_attach(Path(f"{built['kind']}_{name}.pdf"), "form", agent=AGENT, data=pdf,
                      **({"flagId": flag_id} if flag_id else {}))
    log(AGENT, "document_rendered", f"{built['title']} rendered as a PDF", inputIds=[document_id])


def tell_student(profile: dict, document_id: str, title: str, submit_to: str) -> None:
    facts = {"document_title": title, "name": profile.get("name"), "form": title}
    fallback = (f"I've filled in your {title} from what's on your file. It's ready to go to "
                f"{submit_to}. Have a look and tell me yes to send it, or no to leave it. "
                f"I won't send anything until you say so.")
    rendered = guard.speak(
        purpose=("Tell the student her form is filled in and ready, that she should review it, and "
                 f"that nothing is sent to {submit_to} until she approves it. Do not state any "
                 "figure from the form."),
        facts=facts, channel="chat", audience="student", fallback=fallback, log_fn=log, agent=AGENT)
    for channel in research.channels_for(profile):
        mutation("notifications:queue", {
            "profileId": profile["_id"], "channel": channel, "kind": "document_ready",
            "title": f"{title} is ready for you to check",
            "body": guard.for_sms(rendered.text) if channel == "sms" else rendered.text,
            "refs": [document_id], "awaiting": "approval",
        })


def fill_what_is_due(profile_id: str, today: date | None = None) -> list[str]:
    """Fill in every form this student currently needs and does not already have."""
    today = today or date.today()
    profile = query("profiles:get", {"profileId": profile_id})
    if profile is None or profile.get("simulated"):
        return []
    flags = query("flags:listByProfile", {"profileId": profile_id})
    cases = query("cases:listByProfile", {"profileId": profile_id})
    existing = {d["kind"] for d in query("documents:forProfile", {"profileId": profile_id})
                if d["state"] != "declined"}
    made = []
    for kind, due in AUTO.items():
        if kind in existing or not due(profile, flags, cases, today):
            continue
        document_id = fill(profile_id, kind)
        if document_id:
            made.append(document_id)
    return made


# ---------------------------------------------------------------------------
# Submit — only what she approved
# ---------------------------------------------------------------------------

def submit_approved() -> int:
    """Send every approved document, once. Returns how many were sent."""
    pending = query("documents:awaitingSubmission")
    for document in pending:
        submit(document)
    return len(pending)


def submit(document: dict) -> None:
    """Record the submission.

    Docket does not have a filing channel to the IRS, and inventing one would be the single most
    harmful thing this agent could do: a student who believes a form was filed, and finds out in
    April that it was not, is worse off than one who knows she has to mail it. So what happens here
    is deliberately honest — the document is marked submitted with a reference, and the student is
    told exactly what is now hers to do. For an employer, the same document is what the payroll call
    and the written request already carry.
    """
    reference = f"DOCKET-{str(document['_id'])[-8:].upper()}"
    mutation("documents:recordSubmission", {"documentId": document["_id"], "submissionRef": reference})
    profile = query("profiles:get", {"profileId": document["profileId"]})
    if profile is None:
        return
    to_irs = document["submitTo"] == "IRS"
    body = (
        f"Your {document['title']} is finished and signed off. Reference {reference}.\n\n"
        + ("Docket can't file with the IRS for you, so this last step is yours: download the PDF, "
           "print it, sign it, and mail it to the address in the form's instructions. I've kept a "
           "copy on your file and I'll remind you if it's still unsent."
           if to_irs else
           f"I'm sending it to {document['submitTo']} with your refund request, and I'll tell you "
           f"what they say.")
    )
    for channel in research.channels_for(profile):
        mutation("notifications:queue", {
            "profileId": profile["_id"], "channel": channel, "kind": "document_submitted",
            "title": f"{document['title']}: {reference}",
            "body": guard.for_sms(body) if channel == "sms" else body,
            "refs": [document["_id"]], "awaiting": "none",
        })
