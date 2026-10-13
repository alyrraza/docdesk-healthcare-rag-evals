"""The judge parser reads plain or fenced JSON and counts every failure instead of hiding it."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from docdesk.evals.judges.parser import JudgeParser


class Verdict(BaseModel):
    model_config = ConfigDict(extra="forbid")

    supported: bool
    note: str


GOOD = '{"supported": true, "note": "ok"}'


def test_t079c_plain_json_parses() -> None:
    parser = JudgeParser(Verdict)
    assert parser.parse(GOOD) == Verdict(supported=True, note="ok")
    assert (parser.attempts, parser.failures) == (1, [])


def test_t079c_a_fenced_json_block_is_unwrapped() -> None:
    parser = JudgeParser(Verdict)
    assert parser.parse(f"```json\n{GOOD}\n```") == Verdict(supported=True, note="ok")


def test_t079c_a_fence_without_a_language_and_with_chatter_around_it_is_unwrapped() -> None:
    parser = JudgeParser(Verdict)
    reply = f"Here is my verdict:\n```\n{GOOD}\n```\nHope that helps."
    assert parser.parse(reply) == Verdict(supported=True, note="ok")


def test_t079c_text_that_is_not_json_is_a_counted_failure_not_a_pass() -> None:
    parser = JudgeParser(Verdict)
    assert parser.parse("I think it is supported.") is None
    assert parser.attempts == 1
    assert len(parser.failures) == 1


def test_t079c_json_of_the_wrong_shape_is_a_counted_failure() -> None:
    parser = JudgeParser(Verdict)
    assert parser.parse('{"supported": "maybe", "note": "x"}') is None
    assert parser.parse('{"supported": true, "note": "x", "extra": 1}') is None
    assert len(parser.failures) == 2


def test_t079c_an_empty_reply_is_a_counted_failure() -> None:
    parser = JudgeParser(Verdict)
    assert parser.parse("") is None
    assert parser.parse("   \n") is None
    assert len(parser.failures) == 2


def test_t079c_failures_and_attempts_add_up_over_a_run() -> None:
    parser = JudgeParser(Verdict)
    for reply in [GOOD, "nope", GOOD, "{"]:
        parser.parse(reply)
    assert parser.attempts == 4
    assert len(parser.failures) == 2
    assert parser.failure_rate == 0.5


def test_t079c_failure_rate_is_zero_before_any_attempt() -> None:
    assert JudgeParser(Verdict).failure_rate == 0.0


def test_t079c_a_failure_reason_is_short() -> None:
    parser = JudgeParser(Verdict)
    parser.parse("x" * 5000)
    assert len(parser.failures[0]) <= 200
