"""Everything you need to set up the Cartesia agents, printed for your own deployment.

    .venv/bin/python -m scripts.check_voice            # what to paste, and what is still missing
    .venv/bin/python -m scripts.check_voice --probe    # also call every webhook and show the reply

The point of this script is that docs/CARTESIA.md cannot know which Convex deployment you are on.
Pasting a teammate's site URL into the Cartesia dashboard is the single most common way to lose an
hour here: the tools come back 401, or worse, they succeed against the wrong student file, and
nothing in the Cartesia UI tells you which happened.
"""
from __future__ import annotations

import argparse
import os
import sys

import requests
from dotenv import load_dotenv

from agents.caseworker.rehearsal import site_url
from agents.store import query

load_dotenv()

GREEN, RED, DIM, BOLD, OFF = "\033[32m", "\033[31m", "\033[2m", "\033[1m", "\033[0m"

PAYROLL_TOOLS = [("get_case_summary", "/cartesia/case-summary"),
                 ("log_call_outcome", "/cartesia/call-outcome")]
STUDENT_TOOLS = [("identify_caller", "/cartesia/identify"),
                 ("get_student_brief", "/cartesia/student-brief"),
                 ("answer_question", "/cartesia/ask"),
                 ("record_student_decision", "/cartesia/decision"),
                 ("log_student_call", "/cartesia/student-call")]

# (env var, what it is, where you get it)
NEEDED = [
    ("CARTESIA_API_KEY", "your Cartesia API key", "Cartesia dashboard -> API Keys"),
    ("CARTESIA_FROM_NUMBER_ID", "the number both agents call from",
     "Cartesia dashboard -> Phone Numbers (the id, not the number itself)"),
    ("CARTESIA_AGENT_ID", "the payroll caller", "Cartesia dashboard -> Agents, after you create it"),
    ("CARTESIA_STUDENT_AGENT_ID", "the student line", "Cartesia dashboard -> Agents, after you create it"),
    ("PAYROLL_PHONE", "who the payroll request is for, E.164",
     "a teammate's phone. Only rings if you turn the demo redirect off"),
]


def tick(ok: bool) -> str:
    return f"{GREEN}OK{OFF}" if ok else f"{RED}--{OFF}"


