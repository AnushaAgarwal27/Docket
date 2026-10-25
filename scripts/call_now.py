"""Place a real payroll call through Docket's own code path, for rehearsing the demo.

    .venv/bin/python -m scripts.call_now

This is the path the demo actually uses — agents/caseworker/cartesia.py, with the dynamic variables
built from live Convex data — rather than the Cartesia dashboard's dialler. The difference matters
when debugging: the dashboard lets you type variables by hand, so an agent can narrate the right
amount and employer without ever calling a webhook. Here the variables come from the case, so if
the tools do not fire you see it.

Safe to re-run. While the demo redirect is on, only DEMO_CALL_NUMBER rings, and the case is left
alone: placing a call does not move it, so a missed call costs nothing.
"""
from __future__ import annotations

from dotenv import load_dotenv

import os

from agents.caseworker import cartesia, rehearsal
from agents.store import dollars, query
from agents.voice import calls

load_dotenv()

GREEN, RED, DIM, BOLD, OFF = "\033[32m", "\033[31m", "\033[2m", "\033[1m", "\033[0m"
READY = "contacting_employer"


def main() -> None:
    if rehearsal.enabled():
        print(f"{RED}CARTESIA_SIMULATE is on, so no phone will ring.{OFF} "
              f"Unset it in .env for a real call.")
        return

    profile = next((p for p in query("profiles:list") if not p.get("simulated")), None)
    if profile is None:
        print(f"{RED}No student file.{OFF} Run: python -m seed.reset")
        return

    cases = query("cases:listByProfile", {"profileId": profile["_id"]})
    case = next((c for c in cases if c["state"] == READY), None)
    if case is None:
        states = ", ".join(sorted({c["state"] for c in cases})) or "none"
        print(f"{RED}No case is ready to call about.{OFF} States on file: {states}")
        print(f"  {DIM}Arm one with: .venv/bin/python -m scripts.demo_ready --arm{OFF}")
        return

    paystubs = query("paystubs:listByProfile", {"profileId": profile["_id"]})
    variables = cartesia.call_variables(case, profile, paystubs)

    print(f"\n{BOLD}Calling about{OFF}  {case['_id']}  {dollars(case['amountCents'])}")
    print(f"  {DIM}dynamic variables, built from the case — not typed by hand:{OFF}")
    for k, v in variables.items():
        print(f"    {k:<16} {v}")
    dialled, intended = calls.destination(os.environ["PAYROLL_PHONE"])
    print(f"\n  ringing {BOLD}{dialled}{OFF}"
          + (f"  {DIM}(the call is about {intended}){OFF}" if dialled != intended else ""))

    try:
        call_id = cartesia.place_call(case, profile, paystubs)
    except cartesia.CallError as e:
        print(f"\n  {RED}could not start the call: {e}{OFF}")
        return

    print(f"\n  {GREEN}placed{OFF}  {call_id}")
    print(f"  {DIM}Play payroll: 'Hello?' then agree, give a date, then let it hang up.{OFF}")
    print(f"\n  Afterwards:  .venv/bin/python -m scripts.demo_ready\n")


if __name__ == "__main__":
    main()
