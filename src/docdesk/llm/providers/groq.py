"""Groq adapter: maps the common request onto the OpenAI style chat completions API."""

from __future__ import annotations

import time
from typing import Any

import httpx

from docdesk.llm.client import LLMRequest, LLMResult
from docdesk.llm.cost import compute_cost
from docdesk.llm.errors import LLMTimeoutError, ProviderError, RateLimitedError

BASE_URL = "https://api.groq.com/openai/v1"
TIMEOUT_SECONDS = 60.0


class GroqClient:
    """Sends requests to Groq; the key lives only in this object and never in an error text."""

    def __init__(self, api_key: str, http: httpx.Client | None = None) -> None:
        """Refuse an empty key now, so a missing key fails at startup and not mid request."""
        if not api_key:
            raise ValueError("GROQ_API_KEY is not set, the Groq client cannot be built")
        self._api_key = api_key
        self._http = http or httpx.Client(timeout=TIMEOUT_SECONDS)

    def complete(self, request: LLMRequest) -> LLMResult:
        """Send one request and map every failure to one of our typed errors."""
        started = time.perf_counter()
        try:
            response = self._http.post(
                f"{BASE_URL}/chat/completions",
                headers={"Authorization": f"Bearer {self._api_key}"},
                json=self._body(request),
            )
        except httpx.TimeoutException as error:
            raise LLMTimeoutError(f"Groq call timed out after {TIMEOUT_SECONDS:.0f}s") from error
        except httpx.HTTPError as error:
            raise ProviderError(f"Groq call failed: {type(error).__name__}") from error
        latency_ms = (time.perf_counter() - started) * 1000.0
        self._raise_for_status(response)
        return self._result(request.model, response.json(), latency_ms)

    @staticmethod
    def _body(request: LLMRequest) -> dict[str, Any]:
        """Translate the common request into Groq's field names."""
        body: dict[str, Any] = {
            "model": request.model,
            "messages": [
                {"role": "system", "content": request.system},
                {"role": "user", "content": request.user},
            ],
            "temperature": request.temperature,
            "max_completion_tokens": request.max_output_tokens,
        }
        if request.json_mode:
            body["response_format"] = {"type": "json_object"}
        return body

    def _raise_for_status(self, response: httpx.Response) -> None:
        """Turn an error status into a typed error whose text never contains the key."""
        if response.status_code < 400:
            return
        if response.status_code == 429:
            raise RateLimitedError("Groq rate limit reached", _retry_after(response))
        raise ProviderError(
            f"Groq returned HTTP {response.status_code}{_error_code(response)}",
            status_code=response.status_code,
        )

    def _result(self, model: str, data: dict[str, Any], latency_ms: float) -> LLMResult:
        """Read text, finish reason and token counts out of a successful response."""
        choices = data.get("choices") or []
        if not choices:
            raise ProviderError("Groq returned no choices", status_code=200)
        usage = data.get("usage") or {}
        tokens_in = int(usage.get("prompt_tokens", 0))
        tokens_out = int(usage.get("completion_tokens", 0))
        return LLMResult(
            text=choices[0].get("message", {}).get("content") or "",
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            latency_ms=latency_ms,
            finish_reason=choices[0].get("finish_reason") or "unknown",
            model=model,
            cost_usd=compute_cost(model, tokens_in, tokens_out),
        )


def _retry_after(response: httpx.Response) -> float | None:
    """Read the Retry-After header as seconds, or None when it is missing or not a number."""
    try:
        return float(response.headers["retry-after"])
    except (KeyError, ValueError):
        return None


def _error_code(response: httpx.Response) -> str:
    """Name the provider's error code, never its message, which can echo the prompt."""
    try:
        code = response.json()["error"]["code"]
    except (ValueError, KeyError, TypeError):
        return ""
    return f" ({code})" if isinstance(code, str) else ""
