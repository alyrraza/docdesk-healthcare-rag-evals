"""Small shared types for the ingestion pipeline."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Block:
    """A run of text and the page it came from, so chunks can cite a page later."""

    page: int
    text: str
