"""Drop chunks that hold no evidence, so they do not take a rank slot (Phase 5, E4)."""

from __future__ import annotations

import re

from docdesk.retrieval.types import ScoredChunk

TITLE_SUFFIX = "drug label"
# A title chunk is short. A long chunk that happens to end with the words is real text.
MAX_TITLE_WORDS = 8


def normalized(text: str) -> str:
    """Lowercase words only, so case, spacing and punctuation do not hide a title chunk."""
    return " ".join(re.findall(r"[a-z0-9]+", text.lower()))


def is_title_only(chunk: ScoredChunk) -> bool:
    """Why: a chunk whose whole text is the document title matches the query on the drug name
    alone and carries no fact, yet it can outrank the chunk that holds the answer."""
    text = normalized(chunk.text)
    if not text:
        return False
    if text == normalized(chunk.document_title):
        return True
    return text.endswith(TITLE_SUFFIX) and len(text.split()) <= MAX_TITLE_WORDS


def drop_title_only(chunks: list[ScoredChunk]) -> list[ScoredChunk]:
    """Keep the order of every chunk that is not title only."""
    return [chunk for chunk in chunks if not is_title_only(chunk)]
