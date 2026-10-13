"""Backoff on rate limits and timeouts, with a hard cap on attempts."""

from __future__ import annotations

import pytest

from docdesk.llm.client import LLMRequest
from docdesk.llm.errors import LLMTimeoutError, ProviderError, RateLimitedError
from docdesk.llm.retry import RetryingClient
from fakes.llm import FakeLLMClient

REQ = LLMRequest(system="s", user="u", model="m")


def make(
    replies: list[str | Exception], attempts: int = 3
) -> tuple[RetryingClient, FakeLLMClient, list[float]]:
    inner = FakeLLMClient(replies)
    waits: list[float] = []
    client = RetryingClient(inner, max_attempts=attempts, base_delay=1.0, sleep=waits.append)
    return client, inner, waits


def test_ac_gen_04_a_success_needs_no_wait() -> None:
    client, inner, waits = make(["ok"])
    assert client.complete(REQ).text == "ok"
    assert waits == []
    assert len(inner.requests) == 1


def test_ac_gen_04_a_timeout_is_retried_with_doubling_waits() -> None:
    client, inner, waits = make([LLMTimeoutError("t"), LLMTimeoutError("t"), "ok"])
    assert client.complete(REQ).text == "ok"
    assert waits == [1.0, 2.0]
    assert len(inner.requests) == 3


def test_ac_gen_04_a_rate_limit_waits_as_long_as_the_provider_asked() -> None:
    client, _, waits = make([RateLimitedError("slow", retry_after=7.5), "ok"])
    client.complete(REQ)
    assert waits == [7.5]


def test_ac_gen_04_after_the_last_attempt_the_error_is_raised() -> None:
    client, inner, waits = make([LLMTimeoutError("t")] * 3, attempts=3)
    with pytest.raises(LLMTimeoutError):
        client.complete(REQ)
    assert len(inner.requests) == 3
    assert len(waits) == 2


def test_ac_gen_04_a_bad_request_is_not_retried() -> None:
    client, inner, waits = make([ProviderError("bad", status_code=400), "never used"])
    with pytest.raises(ProviderError):
        client.complete(REQ)
    assert len(inner.requests) == 1
    assert waits == []


def test_ac_gen_04_a_very_long_retry_after_is_capped() -> None:
    client, _, waits = make([RateLimitedError("slow", retry_after=3600.0), "ok"])
    client.complete(REQ)
    assert waits == [30.0]
