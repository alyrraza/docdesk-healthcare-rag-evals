"""Small shared types for the ingestion pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class Block:
    """A run of text and the page it came from, so chunks can cite a page later."""

    page: int
    text: str


class TokenCounting(Protocol):
    """Anything that can count tokens, so chunkers can use a fake counter in tests."""

    def count(self, text: str) -> int:
        """Return the number of tokens in the text."""
        ...


@dataclass(frozen=True)
class Chunk:
    """One retrievable piece of text with everything AC-ING-05 says must be stored."""

    position: int
    page: int
    text: str
    token_count: int
    chunker_version: str
    # Only the parent-child chunker fills this: the larger text to hand to the model.
    parent_text: str | None = None
