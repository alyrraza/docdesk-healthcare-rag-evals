"""Fits ranked evidence into the evidence budget, never cutting a chunk (AC-CTX-01, AC-CTX-02)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field

from docdesk.ingestion.types import TokenCounting
from docdesk.retrieval.types import ScoredChunk

# Allowance for the blank line between items, so the joined text stays inside the budget.
SEPARATOR_TOKENS = 2
DUPLICATE_OVERLAP = 0.8


@dataclass(frozen=True)
class PackedItem:
    """A chunk with the short label the model cites it by."""

    label: str
    chunk: ScoredChunk


@dataclass(frozen=True)
class Dropped:
    """A chunk that did not make it, and why, for the trace."""

    chunk_id: uuid.UUID
    reason: str


@dataclass
class Pack:
    """What goes into the prompt, plus the record of what was left out."""

    items: list[PackedItem] = field(default_factory=list)
    dropped: list[Dropped] = field(default_factory=list)
    evidence_text: str = ""
    tokens: int = 0

    @property
    def used_ids(self) -> list[uuid.UUID]:
        """Chunk ids in the prompt, in rank order."""
        return [item.chunk.chunk_id for item in self.items]

    @property
    def dropped_ids(self) -> list[uuid.UUID]:
        """Chunk ids left out, for AC-CTX-02."""
        return [d.chunk_id for d in self.dropped]

    def label_to_chunk_id(self) -> dict[str, uuid.UUID]:
        """Map the model's short labels back to real chunk ids."""
        return {item.label: item.chunk.chunk_id for item in self.items}


def word_overlap(a: str, b: str) -> float:
    """Share of the smaller text's words found in the other, to spot overlapping windows."""
    first, second = set(a.lower().split()), set(b.lower().split())
    if not first or not second:
        return 0.0
    return len(first & second) / min(len(first), len(second))


def format_item(label: str, chunk: ScoredChunk) -> str:
    """One evidence block as the model sees it."""
    return f"[{label}] {chunk.document_title}\n{chunk.text}"


def pack(
    chunks: list[ScoredChunk],
    budget_tokens: int,
    counter: TokenCounting,
    *,
    min_score: float | None = None,
    max_per_document: int = 2,
) -> Pack:
    """Walk the ranking once, filtering, then add items until the next one would not fit."""
    result = Pack()
    kept: list[ScoredChunk] = []
    per_document: dict[uuid.UUID, int] = {}
    full = False
    for chunk in chunks:
        reason = None
        if min_score is not None and chunk.score < min_score:
            reason = "below_threshold"
        elif any(
            k.document_id == chunk.document_id
            and word_overlap(k.text, chunk.text) >= DUPLICATE_OVERLAP
            for k in kept
        ):
            reason = "duplicate"
        elif per_document.get(chunk.document_id, 0) >= max_per_document:
            reason = "document_cap"
        elif full:
            reason = "budget"
        else:
            label = f"c{len(result.items) + 1}"
            cost = counter.count(format_item(label, chunk)) + SEPARATOR_TOKENS
            if result.tokens + cost > budget_tokens:
                # Everything ranked lower is dropped too, so kept items are always the best.
                full, reason = True, "budget"
            else:
                result.items.append(PackedItem(label, chunk))
                result.tokens += cost
                kept.append(chunk)
                per_document[chunk.document_id] = per_document.get(chunk.document_id, 0) + 1
        if reason:
            result.dropped.append(Dropped(chunk.chunk_id, reason))
    result.evidence_text = "\n\n".join(format_item(i.label, i.chunk) for i in result.items)
    return result
