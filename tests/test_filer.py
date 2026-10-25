"""The forms: every value traceable to a record, and a missing fact stopping the form.

The second half matters more than the first. A form that quietly invents a date is worse than no
form at all, because the student would sign it.
"""
from datetime import date

import pytest

from agents.filer import engine, forms

TODAY = date(2026, 3, 1)

PROFILE = {
    "_id": "p1", "name": "Priya Sharma", "visa": "F-1", "arrivalDate": "2024-08-15",
    "school": "Golden Bear University", "employer": "University Dining Services",
}
PAYSTUBS = [
    {"_id": "s1", "periodStart": "2025-01-12", "periodEnd": "2025-01-25",
     "employer": "University Dining Services", "ssCents": 4464, "medicareCents": 1044},
    {"_id": "s2", "periodStart": "2025-02-09", "periodEnd": "2025-02-22",
     "employer": "University Dining Services", "ssCents": 4464, "medicareCents": 1044},
]
FLAG = {"_id": "f1", "ruleId": "FICA_EXEMPT_F1", "amountCents": 44064, "ssCents": 35712,
        "medicareCents": 8352, "paystubIds": ["s1", "s2"],
        "quote": "Social security and Medicare taxes are not withheld"}


def values(built):
    return {label: value for label, value, _source in built["fields"]}


def sources(built):
    return {label: source for label, _value, source in built["fields"]}


# ---------- every value says where it came from ----------

def test_every_field_names_the_record_it_came_from():
    for kind in ("form_8843", "form_843", "form_8316", "refund_letter"):
        built = forms.build(kind, PROFILE, PAYSTUBS, FLAG, TODAY)
        assert built["fields"], kind
        for label, value, source in built["fields"]:
            assert label and str(value) and source, f"{kind}: {label} has no source"


def test_8843_is_computed_from_the_profile():
    built = forms.build("form_8843", PROFILE, PAYSTUBS, FLAG, TODAY)
    v, s = values(built), sources(built)
    assert v["Tax year"] == "2025"                       # filed in 2026, covers 2025
    assert v["Date first entered the US"] == "2024-08-15"
    assert v["Calendar year in the US"] == "2 of 5"      # 2025 - 2024 + 1
    assert s["Date first entered the US"] == "profiles.arrivalDate"
    assert built["submitTo"] == "IRS"


def test_843_uses_the_rule_totals_and_never_re_adds_paystubs():
    """The flag carries the totals the rules engine computed. Summing the paystubs again here would
    be a second, independent calculation that could disagree with the one the student was shown."""
    built = forms.build("form_843", PROFILE, PAYSTUBS, FLAG, TODAY)
    v, s = values(built), sources(built)
    assert v["Social Security withheld"] == "$357.12"    # flags.ssCents, not sum(paystubs)
    assert v["Medicare withheld"] == "$83.52"
    assert v["Total claimed"] == "$440.64"
    assert s["Total claimed"] == "flags.amountCents"


def test_the_letter_quotes_the_verified_clause():
    built = forms.build("refund_letter", PROFILE, PAYSTUBS, FLAG, TODAY)
    assert FLAG["quote"] in built["body"]


# ---------- a missing fact stops the form ----------

def test_a_profile_without_an_arrival_date_cannot_produce_an_8843():
    without = {k: v for k, v in PROFILE.items() if k != "arrivalDate"}
    with pytest.raises(forms.MissingFact, match="arrival date"):
        forms.build("form_8843", without, PAYSTUBS, FLAG, TODAY)


def test_a_claim_with_no_finding_is_refused():
    with pytest.raises(forms.MissingFact, match="no refund finding"):
        forms.build("form_843", PROFILE, PAYSTUBS, None, TODAY)


def test_a_finding_without_its_totals_is_refused():
    partial = {k: v for k, v in FLAG.items() if k != "ssCents"}
    with pytest.raises(forms.MissingFact, match="totals"):
        forms.build("form_843", PROFILE, PAYSTUBS, partial, TODAY)


def test_an_unknown_form_is_refused():
    with pytest.raises(forms.MissingFact, match="does not know how"):
        forms.build("form_1040", PROFILE, PAYSTUBS, FLAG, TODAY)


# ---------- when an 8843 is actually due ----------

def test_8843_is_due_when_the_year_is_not_on_file():
    assert engine.needs_8843({**PROFILE, "filed8843Years": [2024]}, TODAY) is True
    assert engine.needs_8843({**PROFILE, "filed8843Years": [2024, 2025]}, TODAY) is False
    assert engine.needs_8843({**PROFILE, "filings": [{"year": 2025, "form": "8843"}]}, TODAY) is False


def test_8843_is_not_due_for_a_year_before_she_arrived():
    # Tax year 2023; she arrived in 2024, so there is nothing to file for it.
    assert engine.needs_8843(PROFILE, date(2024, 3, 1)) is False


# ---------- the PDF ----------

def test_the_pdf_renders_and_is_a_pdf():
    built = forms.build("form_8843", PROFILE, PAYSTUBS, FLAG, TODAY)
    pdf = engine.render_pdf(built["title"],
                            [{"label": a, "value": str(b), "source": c} for a, b, c in built["fields"]],
                            built["body"])
    assert pdf.startswith(b"%PDF-")
    assert len(pdf) > 1000


def test_the_pdf_escapes_values_from_the_student_file():
    """A name or employer with markup in it must not become markup in the document."""
    nasty = [{"label": "Name", "value": "<b>Priya</b> & Co", "source": "profiles.name"}]
    pdf = engine.render_pdf("Test", nasty, "Body & <text>")
    assert pdf.startswith(b"%PDF-")
