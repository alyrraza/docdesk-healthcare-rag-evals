"""Parent-child chunker: match on small children, hand the model the larger parent."""

from __future__ import annotations

from dataclasses import replace

from docdesk.ingestion.chunkers import fixed, recursive
from docdesk.ingestion.chunkers.packing import check_limits
from docdesk.ingestion.types import Block, Chunk, TokenCounting

VERSION = "parent-child-v1"
# A parent holds about this many children, so the model gets context around the matched passage.
PARENT_FACTOR = 4


def chunk(blocks: list[Block], size: int, overlap: int, counter: TokenCounting) -> list[Chunk]:
    """Cut pages into parents, then cut each parent into children of at most `size` tokens."""
    check_limits(size, overlap)
    parents = recursive.chunk(blocks, PARENT_FACTOR * size, 0, counter)
    chunks: list[Chunk] = []
    for parent in parents:
        children = fixed.chunk([Block(parent.page, parent.text)], size, overlap, counter)
        for child in children:
            chunks.append(
                replace(
                    child, position=len(chunks), chunker_version=VERSION, parent_text=parent.text
                )
            )
    return chunks