def probe(base: str, token: str) -> None:
    """Call every webhook once. A 200 means Cartesia will get the same answer."""
    profiles = [p for p in query("profiles:list") if not p.get("simulated")]
    if not profiles:
        print(f"  {RED}no student file yet; run `python -m seed.reset` first{OFF}")
        return
    pid = profiles[0]["_id"]
    cases = query("cases:listByProfile", {"profileId": pid})
    case_id = cases[0]["_id"] if cases else None
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    bodies = {
        "/cartesia/identify": {"from_number": profiles[0].get("phone") or "+19259677432"},
        "/cartesia/student-brief": {"profile_id": pid},
        "/cartesia/ask": {"profile_id": pid, "question": "what is form 8843"},
        "/cartesia/decision": {"profile_id": pid, "subject": "refund", "answer": "no"},
        "/cartesia/student-call": {"profile_id": pid, "summary": "Setup check.",
                                   "direction": "outbound", "purpose": "setup_check"},
        "/cartesia/case-summary": {"case_id": case_id},
    }
    for name, path in STUDENT_TOOLS + PAYROLL_TOOLS[:1]:
        body = bodies.get(path)
        if body is None or (path == "/cartesia/case-summary" and case_id is None):
            print(f"  {DIM}skipped {name} (no case on file yet){OFF}")
            continue
        try:
            r = requests.post(base + path, json=body, headers=headers, timeout=25)
        except requests.RequestException as e:
            print(f"  {RED}{name}: could not reach it ({type(e).__name__}){OFF}")
            continue
        mark = tick(r.status_code == 200)
        print(f"  {mark} {name:<26} {r.status_code}  {DIM}{r.text[:72].strip()}{OFF}")
    print(f"\n  {DIM}log_call_outcome is not probed: it would move a real case's state.{OFF}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe", action="store_true", help="call every webhook and show the reply")
    args = parser.parse_args()

    try:
        base = site_url()
    except KeyError:
        print(f"{RED}CONVEX_URL is not set in .env. Run `npx convex dev` first.{OFF}")
        sys.exit(1)
    token = os.environ.get("CARTESIA_TOOL_TOKEN", "")

    print(f"\n{BOLD}Your deployment{OFF}")
    print(f"  site URL   {base}")
    print(f"  {DIM}this is the base for every webhook URL below. Not a teammate's.{OFF}")

    print(f"\n{BOLD}Webhook tools — paste these into the Cartesia dashboard{OFF}")
    print(f"  {DIM}All POST. Auth: Bearer. Token: the CARTESIA_TOOL_TOKEN value below.{OFF}")
    print(f"\n  {DIM}On the payroll caller (CARTESIA_AGENT_ID):{OFF}")
    for name, path in PAYROLL_TOOLS:
        print(f"    {name:<26} {base}{path}")
    print(f"\n  {DIM}On the student line (CARTESIA_STUDENT_AGENT_ID):{OFF}")
    for name, path in STUDENT_TOOLS:
        print(f"    {name:<26} {base}{path}")

    print(f"\n{BOLD}Bearer token{OFF}")
    if token:
        print(f"  {token}")
    else:
        print(f"  {RED}not set.{OFF} Generate one and set it in both places:")
        print("    openssl rand -hex 24")
        print("    npx convex env set CARTESIA_TOOL_TOKEN <that value>")
        print("    ...then put the same value in .env as CARTESIA_TOOL_TOKEN")

    # The commonest failure: the token was set on Convex but not copied into .env, or vice versa.
    if token:
        try:
            r = requests.post(f"{base}/cartesia/identify", json={"from_number": "+10000000000"},
                              headers={"Authorization": f"Bearer {token}",
                                       "Content-Type": "application/json"}, timeout=20)
            if r.status_code == 401:
                print(f"  {RED}Convex rejects this token.{OFF} The value in .env and the one on Convex differ.")
                print("  Fix with:  npx convex env get CARTESIA_TOOL_TOKEN   (then paste it into .env)")
            else:
                print(f"  {GREEN}Convex accepts this token.{OFF}")
        except requests.RequestException as e:
            print(f"  {RED}could not reach Convex ({type(e).__name__}){OFF}")

    print(f"\n{BOLD}Still needed in .env{OFF}")
    missing = []
    for key, what, where in NEEDED:
        value = os.environ.get(key, "").strip()
        print(f"  {tick(bool(value))} {key:<27} {what}")
        if not value:
            missing.append((key, where))
    if missing:
        print(f"\n  {DIM}where each one comes from:{OFF}")
        for key, where in missing:
            print(f"    {key:<27} {where}")

    simulate = os.environ.get("CARTESIA_SIMULATE", "").strip().lower() in {"1", "true", "yes"}
    redirect = os.environ.get("DEMO_CALL_REDIRECT", "1").strip().lower() not in {"0", "false", "no"}
    demo_number = os.environ.get("DEMO_CALL_NUMBER") or "+19259677432"

    print(f"\n{BOLD}What will actually happen on an approval right now{OFF}")
    if simulate:
        print(f"  {DIM}CARTESIA_SIMULATE=1: a stand-in call runs the two webhooks against Convex.")
        print(f"  No phone rings. Good for rehearsing; unset it when you want a real call.{OFF}")
    elif missing:
        print(f"  {DIM}Nothing is dialled: {len(missing)} setting(s) above are still empty.")
        print(f"  The dashboard and activity feed will say which one.{OFF}")
    elif redirect:
        print(f"  A real call is placed, and {BOLD}only {demo_number} rings{OFF} (demo redirect is on).")
        print(f"  {DIM}The number the call is for travels with it and shows on the dashboard.{OFF}")
    else:
        print(f"  {RED}A real call is placed to the real number. The demo redirect is OFF.{OFF}")

    if args.probe:
        print(f"\n{BOLD}Probing the webhooks{OFF}")
        if not token:
            print(f"  {RED}no token; set CARTESIA_TOOL_TOKEN first{OFF}")
        else:
            probe(base, token)
    else:
        print(f"\n  {DIM}Run with --probe to call every webhook and see what Cartesia will get.{OFF}")
    print()


if __name__ == "__main__":
    main()
