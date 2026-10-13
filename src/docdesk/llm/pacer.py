"""Keeps model calls under the per minute limits by waiting, so a long eval run never gets a 429."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable
from dataclasses import dataclass

from docdesk.llm.client import LLMClient, LLMRequest, LLMResult

WINDOW_SECONDS = 60.0
# Rough size of a prompt: one token is about three characters, rounded on the safe side.
CHARS_PER_TOKEN = 3


@dataclass(frozen=True)
class ModelLimits:
    """The per minute limits of one model on one provider key."""

    tokens_per_minute: int
    requests_per_minute: int


# Groq free tier, measured 2026-10-13 and recorded in DECISIONS.md.
GROQ_FREE_LIMITS = ModelLimits(tokens_per_minute=8000, requests_per_minute=30)


@dataclass
class Reservation:
    """One call's place in the window; settled with the real token count after the call."""

    model: str
    started_at: float
    tokens: int


class Pacer:
    """Sliding one minute window per model; works inside one process only (see DECISIONS.md)."""

    def __init__(
        self,
        limits: dict[str, ModelLimits],
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        """Take clock and sleep as arguments so tests do not really wait."""
        self._limits = limits
        self._clock = clock
        self._sleep = sleep
        self._window: dict[str, list[Reservation]] = {}
        self._lock = threading.Lock()

    def acquire(self, model: str, estimated_tokens: int) -> Reservation:
        """Block until the call fits both limits, then reserve its place; never raises."""
        while True:
            with self._lock:
                now = self._clock()
                wait = self._wait_needed(model, estimated_tokens, now)
                if wait <= 0:
                    reservation = Reservation(model, now, estimated_tokens)
                    self._window.setdefault(model, []).append(reservation)
                    return reservation
            self._sleep(wait)

    def settle(self, reservation: Reservation, actual_tokens: int) -> None:
        """Replace the estimate with the real count, so a short answer frees its room."""
        with self._lock:
            reservation.tokens = actual_tokens

    def _wait_needed(self, model: str, tokens: int, now: float) -> float:
        """Seconds until the oldest entries leave the window far enough for this call."""
        limits = self._limits.get(model)
        if limits is None:
            return 0.0
        entries = [r for r in self._window.get(model, []) if now - r.started_at < WINDOW_SECONDS]
        self._window[model] = entries
        wait = 0.0
        if len(entries) >= limits.requests_per_minute:
            drop = len(entries) - limits.requests_per_minute + 1
            wait = entries[drop - 1].started_at + WINDOW_SECONDS - now
        used = sum(r.tokens for r in entries)
        for entry in entries:
            if used + tokens <= limits.tokens_per_minute:
                break
            used -= entry.tokens
            wait = max(wait, entry.started_at + WINDOW_SECONDS - now)
        return wait


class PacedClient:
    """Wraps any client so each call waits for its turn first."""

    def __init__(self, inner: LLMClient, pacer: Pacer) -> None:
        """Hold the client to wrap and the pacer shared by every client of the same key."""
        self._inner = inner
        self._pacer = pacer

    def complete(self, request: LLMRequest) -> LLMResult:
        """Wait for room, call, then record the real tokens; a failed call keeps its estimate."""
        prompt_chars = len(request.system) + len(request.user)
        estimate = prompt_chars // CHARS_PER_TOKEN + request.max_output_tokens
        reservation = self._pacer.acquire(request.model, estimate)
        result = self._inner.complete(request)
        self._pacer.settle(reservation, result.tokens_in + result.tokens_out)
        return result
