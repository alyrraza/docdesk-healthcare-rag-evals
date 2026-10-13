"""Recursive chunker: keep paragraphs whole when they fit, then sentences, then words."""

from __future__ import annotations

from collections.abc import Callable

from docdesk.ingestion.chunkers.packing import check_limits, cut_long_text, pack
from docdesk.ingestion.sentences import PARAGRAPH_BREAK, split_sentences
from docdesk.ingestion.types import Block, Chunk, TokenCounting

VERSION = "recursive-v1"


def split_paragraphs(text: str) -> list[str]:
    """Split on blank lines, the coarsest boundary a document has."""
    return [part.strip() for part in PARAGRAPH_BREAK.split(text) if part.strip()]


# (how to split, what to join the pieces back with), coarsest first.
LEVELS: tuple[tuple[Callable[[str], list[str]], str], ...] = (
    (split_paragraphs, "\n\n"),
    (split_sentences, " "),
    (str.split, " "),
)


def split_to_fit(
    text: str,
    size: int,
    overlap: int,
    counter: TokenCounting,
    levels: tuple[tuple[Callable[[str], list[str]], str], ...] = LEVELS,
) -> list[str]:
    """Return pieces of at most `size` tokens, splitting at the coarsest boundary that works."""
    if counter.count(text) <= size:
        return [text]
    if not levels:
        return cut_long_text(text, size, counter)
    splitter, joiner = levels[0]
    parts = splitter(text)
    if len(parts) <= 1:
        return split_to_fit(text, size, overlap, counter, levels[1:])
    pieces: list[str] = []
    small: list[str] = []
    for part in parts:
        if counter.count(part) <= size:
            small.append(part)
            continue
        pieces.extend(pack(small, size, overlap, counter, joiner))
        small = []
        pieces.extend(split_to_fit(part, size, overlap, counter, levels[1:]))
    pieces.extend(pack(small, size, overlap, counter, joiner))
    return pieces


def chunk(blocks: list[Block], size: int, overlap: int, counter: TokenCounting) -> list[Chunk]:
    """Split each page into chunks of at most `size` tokens, never mixing two pages."""
    check_limits(size, overlap)
    chunks: list[Chunk] = []
    for block in blocks:
        for text in split_to_fit(block.text, size, overlap, counter):
            if text.strip():
                chunks.append(Chunk(len(chunks), block.page, text, counter.count(text), VERSION))
    return chunks
