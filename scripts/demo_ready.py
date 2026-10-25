"""Put the demo in the state a payroll call expects, so you can rehearse the call on its own.

    .venv/bin/python -m scripts.demo_ready          # show the state and what is blocking a call
    .venv/bin/python -m scripts.demo_ready --arm    # move the case to contacting_employer

Why this exists. Docket will not record a payroll call on a case the student has not approved:
cases.logCallOutcome can only reach awaiting_response from contacting_employer, and only
cases:approve gets it there. That rule is right — it is what stops a call being logged against
someone who never agreed to it — but it bites when you dial from the Cartesia dashboard, which
skips Docket entirely.

The failure is quiet from the caller's side. The webhook returns 409 and tells the voice agent to
thank payroll and end the call, so a rejected write sounds exactly like a successful one. You find
out afterwards, by looking in the database. --arm avoids that by approving first.

For the real demo, approve the way a student would — "yes" in ASI:One, or the dashboard button —
and the case arms itself.
"""
from __future__ import annotations

import argparse

from dotenv import load_dotenv

from agents.store import dollars, mutation, query

load_dotenv()

GREEN, RED, DIM, BOLD, OFF = "\033[32m", "\033[31m", "\033[2m", "\033[1m", "\033[0m"

# Where a case has to be before a payroll call can record its outcome.
READY = "contacting_employer"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arm", action="store_true",
                        help="approve the refund case so a call outcome can be recorded")
    args = parser.parse_args()

    profile = next((p for p in query("profiles:list") if not p.get("simulated")), None)
    if profile is None:
        print(f"{RED}No student file. Run: python -m seed.reset{OFF}")
        return

    cases = query("cases:listByProfile", {"profileId": profile["_id"]})
    if not cases:
        print(f"{RED}No refund case yet.{OFF} Run the rules and open one:")
        print("  .venv/bin/python -m scripts.chat_test \"check my pay\"")
        return

    case = max(cases, key=lambda c: c["_creationTime"])
    # cases:listByProfile returns the case rows alone; only the dashboard snapshot joins the calls
    # onto them. Reading case["calls"] here always said zero, whether or not a call had been
    # recorded — which is worse than not showing it at all.
    snapshot = query("dashboard:snapshot", {"profileId": profile["_id"]}) or {}
    joined = next((c for c in snapshot.get("cases", []) if c["_id"] == case["_id"]), {})
    calls = joined.get("calls") or []

    print(f"\n{BOLD}{profile['name']}{OFF}  case {case['_id']}")
    print(f"  amount  {dollars(case['amountCents'])}")
    print(f"  state   {case['state']}")
    print(f"  calls   {len(calls)} recorded")
    for call in calls:
        print(f"    - {call.get('answeredBy')}: {(call.get('summary') or '')[:70]}")
        print(f"      promised {call.get('promisedBy') or '(no date)'}"
              f"   reference {call.get('referenceNo') or '(none)'}")

    if case["state"] == READY:
        print(f"\n  {GREEN}Ready.{OFF} A payroll call can record its outcome now.")
    elif case["state"] == "awaiting_approval":
        if not args.arm:
            print(f"\n  {RED}Not ready.{OFF} The student has not approved this case, so "
                  f"log_call_outcome will be rejected with 409 and")
            print(f"  the call will still sound like it worked. Re-run with --arm, or approve it "
                  f"the way she would:")
            print(f"    .venv/bin/python -m scripts.chat_test \"check my pay\" \"yes\"")
            return
        mutation("cases:approve", {"caseId": case["_id"]})
        after = query("cases:get", {"caseId": case["_id"]})
        print(f"\n  {GREEN}Armed.{OFF} {case['state']} -> {after['state']}")
        print(f"  {DIM}This is exactly what Priya clicking Approve does.{OFF}")
    else:
        print(f"\n  {DIM}Nothing to arm: a case in {case['state']} has already been through "
              f"the call.{OFF}")
        print(f"  {DIM}For a fresh run: .venv/bin/python -m seed.reset{OFF}")

    print(f"\n  {DIM}After the call, check it actually saved:{OFF}")
    print(f"    .venv/bin/python -m scripts.demo_ready\n")


if __name__ == "__main__":
    main()
