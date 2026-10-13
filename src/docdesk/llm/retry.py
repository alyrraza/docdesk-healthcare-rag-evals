"""Backoff around any client, with a hard cap on attempts and on any single wait."""

from __future__ import annotations

import time
from collections.abc import Callable

from docdesk.llm.client import LLMClient, LLMRequest, LLMResult
from docdesk.llm.errors import LLMError, RateLimitedError

# A provider can ask for minutes; a user request cannot wait that long.
MAX_WAIT_SECONDS = 30.0


class RetryingClient:
    """Wraps a client so a rate limit or timeout is retried a few times, then raised."""

    def __init__(
        self,
        inner: LLMClient,
        max_attempts: int = 3,
        base_delay: float = 1.0,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        """Take sleep as an argument so tests do not really wait."""
        self._inner = inner
        self._max_attempts = max_attempts
        self._base_delay = base_delay
        self._sleep = sleep

    def complete(self, request: LLMRequest) -> LLMResult:
        """Call the inner client; wait and retry only for errors that can pass on their own."""
        for attempt in range(1, self._max_attempts + 1):
            try:
                return self._inner.complete(request)
            except LLMError as error:
                if not error.retryable or attempt == self._max_attempts:
                    raise
                self._sleep(self._wait_for(error, attempt))
        raise AssertionError("unreachable: the loop returns or raises")

    def _wait_for(self, error: LLMError, attempt: int) -> float:
        """Use the provider's own wait when it gave one, else double the delay each attempt."""
        if isinstance(error, RateLimitedError) and error.retry_after is not None:
            return min(error.retry_after, MAX_WAIT_SECONDS)
        return min(self._base_delay * 2 ** (attempt - 1), MAX_WAIT_SECONDS)
