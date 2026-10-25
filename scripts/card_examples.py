"""Write docs/CARD_EXAMPLES.md: one rendered example per card kind, to paste into the ASI:One Card Playground.

    .venv/bin/python -m scripts.card_examples

Uses Priya's synthetic numbers from seed/demo_data.py; the same builders the Coordinator sends.
"""
import json
from pathlib import Path

from agents.coordinator.cards import finding_detail, profile_form, refund_review, validate
from seed import demo_data

OUT = Path("docs/CARD_EXAMPLES.md")
QUOTE = ("Social security and Medicare taxes are not withheld from pay for the work unless the student is "
         "considered a resident alien.")


def main() -> None:
    ss = sum(p["ssCents"] for p in demo_data.paystubs())
    medicare = sum(p["medicareCents"] for p in demo_data.paystubs())
    cards = [
        profile_form(),
        finding_detail("Social Security and Medicare withheld", [
            ("Social Security", "$357.12 · high confidence"),
            ("Medicare", "$83.52 · medium confidence: an exception may apply"),
        ], QUOTE, "IRS Publication 519", "Social Security upheld; Medicare downgraded", "example_flag_id",
            "The Hearing is over. Here is the verdict."),
        refund_review(demo_data.EMPLOYER, ss + medicare, ss, medicare, "Social Security upheld; Medicare downgraded",
                      "example_case_id", None, "Approve and I'll contact payroll; nothing happens until you do."),
    ]
    lines = ["# Interactive Card examples", "",
             "Paste a payload into https://asi1.ai/developer/card-playground to see it rendered. Each card is sent as a",
             "ChatMessage with TextContent (the text above the card) and one MetadataContent holding the metadata below.",
             "Regenerate with `python -m scripts.card_examples`.", ""]
    for card in cards:
        assert validate(card) == [], validate(card)
        meta = card.metadata()
        lines += [f"## {card.kind}", "", f"Text: {card.text}", "", "Payload (`card_payload`):", "", "```json",
                  json.dumps(card.payload, indent=2), "```", "", "Metadata:", "", "```json",
                  json.dumps({k: v for k, v in meta.items() if k != "card_payload"} | {"card_payload": "<payload above, as a JSON string>"}, indent=2),
                  "```", ""]
    OUT.write_text("\n".join(lines))
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
