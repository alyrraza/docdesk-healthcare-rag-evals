"""The Groq adapter maps the common request to the chat completions API."""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest

from docdesk.llm.client import LLMRequest
from docdesk.llm.errors import LLMTimeoutError, ProviderError, RateLimitedError
from docdesk.llm.providers.groq import GroqClient

REQ = LLMRequest(
    system="rules", user="question", model="openai/gpt-oss-120b", max_output_tokens=300
)
KEY = "gsk_test_key_value"


def reply(content: str = '{"a": 1}', finish: str = "stop") -> dict[str, Any]:
    return {
        "choices": [{"message": {"content": content}, "finish_reason": finish}],
        "usage": {"prompt_tokens": 1000, "completion_tokens": 500},
    }


def client_for(handler: Any) -> GroqClient:
    return GroqClient(api_key=KEY, http=httpx.Client(transport=httpx.MockTransport(handler)))


def test_ac_gen_01_the_request_is_sent_with_the_bearer_key_and_the_common_fields() -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen["auth"] = request.headers["authorization"]
        seen["url"] = str(request.url)
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json=reply())

    client_for(handler).complete(REQ)
    assert seen["auth"] == f"Bearer {KEY}"
    assert seen["url"].endswith("/openai/v1/chat/completions")
    body = seen["body"]
    assert body["model"] == "openai/gpt-oss-120b"
    assert body["messages"][0] == {"role": "system", "content": "rules"}
    assert body["messages"][1] == {"role": "user", "content": "question"}
    assert body["temperature"] == 0.0
    assert body["max_completion_tokens"] == 300
    assert body["response_format"] == {"type": "json_object"}


def test_ac_gen_01_json_mode_off_sends_no_response_format() -> None:
    seen: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(json.loads(request.content))
        return httpx.Response(200, json=reply("plain"))

    client_for(handler).complete(LLMRequest(system="s", user="u", model="m", json_mode=False))
    assert "response_format" not in seen


def test_ac_obs_03_the_result_has_text_tokens_finish_reason_model_and_cost() -> None:
    result = client_for(lambda r: httpx.Response(200, json=reply())).complete(REQ)
    assert result.text == '{"a": 1}'
    assert (result.tokens_in, result.tokens_out) == (1000, 500)
    assert result.finish_reason == "stop"
    assert result.model == "openai/gpt-oss-120b"
    assert str(result.cost_usd) == "0.00045"
    assert result.latency_ms >= 0


def test_ac_gen_04_a_length_finish_reason_is_passed_through_for_truncation_checks() -> None:
    result = client_for(lambda r: httpx.Response(200, json=reply('{"a"', "length"))).complete(REQ)
    assert result.finish_reason == "length"


def test_ac_gen_04_a_429_becomes_a_rate_limit_error_with_the_retry_after_seconds() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(429, headers={"retry-after": "12"}, json={"error": {"message": "x"}})

    with pytest.raises(RateLimitedError) as caught:
        client_for(handler).complete(REQ)
    assert caught.value.retry_after == 12.0


def test_ac_gen_04_a_timeout_becomes_our_timeout_error() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow", request=request)

    with pytest.raises(LLMTimeoutError):
        client_for(handler).complete(REQ)


def test_ac_gen_04_other_http_errors_become_provider_errors_without_the_key() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": {"message": "invalid key " + KEY}})

    with pytest.raises(ProviderError) as caught:
        client_for(handler).complete(REQ)
    assert caught.value.status_code == 401
    assert KEY not in str(caught.value)


def test_ac_gen_04_an_answer_with_no_choices_is_a_provider_error() -> None:
    with pytest.raises(ProviderError):
        client_for(lambda r: httpx.Response(200, json={"choices": []})).complete(REQ)


def test_ac_gen_01_a_missing_key_is_refused_when_the_client_is_built() -> None:
    with pytest.raises(ValueError, match="GROQ_API_KEY"):
        GroqClient(api_key="", http=httpx.Client())
