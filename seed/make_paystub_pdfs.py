"""Render Priya's 8 synthetic paystubs to PDFs for the Ledger agent to extract.

    python -m seed.make_paystub_pdfs [out_dir]
"""
import sys
from datetime import date, timedelta
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

from seed import demo_data


def money(cents: int) -> str:
    return f"${cents // 100:,}.{cents % 100:02d}"


def render(stub: dict, path: Path) -> None:
    c = canvas.Canvas(str(path), pagesize=letter)
    y = 740
    def line(text, size=11, gap=18):
        nonlocal y
        c.setFont("Helvetica", size)
        c.drawString(72, y, text)
        y -= gap

    line(demo_data.EMPLOYER, 16, 22)
    line("Earnings Statement  -  SYNTHETIC DEMO DOCUMENT", 9, 28)
    p = demo_data.PROFILE
    line(f"Employee: {p['name']}        School: {p['school']}")
    line(f"Pay period: {stub['periodStart']} to {stub['periodEnd']}", gap=28)
    start = date.fromisoformat(stub["periodStart"])
    for i, h in enumerate(stub["hoursByWeek"]):
        wk = start + timedelta(days=7 * i)
        line(f"Hours, week of {wk.isoformat()}: {h:.2f}")
    line(f"Rate: {money(demo_data.RATE_CENTS)} per hour", gap=28)
    line(f"Gross pay: {money(stub['grossCents'])}")
    line(f"Social Security (OASDI) withheld: {money(stub['ssCents'])}")
    line(f"Medicare withheld: {money(stub['medicareCents'])}")
    line("Federal income tax withheld: $0.00", gap=28)
    line(f"Net pay: {money(stub['netCents'])}", 13)
    c.save()


if __name__ == "__main__":
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "seed/paystubs")
    out.mkdir(parents=True, exist_ok=True)
    for stub in demo_data.paystubs():
        render(stub, out / stub["sourceFile"])
    print(f"Wrote {demo_data.PAYSTUB_COUNT} paystubs to {out}")
