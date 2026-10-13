"""Typed errors from a model call, each saying whether trying again could help."""

from __future__ import annotations


class LLMError(Exception):
    """Base class, so callers can catch every model failure with one type."""

    retryable: bool = False


class RateLimitedError(LLMError):
    """The provider said slow down; it may tell us how long to wait."""

    retryable = True

    def __init__(self, message: str, retry_after: float | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


class LLMTimeoutError(LLMError):
    """The call took longer than the per-call timeout."""

    retryable = True


class ProviderError(LLMError):
    """Any other failure; a 5xx may pass on its own, a 4xx never will."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code

    @property
    def retryable(self) -> bool:  # type: ignore[override]
        """Retry only server side errors."""
        return self.status_code is not None and self.status_code >= 500
