"""The common LLM interface and the fake that stands in for a provider in tests."""

from __future__ import annotations

import dataclasses

import pytest

from docdesk.llm.client import LLMClient, LLMRequest
from docdesk.llm.errors import LLMTimeoutError, ProviderError, RateLimitedError
from fakes.llm import FakeLLMClient


def request() -> LLMRequest:
    return LLMRequest(system="rules", user="question", model="m")


def test_ac_obs_03_the_fake_returns_scripted_replies_in_order_and_records_requests() -> None:
    fake = FakeLLMClient(["one", "two"])
    client: LLMClient = fake
    assert client.complete(request()).text == "one"
    assert client.complete(request()).text == "two"
    assert len(fake.requests) == 2


def test_ac_obs_03_a_result_carries_tokens_latency_finish_reason_model_and_cost() -> None:
    result = FakeLLMClient(["a b c"]).complete(request())
    assert (result.tokens_out, result.finish_reason, result.model) == (3, "stop", "fake-model")
    assert result.latency_ms >= 0
    assert result.cost_usd == 0


def test_ac_obs_03_a_scripted_error_is_raised() -> None:
    with pytest.raises(LLMTimeoutError):
        FakeLLMClient([LLMTimeoutError("slow")]).complete(request())


def test_ac_obs_03_calling_the_fake_more_than_scripted_fails_loudly() -> None:
    with pytest.raises(AssertionError):
        FakeLLMClient([]).complete(request())


def test_ac_obs_03_a_request_is_immutable_with_safe_defaults() -> None:
    req = request()
    assert (req.temperature, req.json_mode) == (0.0, True)
    with pytest.raises(dataclasses.FrozenInstanceError):
        req.user = "changed"  # type: ignore[misc]


def test_ac_obs_03_error_types_say_whether_a_retry_can_help() -> None:
    assert RateLimitedError("slow down", retry_after=2.0).retryable
    assert LLMTimeoutError("t").retryable
    assert ProviderError("server", status_code=503).retryable
    assert not ProviderError("bad request", status_code=400).retryable


def test_ac_obs_03_a_provider_error_keeps_its_code_and_a_json_failure_is_retryable() -> None:
    error = ProviderError("bad json", status_code=400, code="json_validate_failed")
    assert error.code == "json_validate_failed" and error.retryable
    assert not ProviderError("other", status_code=400, code="invalid_api_key").retryable
