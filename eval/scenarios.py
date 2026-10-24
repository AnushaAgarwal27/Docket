"""Live scenario checks for the agent behaviours, against the running agents (scripts/run_agents.sh).

    .venv/bin/python -m eval.scenarios                  # all scenarios, in order
    .venv/bin/python -m eval.scenarios refund readme    # just these

A throwaway student agent talks to the Coordinator over the real chat protocol, the same way ASI:One
does, and records every message it gets, including the ones it did not ask for. The run resets the
demo first, so it wipes Convex and Nessie demo state like `python -m seed.reset`.

Scenarios (one per change):
  notice     Ledger -> Tax on new paystubs: flags appear and Priya is told, with no message from her
  intent     indirect wording is understood; the reply carries the verified clause and the disclaimer
  season     "next season" answer uses her year count and last year's filings
  approve    an ambiguous "sure" does not approve; "yes" does
  refund     payroll promises, the refund lands, and Priya is told without asking
  readme     Agentverse lists docket-coordinator with a readme
"""
from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from datetime import datetime, timezone
from uuid import uuid4

import requests
from dotenv import load_dotenv
from uagents import Agent, Context, Protocol
from uagents_core.contrib.protocols.chat import ChatAcknowledgement, ChatMessage, TextContent, chat_protocol_spec

load_dotenv()

from agents.store import mutation, query  # noqa: E402  (needs .env loaded)

COORDINATOR = os.environ.get("COORDINATOR_ADDRESS", "agent1qwj0e7jf5gu6lw3tael5ld2v8xeg4jrzgs8wx7yg22a82du6dcqeqtr0686")
PY = sys.executable
ORDER = ["notice", "intent", "season", "approve", "refund", "readme"]
FICA_CLAUSE = "Social security and Medicare taxes are not withheld from pay for the work"
DISCLAIMER_END = "confirm with your international student office."

student = Agent(name="docket-scenario-student", seed="docket-scenario-student-local-only", port=8018,
                endpoint=["http://127.0.0.1:8018/submit"])
chat = Protocol(spec=chat_protocol_spec)
inbox: asyncio.Queue[str] = asyncio.Queue()
results: list[tuple[str, bool, str]] = []


@chat.on_message(ChatMessage)
async def on_message(ctx: Context, sender: str, msg: ChatMessage):
    await ctx.send(sender, ChatAcknowledgement(timestamp=datetime.now(timezone.utc), acknowledged_msg_id=msg.msg_id))
    for item in msg.content:
        if isinstance(item, TextContent):
            await inbox.put(item.text)


@chat.on_message(ChatAcknowledgement)
async def on_ack(ctx: Context, sender: str, msg: ChatAcknowledgement):
    pass


student.include(chat)


async def say(ctx: Context, text: str, timeout: float = 90) -> str:
    while not inbox.empty():
        inbox.get_nowait()
    print(f"  >>> {text}", flush=True)
    await ctx.send(COORDINATOR, ChatMessage(timestamp=datetime.now(timezone.utc), msg_id=uuid4(),
                                            content=[TextContent(type="text", text=text)]))
    return await wait_for(lambda t: True, timeout)


async def wait_for(match, timeout: float) -> str:
    """The next inbox message that matches, or "" on timeout."""
    deadline = asyncio.get_running_loop().time() + timeout
    while True:
        left = deadline - asyncio.get_running_loop().time()
        if left <= 0:
            return ""
        try:
            text = await asyncio.wait_for(inbox.get(), left)
        except asyncio.TimeoutError:
            return ""
        if match(text):
            print(f"  <<< {text[:160]!r}", flush=True)
            return text


