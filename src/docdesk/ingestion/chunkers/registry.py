"""Looks up a chunking strategy by the name used in configuration and experiments."""

from __future__ import annotations

from collections.abc import Callable

from docdesk.ingestion.chunkers import fixed, recursive
from docdesk.ingestion.types import Block, Chunk, TokenCounting

Chunker = Callable[[list[Block], int, int, TokenCounting], list[Chunk]]

CHUNKERS: dict[str, Chunker] = {
    "fixed": fixed.chunk,
    "recursive": recursive.chunk,
}


def get_chunker(name: str) -> Chunker:
    """Return the chunk function for a name, so a typo in config fails with the valid choices."""
    if name not in CHUNKERS:
        raise ValueError(f"unknown chunker '{name}', choose one of: {', '.join(sorted(CHUNKERS))}")
    return CHUNKERS[name]
