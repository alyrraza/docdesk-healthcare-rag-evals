"""Errors the pipeline turns into a `failed` document with a readable reason (AC-ING-03)."""

from __future__ import annotations


class ParseError(Exception):
    """A file could not be turned into text; the message is shown to the user as the reason."""

    def __init__(self, reason: str) -> None:
        """Keep the reason as an attribute so the pipeline can store it without parsing a string."""
        super().__init__(reason)
        self.reason = reason