def check(name: str, ok: bool, detail: str) -> None:
    results.append((name, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}: {detail}", flush=True)


def profile_id() -> str:
    return query("profiles:list")[0]["_id"]


async def wait_paystubs(n: int, timeout: float = 240) -> int:
    count = 0
    for _ in range(int(timeout / 5)):
        count = len(await asyncio.to_thread(query, "paystubs:listByProfile", {"profileId": profile_id()}))
        if count >= n:
            break
        await asyncio.sleep(5)
    return count


async def scenario_notice(ctx: Context):
    await say(ctx, "hi")  # so the Coordinator knows where to reach this student
    await asyncio.to_thread(subprocess.run, [PY, "-m", "seed.reset"], check=True, capture_output=True)
    told = await wait_for(lambda t: "paystub" in t.lower() and "issue" in t.lower(), timeout=300)
    flags = await asyncio.to_thread(query, "flags:listByProfile", {"profileId": profile_id()})
    check("notice", bool(told) and len(flags) >= 1,
          f"{len(flags)} flags written and {'Priya was told' if told else 'no message to Priya'}, without her asking")


async def scenario_intent(ctx: Context):
    if await wait_paystubs(8) < 8:
        check("intent", False, "paystubs never arrived")
        return
    text = await say(ctx, "am I paying tax I shouldn't?")
    ok = FICA_CLAUSE in text and text.rstrip().lower().endswith(DISCLAIMER_END) and "$440.64" in text
    check("intent", ok, "indirect wording answered with $440.64, the verified IRS clause, ending with the disclaimer"
          if ok else f"got {text[:160]!r}")
    vague = await say(ctx, "hmm")
    check("intent-other", "check my pay" in vague, "an unclear message gets the help text, not a guess")


async def scenario_season(ctx: Context):
    text = await say(ctx, "what do I need to do for next tax season?")
    ok = "8843" in text and "calendar year 3" in text and "2025" in text
    check("season", ok, "mentions Form 8843, calendar year 3, and last year's (2025) filing" if ok else f"got {text[:120]!r}")


async def scenario_approve(ctx: Context):
    await say(ctx, "check my pay")  # make sure a case is waiting for approval
    vague = await say(ctx, "sure go ahead")
    yes = await say(ctx, "yes")
    check("approve", "reply **YES**" in vague and "Approved" in yes,
          "ambiguous wording asked for an explicit YES; YES approved")


async def scenario_refund(ctx: Context):
    cases = await asyncio.to_thread(query, "cases:listByProfile", {"profileId": profile_id()})
    case = next((c for c in cases if c["state"] in ("contacting_employer", "awaiting_response")), None)
    if case is None:
        check("refund", False, "no approved case to refund")
        return
    if case["state"] == "contacting_employer":  # stands in for the Cartesia call's log_call_outcome
        await asyncio.to_thread(mutation, "cases:logCallOutcome", {
            "caseId": case["_id"], "answeredBy": "Payroll (scenario check)", "summary": "Agreed to refund",
            "result": "promised", "promisedBy": "2026-11-07"})
    await asyncio.to_thread(subprocess.run, [PY, "-m", "seed.release_refund", "2026-11-07"], check=True,
                            capture_output=True)
    told = await wait_for(lambda t: "landed" in t, timeout=120)
    state = (await asyncio.to_thread(query, "cases:get", {"caseId": case["_id"]}))["state"]
    check("refund", bool(told) and state == "closed",
          f"case {state}; {'Priya was told the refund landed' if told else 'no message to Priya'}")


async def scenario_readme(ctx: Context):
    r = requests.post("https://agentverse.ai/v1/search/agents", json={"search_text": "docket-coordinator", "limit": 5},
                      timeout=20)
    agent = next((a for a in r.json().get("agents", []) if a["address"] == COORDINATOR), None)
    check("readme", bool(agent and agent.get("readme")),
          "Agentverse shows the readme" if agent and agent.get("readme") else "no readme on Agentverse yet")


@student.on_event("startup")
async def run(ctx: Context):
    await asyncio.sleep(3)
    wanted = [s for s in ORDER if s in sys.argv[1:]] or ORDER
    for name in wanted:
        print(f"\n== {name}", flush=True)
        try:
            await globals()[f"scenario_{name}"](ctx)
        except Exception as e:
            check(name, False, f"error: {e}")
    passed = sum(ok for _, ok, _ in results)
    print(f"\n{passed}/{len(results)} scenarios passed", flush=True)
    os._exit(0 if passed == len(results) else 1)


if __name__ == "__main__":
    student.run()
