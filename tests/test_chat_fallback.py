import asyncio
import logging

import agents.coordinator.agent as coord


class Ctx:
    logger = logging.getLogger("test")


def run(text, monkeypatch, answer=None, selection=None, log=None):
    logged = []
    monkeypatch.setattr(coord, "answer", answer or (lambda ctx, t: _ok("answered")))
    monkeypatch.setattr(coord, "answer_selection", selection or (lambda ctx, s: _ok(f"selected {s['action']}")))
    monkeypatch.setattr(coord, "log", log or (lambda *a, **k: logged.append(a)))
    return asyncio.run(coord.handle(Ctx(), text, {})), logged


async def _ok(value):
    return value


async def _boom(*_):
    raise RuntimeError("Convex is down")


def test_card_json_goes_to_the_selection_handler(monkeypatch):
    out, _ = run('{"action": "approve_refund"}', monkeypatch)
    assert out == ["selected approve_refund"]


def test_plain_text_goes_to_answer(monkeypatch):
    out, _ = run("check my pay", monkeypatch)
    assert out == ["answered"]


def test_failure_gives_a_fallback_reply_and_logs_it(monkeypatch):
    out, logged = run("check my pay", monkeypatch, answer=_boom)
    assert out == [coord.FAILED] and "Nothing was sent" in out[0]
    assert logged[0][:2] == ("coordinator", "chat_failed") and "Convex is down" in logged[0][2]


def test_failure_while_logging_still_replies(monkeypatch):
    def broken_log(*a, **k):
        raise ConnectionError("no network")
    out, _ = run("check my pay", monkeypatch, answer=_boom, log=broken_log)
    assert out == [coord.FAILED]
