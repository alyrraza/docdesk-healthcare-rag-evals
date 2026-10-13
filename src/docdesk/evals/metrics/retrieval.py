"""Retrieval metrics without any LLM call (AC-EVL-02).

`gold_sets` has one set of gold chunk ids per evidence entry of the item. An item with no
entries (unanswerable) has no retrieval score, so every function returns None for it.
"""

from __future__ import annotations

from collections.abc import Sequence, Set


def top_k(retrieved: Sequence[str], k: int) -> Sequence[str]:
    """Cut the ranked ids at k, refusing a k that would silently mean nothing."""
    if k < 1:
        raise ValueError(f"k must be at least 1, got {k}")
    return retrieved[:k]


def recall_at_k(retrieved: Sequence[str], gold_sets: Sequence[Set[str]], k: int) -> float | None:
    """Share of evidence entries that have a gold chunk in the top k; all are required."""
    cut = set(top_k(retrieved, k))
    if not gold_sets:
        return None
    return sum(1 for gold in gold_sets if gold & cut) / len(gold_sets)


def hit_at_k(retrieved: Sequence[str], gold_sets: Sequence[Set[str]], k: int) -> float | None:
    """1.0 when any evidence entry has a gold chunk in the top k, else 0.0."""
    cut = set(top_k(retrieved, k))
    if not gold_sets:
        return None
    return 1.0 if any(gold & cut for gold in gold_sets) else 0.0


def reciprocal_rank(
    retrieved: Sequence[str], gold_sets: Sequence[Set[str]], k: int | None = None
) -> float | None:
    """1 / rank of the first chunk that is gold for any entry, or 0.0 if none within k."""
    if not gold_sets:
        return None
    ranked = retrieved if k is None else top_k(retrieved, k)
    every_gold = set().union(*gold_sets)
    for rank, chunk_id in enumerate(ranked, start=1):
        if chunk_id in every_gold:
            return 1.0 / rank
    return 0.0


def context_precision_at_k(
    retrieved: Sequence[str], gold_sets: Sequence[Set[str]], k: int
) -> float | None:
    """Share of the returned top k that is gold for some entry; 0.0 for an empty result."""
    cut = top_k(retrieved, k)
    if not gold_sets:
        return None
    if not cut:
        return 0.0
    every_gold = set().union(*gold_sets)
    return sum(1 for chunk_id in cut if chunk_id in every_gold) / len(cut)
