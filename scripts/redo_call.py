"""Undo the payroll call so you can do it again.

    .venv/bin/python -m scripts.redo_call

Puts the case back to the moment before the student approved it and forgets the call that followed.
Takes about a second.

Use this between takes. `scripts.demo_reset` also gets you there but costs about a minute, because
it re-reads all eight paystubs through Claude. Nothing about the paystubs, the flags or the hearing
changes between one rehearsal of the call and the next -- only the case state and the call do --
so this rewinds only those. The amount stays exactly what the rules computed, which is the point:
a redo must not be a chance for the total to drift.

Reach for demo_reset instead when the paystubs, the rules or the seed data have changed, or when
you want the activity feed empty for a recording.
"""
from __future__ import annotations

from dotenv import load_dotenv

from agents.store import dollars, mutation, query

load_dotenv()

GREEN, RED, DIM, BOLD, OFF = "\033[32m", "\033[31m", "\033[2m", "\033[1m", "\033[0m"


def main() -> None:
    profile = next((p for p in query("profiles:list") if not p.get("simulated")), None)
    if profile is None:
        print(f"{RED}No student file.{OFF} Run: .venv/bin/python -m scripts.demo_reset --no-approve")
        return

    cases = query("cases:listByProfile", {"profileId": profile["_id"]})
    if not cases:
        print(f"{RED}No case to rewind.{OFF} Run: .venv/bin/python -m scripts.demo_reset --no-approve")
        return

    case = max(cases, key=lambda c: c["_creationTime"])
    before = case["state"]
    if before == "awaiting_approval":
        print(f"{DIM}Already waiting for her yes; nothing to undo.{OFF}")
    else:
        result = mutation("cases:rewindForDemo", {"caseId": case["_id"]}) or {}
        calls = result.get("callsDeleted", 0)
        print(f"{GREEN}Rewound.{OFF} {before} -> awaiting_approval"
              f"   {calls} call{'' if calls == 1 else 's'} forgotten")

    after = query("cases:get", {"caseId": case["_id"]})
    print(f"\n{BOLD}{profile['name']}{OFF}  {dollars(after['amountCents'])}  {after['state']}")
    print("\nApprove it again from whichever surface you are showing:")
    print("  the Hearing game   http://localhost:5173/game.html  -> Open the case -> Approve the call")
    print("  ASI:One            say \"yes, contact payroll\" to docket-coordinator")
    print("  the dashboard      the Approve button on the case")
    print(f"\n{DIM}Then check it recorded:  .venv/bin/python -m scripts.demo_ready{OFF}\n")


if __name__ == "__main__":
    main()
