"""Citation precision and recall against the gold evidence, with no LLM (T092).

`gold_sets` comes from the golden loader, which already applies the resolver rule: a chunk is gold
for a quote if it holds the whole quote or overlaps at least half of it by position.
"""

from __future__ import annotations

from collections.abc import Sequence, Set
from dataclasses import dataclass


@dataclass(frozen=True)
class CitationScores:
    """None means the score is undefined for this item, not zero."""

    precision: float | None
    recall: float | None


def citation_scores(cited_ids: Sequence[str], gold_sets: Sequence[Set[str]]) -> CitationScores:
    """Share of cited chunks that are gold, and share of evidence entries with a gold citation."""
    if not gold_sets:
        return CitationScores(None, None)
    cited = set(cited_ids)
    every_gold = set().union(*gold_sets)
    precision = len(cited & every_gold) / len(cited) if cited else None
    recall = sum(1 for gold in gold_sets if gold & cited) / len(gold_sets)
    return CitationScores(precision, recall)
