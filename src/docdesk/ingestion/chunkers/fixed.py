"""Fixed size chunker: pack whole sentences up to a token budget, with sentence overlap."""

from __future__ import annotations

from docdesk.ingestion.chunkers.packing import check_limits, cut_long_text, pack
from docdesk.ingestion.sentences import split_sentences
from docdesk.ingestion.types import Block, Chunk, TokenCounting

VERSION = "fixed-v1"


def sentence_units(text: str, size: int, counter: TokenCounting) -> list[str]:
    """List the sentences of a page, cutting any single sentence that alone exceeds the limit."""
    units: list[str] = []
    for sentence in split_sentences(text):
        if counter.count(sentence) > size:
            units.extend(cut_long_text(sentence, size, counter))
        else:
            units.append(sentence)
    return units


def chunk(blocks: list[Block], size: int, overlap: int, counter: TokenCounting) -> list[Chunk]:
    """Split each page into chunks of at most `size` tokens, never mixing two pages."""
    check_limits(size, overlap)
    chunks: list[Chunk] = []
    for block in blocks:
        for text in pack(sentence_units(block.text, size, counter), size, overlap, counter):
            chunks.append(Chunk(len(chunks), block.page, text, counter.count(text), VERSION))
    return chunks
