from datetime import date

from agents.caseworker.letter import DISCLAIMER, letter_paragraphs, render_pdf
from seed.demo_data import PROFILE, paystubs

FLAG = {"amountCents": 44064, "ssCents": 35712, "medicareCents": 8352,
        "quote": "Social security and Medicare taxes are not withheld from pay for the work unless the student is "
                 "considered a resident alien."}


def test_letter_uses_the_flag_amounts_quote_and_disclaimer():
    text = "\n".join(letter_paragraphs(PROFILE, FLAG, paystubs(), "IRS Publication 519", date(2026, 10, 24)))
    assert "$357.12" in text and "$83.52" in text and "$440.64" in text
    assert FLAG["quote"] in text and "IRS Publication 519 states" in text
    assert "2026-01-12 to 2026-05-03" in text and "8 paychecks" in text
    assert text.endswith(DISCLAIMER)


def test_letter_numbers_come_from_the_flag_not_the_paystubs():
    # If the paystubs and the flag disagree, the letter says what the rule computed.
    text = "\n".join(letter_paragraphs(PROFILE, {**FLAG, "amountCents": 1}, paystubs(), "IRS", date(2026, 10, 24)))
    assert "$0.01" in text and "$440.64" not in text


def test_pdf_renders():
    pdf = render_pdf(letter_paragraphs(PROFILE, FLAG, paystubs(), "IRS Publication 519 <&>", date(2026, 10, 24)))
    assert pdf.startswith(b"%PDF") and len(pdf) > 1000
