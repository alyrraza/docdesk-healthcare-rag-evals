"""The one interface every model provider implements, so no other code sees a vendor."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol


@dataclass(frozen=True)
class LLMRequest:
    """What we ask of a model; the adapter maps it to the provider's own format."""

    system: str
    user: str
    model: str
    temperature: float = 0.0
    max_output_tokens: int = 600
    # Ask the provider for a single JSON object; the schema is still checked in our code.
    json_mode: bool = True


@dataclass(frozen=True)
class LLMResult:
    """What came back, with everything the trace and the cost report need."""

    text: str
    tokens_in: int
    tokens_out: int
    latency_ms: float
    # "stop" for a normal end, "length" when the answer was cut off.
    finish_reason: str
    # The model that answered, logged with every result.
    model: str
    cost_usd: Decimal
    # True when the eval cache answered; tokens and latency are then the original call's.
    cache_hit: bool = False
    # Which key slot of a key pool served the call; None without a pool or on a cache hit.
    slot: int | None = None


class LLMClient(Protocol):
    """Anything that can complete a request; real adapters and the test fake both fit."""

    def complete(self, request: LLMRequest) -> LLMResult:
        """Send the request and return the result, or raise an LLMError."""
        ...
