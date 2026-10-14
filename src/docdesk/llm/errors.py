"""Typed errors from a model call, each saying whether trying again could help."""

from __future__ import annotations


class LLMError(Exception):
    """Base class, so callers can catch every model failure with one type."""

    retryable: bool = False


class RateLimitedError(LLMError):
    """The provider said slow down; it may tell us how long to wait."""

    def __init__(
        self, message: str, retry_after: float | None = None, daily: bool = False
    ) -> None:
        super().__init__(message)
        self.retry_after = retry_after
        # A daily limit will not pass in seconds, so waiting is pointless: another key may serve.
        self.daily = daily

    @property
    def retryable(self) -> bool:  # type: ignore[override]
        """Retry a per minute limit; never a daily one."""
        return not self.daily


class LLMTimeoutError(LLMError):
    """The call took longer than the per-call timeout."""

    retryable = True


class ProviderError(LLMError):
    """Any other failure; a 5xx or a JSON mode failure may pass on its own, a 4xx usually never."""

    def __init__(
        self, message: str, status_code: int | None = None, code: str | None = None
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code

    @property
    def retryable(self) -> bool:  # type: ignore[override]
        """Retry server errors and the provider's occasional rejection of its own JSON output."""
        server_side = self.status_code is not None and self.status_code >= 500
        return server_side or self.code == "json_validate_failed"
