"""A scripted LLM client, so no automated test ever calls a real provider."""

from __future__ import annotations

from decimal import Decimal

from docdesk.llm.client import LLMRequest, LLMResult


class FakeLLMClient:
    """Returns the scripted replies in order; an exception in the script is raised instead."""

    def __init__(
        self,
        replies: list[str | Exception],
        model: str = "fake-model",
        finish_reasons: list[str] | None = None,
    ) -> None:
        self.replies = list(replies)
        self.model = model
        self.finish_reasons = list(finish_reasons or [])
        self.requests: list[LLMRequest] = []

    def complete(self, request: LLMRequest) -> LLMResult:
        self.requests.append(request)
        if not self.replies:
            raise AssertionError("FakeLLMClient was called more often than the test scripted")
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return LLMResult(
            text=reply,
            tokens_in=len((request.system + " " + request.user).split()),
            tokens_out=len(reply.split()),
            latency_ms=1.0,
            finish_reason=self.finish_reasons.pop(0) if self.finish_reasons else "stop",
            model=self.model,
            cost_usd=Decimal("0"),
        )
