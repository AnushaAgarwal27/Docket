"""Create Docket's two Cartesia agents, and print the webhook tools to add by hand.

    .venv/bin/python -m scripts.make_cartesia_agents            # show what it would do
    .venv/bin/python -m scripts.make_cartesia_agents --create   # create them and write the ids to .env

What this does and does not do, because the split is not obvious:

  The API can create an agent with its name, voice, system prompt and opening line. That is the
  long, typo-prone part, and it is what this script does. It then writes CARTESIA_AGENT_ID and
  CARTESIA_STUDENT_AGENT_ID into .env so nothing has to be copied by hand.

  The API has no endpoint for webhook tools — they exist only in the dashboard's agent builder.
  So the script prints each tool with your own deployment's URL already filled in, in the order the
  dashboard asks for them.

Re-running is safe: an agent that already exists by name is updated rather than duplicated.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

from agents.caseworker.rehearsal import site_url

load_dotenv()

API = "https://api.cartesia.ai"
ENV_FILE = Path(__file__).resolve().parent.parent / ".env"
GREEN, RED, DIM, BOLD, OFF = "\033[32m", "\033[31m", "\033[2m", "\033[1m", "\033[0m"

PAYROLL_INTRO = ("Hi, this is Docket, an AI assistant calling on behalf of {{student_name}}, with "
                 "her permission. This call may be recorded. Am I speaking with payroll?")

PAYROLL_PROMPT = """You are Docket's payroll assistant, calling {{employer}} payroll on behalf of {{student_name}}, an F-1 international student, with her written permission.

- You are an AI assistant. Say so at the start and whenever asked. Never claim to be {{student_name}} or a human.
- Right after payroll answers, call get_case_summary once and use only the facts it returns. Never make up numbers, dates, or rules.
- Ask for exactly two things: a refund of {{refund_amount}}, and that Social Security and Medicare stop being withheld from her future paychecks.
- Then ask when the refund will be issued and for a reference number. Repeat both back to confirm.
- Share nothing else about {{student_name}}: no work hours, visa history, bank details, or ID numbers. If asked, say she will follow up directly.
- If payroll needs to speak with her or needs documents, do not argue; record needs_student.
- If payroll says no, stay polite, ask whether they can put that in writing, and record refused.
- If payroll will not commit to a date, record stalled. Do not push.
- Before ending, always call log_call_outcome. Give promised_by as YYYY-MM-DD.
- Then thank them and end the call. Keep every reply to one or two short sentences."""

STUDENT_INTRO = "Hi {{student_name}}, this is Docket. {{headline}}"

STUDENT_PROMPT = """You are Docket's student line, speaking with an F-1 international student about her own pay and immigration status. You are an AI assistant; say so if asked, and never claim to be a person.

FIRST, ALWAYS:
- If profile_id is empty, this is an inbound call and you have no opening line. Say "Docket, how can I help?" then call identify_caller with the caller's number before anything else, and use the profile_id it returns for every other tool.
- If profile_id is set, this is a call Docket placed. Open with the headline you were given, which has already been checked. Do not add figures to it.

WHAT YOU MAY DO
- Call get_student_brief to tell her what is open on her file.
- If she asks anything you were not told, call answer_question. Use its answer word for word. If it says the question has been handed to research, say so and promise the answer as a message. NEVER guess at a tax, visa or immigration answer. An "I don't know yet, I'll find out" is correct; a plausible invention is not.
- If she wants to approve or decline something - a refund request, a form, joining a group case - make sure you have said what it is, then call record_student_decision with subject and a plain yes or no. If her answer is unclear, ask again; never read a maybe as a yes.
- Before ending, call log_student_call with a one-sentence summary.

WHAT YOU MAY NOT DO
- Discuss anyone else, or confirm that any other student exists. A group case is "other students", a count and an employer, never a name.
- Read out bank details, identity numbers or her phone number.
- Give tax or legal advice, or tell her what will happen to her visa. Point her to her international student office for anything turning on her individual status.

