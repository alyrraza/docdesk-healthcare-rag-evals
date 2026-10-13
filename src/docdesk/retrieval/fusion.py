"""Reciprocal rank fusion: merge ranked lists using ranks only (AC-RET-03)."""

from __future__ import annotations

import uuid
from dataclasses import replace

from docdesk.retrieval.types import ScoredChunk


def reciprocal_rank_fusion(lists: list[list[ScoredChunk]], rrf_k: int) -> list[ScoredChunk]:
    """Merge lists by summing 1 / (rrf_k + rank), since scores of different legs do not compare."""
    scores: dict[uuid.UUID, float] = {}
    first_seen: dict[uuid.UUID, ScoredChunk] = {}
    sources: dict[uuid.UUID, set[str]] = {}
    for ranked in lists:
        for rank, chunk in enumerate(ranked, start=1):
            scores[chunk.chunk_id] = scores.get(chunk.chunk_id, 0.0) + 1.0 / (rrf_k + rank)
            first_seen.setdefault(chunk.chunk_id, chunk)
            sources.setdefault(chunk.chunk_id, set()).add(chunk.source)
    # Sorting on (-score, id) makes equal scores come out in the same order every run.
    ordered = sorted(scores, key=lambda chunk_id: (-scores[chunk_id], chunk_id))
    return [
        replace(
            first_seen[chunk_id],
            score=scores[chunk_id],
            source="both" if len(sources[chunk_id]) > 1 else first_seen[chunk_id].source,
        )
        for chunk_id in ordered
    ]
