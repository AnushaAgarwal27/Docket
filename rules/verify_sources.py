"""Check every rule's quote against the fetched source text before the demo.

Fetched pages live in sources/<source_id>.txt (`python -m rules.download_sources` writes them;
Convex `sources` holds the same text). Exits non-zero if any quote fails. Sources outside the
allow-list (IRS, USCIS, the university) are reported as unverified.

    python -m rules.verify_sources
"""
import sys
from pathlib import Path

from rules.engine import load_rules
from rules.quote_checker import check_quote, source_status

SOURCES_DIR = Path("sources")


def main() -> int:
    failed = 0
    for rule in load_rules():
        path = SOURCES_DIR / f"{rule['source_id']}.txt"
        if not path.exists():
            print(f"MISSING  {rule['id']}: no {path}")
            failed += 1
            continue
        result = check_quote(rule["quote"], path.read_text())
        status = source_status(rule["source_url"])
        print(f"{'OK      ' if result.ok else 'FAIL    '}{rule['id']}: {result.reason}; {status} source")
        failed += not result.ok
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