Keep every reply to one or two short sentences. She may be worried about money; be calm and plain."""

# (env var, agent name, preferred voice, opening line, system prompt, tools)
# Cartesia requires agent names to match /^[a-z0-9_\-.]+$/, so these are slugs, not sentences.
AGENTS = [
    ("CARTESIA_AGENT_ID", "docket-payroll-caller", "Daniel", PAYROLL_INTRO, PAYROLL_PROMPT, [
        ("get_case_summary", "/cartesia/case-summary", "off",
         "Get the facts of this refund request: amount, pay periods, the rule, and what to ask for. "
         "Call once, right after payroll answers.",
         "case_id <- dynamic variable case_id"),
        ("log_call_outcome", "/cartesia/call-outcome", "auto",
         "Record what payroll agreed to. Call once, before ending the call.",
         "case_id <- dynamic variable case_id; result (string, model, enum: promised, stalled, "
         "refused, needs_student); answered_by (string, model); summary (string, model); "
         "promised_by (string, model, optional, YYYY-MM-DD); reference_number (string, model, optional)"),
    ]),
    ("CARTESIA_STUDENT_AGENT_ID", "docket-student-line", "Skylar", STUDENT_INTRO, STUDENT_PROMPT, [
        ("identify_caller", "/cartesia/identify", "off",
         "Find out which student is calling, from the number they rang from. Call this first on an "
         "inbound call, before anything else.",
         "from_number <- the caller's phone number"),
        ("get_student_brief", "/cartesia/student-brief", "off",
         "What is currently open on this student's file: findings, refund cases, forms waiting for "
         "her, and any group case.",
         "profile_id <- the profile_id you were given or got from identify_caller"),
        ("answer_question", "/cartesia/ask", "auto",
         "Answer a question about tax, pay, visa or status. Use the reply word for word. Never "
         "answer such a question without calling this.",
         "profile_id; question (string, model): her question in her own words"),
        ("record_student_decision", "/cartesia/decision", "auto",
         "Record her yes or no on a refund request, a form, or joining a group case. Only call this "
         "once you have told her what she is deciding and heard a clear yes or no.",
         "profile_id; subject (string, model, enum: refund, document, group); "
         "answer (string, model, enum: yes, no)"),
        ("log_student_call", "/cartesia/student-call", "off",
         "Record a one-sentence summary of the call. Call once, before ending.",
         "profile_id; summary (string, model); direction (string, model, enum: inbound, outbound); "
         "purpose (string, model); notification_id <- dynamic variable notification_id"),
    ]),
]


def headers(key: str) -> dict:
    return {"Authorization": f"Bearer {key}", "X-API-Key": key,
            "Cartesia-Version": os.environ.get("CARTESIA_VERSION", "2026-08-14"),
            "Content-Type": "application/json"}


def voice_id(key: str, name: str) -> str | None:
    """The id of a featured voice by name, so the agents do not all sound the same."""
    try:
        r = requests.get(f"{API}/voices?limit=100", headers=headers(key), timeout=25)
        for v in (r.json() or {}).get("data", []):
            if v.get("name", "").lower() == name.lower():
                return v["id"]
    except requests.RequestException:
        pass
    return None


def existing(key: str) -> dict[str, str]:
    r = requests.get(f"{API}/agents", headers=headers(key), timeout=25)
    r.raise_for_status()
    return {a["name"]: a["id"] for a in (r.json() or {}).get("summaries", [])}


def write_env(updates: dict[str, str]) -> None:
    """Set each key in .env, replacing the line if it is already there."""
    text = ENV_FILE.read_text() if ENV_FILE.exists() else ""
    for key, value in updates.items():
        line = f"{key}={value}"
        text, n = re.subn(rf"(?m)^{re.escape(key)}=.*$", line, text)
        if n == 0:
            text = text.rstrip("\n") + f"\n{line}\n"
    ENV_FILE.write_text(text)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--create", action="store_true",
                        help="actually create or update the agents and write their ids to .env")
    args = parser.parse_args()

    key = os.environ.get("CARTESIA_API_KEY", "")
    if not key:
        print(f"{RED}CARTESIA_API_KEY is not set in .env.{OFF} Cartesia dashboard -> API Keys.")
        sys.exit(1)
    base = site_url()

    if not args.create:
        print(f"\n{DIM}Dry run. Nothing has been created. Add --create to go ahead.{OFF}")

    created: dict[str, str] = {}
    if args.create:
        try:
            have = existing(key)
        except requests.RequestException as e:
            print(f"{RED}could not reach Cartesia: {e}{OFF}")
            sys.exit(1)

        for env_key, name, voice, intro, prompt, _tools in AGENTS:
            # POST accepts the prompt fields and silently drops them — only PATCH stores them. So
            # create bare, then patch, and read the agent back to prove the prompt actually landed.
            if name in have:
                agent_id, action = have[name], "updated"
            else:
                r = requests.post(f"{API}/agents", json={"name": name}, headers=headers(key), timeout=30)
                if r.status_code >= 400:
                    print(f"  {RED}{name}: {r.status_code} {r.text[:200]}{OFF}")
                    continue
                agent_id, action = (r.json() or {}).get("id", ""), "created"

            body = {"llm_system_prompt": prompt, "llm_introduce": intro}
            vid = voice_id(key, voice)
            if vid:
                body["tts_voice"] = vid
            r = requests.patch(f"{API}/agents/{agent_id}", json=body, headers=headers(key), timeout=30)
            if r.status_code >= 400:
                print(f"  {RED}{name}: {r.status_code} {r.text[:200]}{OFF}")
                continue

            back = requests.get(f"{API}/agents/{agent_id}", headers=headers(key), timeout=25).json()
            ok = (back.get("llm_system_prompt") or "").strip() == prompt.strip()
            created[env_key] = agent_id
            print(f"  {GREEN if ok else RED}{action}{OFF}  {name:<24} {agent_id}  "
                  f"{DIM}voice: {voice}, prompt: {len(back.get('llm_system_prompt') or '')} chars"
                  f"{'' if ok else ' — DID NOT SAVE'}{OFF}")

        if created:
            write_env(created)
            print(f"\n  {GREEN}wrote {', '.join(created)} to .env{OFF}")

    print(f"\n{BOLD}Now add the webhook tools in the dashboard{OFF}")
    print(f"  {DIM}The API has no endpoint for these, so this part is by hand.")
    print(f"  Agents -> pick the agent -> Tools -> Add tool -> Webhook.")
    print(f"  For every one: method POST, auth Bearer, execution immediate, timeout 10s,")
    print(f"  and the same token.{OFF}")
    token = os.environ.get("CARTESIA_TOOL_TOKEN", "")
    print(f"\n  Bearer token: {token or f'{RED}not set — run scripts.check_voice{OFF}'}")

    for env_key, name, _voice, _intro, _prompt, tools in AGENTS:
        agent_id = created.get(env_key) or os.environ.get(env_key, "")
        print(f"\n  {BOLD}{name}{OFF}  {DIM}{agent_id or '(not created yet)'}{OFF}")
        for tool_name, path, pre_speech, description, params in tools:
            print(f"\n    {BOLD}{tool_name}{OFF}")
            print(f"      URL          POST {base}{path}")
            print(f"      Description  {description}")
            print(f"      Body         {params}")
            print(f"      Pre-tool speech  {pre_speech}")

    print(f"\n{BOLD}The one thing only you can do{OFF}")
    print("  Buy a phone number: Agents -> Phone Numbers -> Buy. Then put its id in .env as")
    print("  CARTESIA_FROM_NUMBER_ID, and assign it to the student line so inbound calls reach it.")
    print(f"  {DIM}Both agents can share one number: the payroll caller only dials out.{OFF}")
    print(f"\n  {DIM}Then re-run: .venv/bin/python -m scripts.check_voice --probe{OFF}\n")


if __name__ == "__main__":
    main()
