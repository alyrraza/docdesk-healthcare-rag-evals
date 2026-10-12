"""Time source in one place so tests can replace it."""

from __future__ import annotations

from datetime import UTC, datetime


def utc_now() -> datetime:
    """Return current UTC time through one function so tests can freeze it."""
    return datetime.now(UTC)
