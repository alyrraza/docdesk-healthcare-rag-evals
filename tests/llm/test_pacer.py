"""The pacer keeps calls under the per model per minute limits by waiting, never by failing."""

from __future__ import annotations

from docdesk.llm.client import LLMRequest
from docdesk.llm.pacer import ModelLimits, PacedClient, Pacer
from fakes.llm import FakeLLMClient


class FakeTime:
    """A clock where sleeping moves time forward, so tests do not really wait."""

    def __init__(self) -> None:
        self.now = 1000.0
        self.sleeps: list[float] = []

    def clock(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


def make_pacer(tpm: int = 1000, rpm: int = 10) -> tuple[Pacer, FakeTime]:
    fake = FakeTime()
    pacer = Pacer({"m": ModelLimits(tpm, rpm)}, clock=fake.clock, sleep=fake.sleep)
    return pacer, fake


def test_t079a_calls_under_both_limits_do_not_wait() -> None:
    pacer, fake = make_pacer(tpm=1000, rpm=10)
    pacer.acquire("m", 400)
    pacer.acquire("m", 400)
    assert fake.sleeps == []


def test_t079a_the_token_limit_makes_the_call_wait_until_old_tokens_expire() -> None:
    pacer, fake = make_pacer(tpm=1000)
    pacer.acquire("m", 800)
    fake.now += 10
    pacer.acquire("m", 800)
    assert fake.sleeps == [50.0]


def test_t079a_the_request_limit_makes_the_call_wait_for_the_oldest_request() -> None:
    pacer, fake = make_pacer(tpm=100000, rpm=2)
    pacer.acquire("m", 1)
    fake.now += 20
    pacer.acquire("m", 1)
    pacer.acquire("m", 1)
    assert fake.sleeps == [40.0]


def test_t079a_actual_tokens_replace_the_estimate() -> None:
    pacer, fake = make_pacer(tpm=1000)
    first = pacer.acquire("m", 900)
    pacer.settle(first, 100)
    pacer.acquire("m", 800)
    assert fake.sleeps == []


def test_t079a_a_request_bigger_than_the_whole_limit_still_goes_through_alone() -> None:
    pacer, fake = make_pacer(tpm=1000)
    pacer.acquire("m", 5000)
    assert fake.sleeps == []


def test_t079a_a_model_with_no_limits_is_never_delayed() -> None:
    pacer, fake = make_pacer()
    for _ in range(50):
        pacer.acquire("other-model", 100000)
    assert fake.sleeps == []


def test_t079a_each_model_has_its_own_window() -> None:
    fake = FakeTime()
    limits = {"a": ModelLimits(1000, 10), "b": ModelLimits(1000, 10)}
    pacer = Pacer(limits, clock=fake.clock, sleep=fake.sleep)
    pacer.acquire("a", 1000)
    pacer.acquire("b", 1000)
    assert fake.sleeps == []


def test_t079a_the_paced_client_records_the_real_token_count() -> None:
    pacer, fake = make_pacer(tpm=1000)
    inner = FakeLLMClient(["one two three"])
    client = PacedClient(inner, pacer)
    request = LLMRequest(system="s", user="u", model="m", max_output_tokens=900)
    result = client.complete(request)
    assert result.text == "one two three"
    # The estimate was about 900; the real use was 5 tokens, so this fits without waiting.
    pacer.acquire("m", 900)
    assert fake.sleeps == []


def test_t079a_a_failed_call_still_counts_against_the_window() -> None:
    pacer, fake = make_pacer(tpm=1000)
    client = PacedClient(FakeLLMClient([RuntimeError("boom")]), pacer)
    request = LLMRequest(system="s", user="u", model="m", max_output_tokens=900)
    try:
        client.complete(request)
    except RuntimeError:
        pass
    pacer.acquire("m", 900)
    assert len(fake.sleeps) == 1
