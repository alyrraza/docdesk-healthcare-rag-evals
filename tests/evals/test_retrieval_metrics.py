"""AC-EVL-02: retrieval metrics are pure functions, checked here against hand computed answers."""

from __future__ import annotations

import pytest

from docdesk.evals.metrics.retrieval import (
    context_precision_at_k,
    hit_at_k,
    recall_at_k,
    reciprocal_rank,
)

RETRIEVED = ["a", "b", "c", "d", "e"]
# Two evidence entries: the first is satisfied by "b" (rank 2), the second by "e" (rank 5) or "z".
GOLD = [frozenset({"b"}), frozenset({"e", "z"})]


def test_ac_evl_02_recall_is_the_share_of_evidence_entries_with_a_gold_chunk_in_the_top_k() -> None:
    assert recall_at_k(RETRIEVED, GOLD, 1) == 0.0
    assert recall_at_k(RETRIEVED, GOLD, 3) == 0.5
    assert recall_at_k(RETRIEVED, GOLD, 5) == 1.0


def test_ac_evl_02_one_chunk_can_satisfy_two_entries() -> None:
    assert recall_at_k(["x"], [frozenset({"x"}), frozenset({"x", "y"})], 1) == 1.0


def test_ac_evl_02_hit_rate_needs_only_one_entry_to_be_satisfied() -> None:
    assert hit_at_k(RETRIEVED, GOLD, 1) == 0.0
    assert hit_at_k(RETRIEVED, GOLD, 2) == 1.0


def test_ac_evl_02_reciprocal_rank_uses_the_first_gold_chunk_for_any_entry() -> None:
    assert reciprocal_rank(RETRIEVED, GOLD) == 0.5
    assert reciprocal_rank(["e", "b"], GOLD) == 1.0


def test_ac_evl_02_reciprocal_rank_is_zero_when_no_gold_chunk_is_in_the_cutoff() -> None:
    assert reciprocal_rank(RETRIEVED, GOLD, k=1) == 0.0
    assert reciprocal_rank(["p", "q"], GOLD) == 0.0


def test_ac_evl_02_context_precision_is_the_share_of_the_top_k_that_is_gold() -> None:
    assert context_precision_at_k(RETRIEVED, GOLD, 5) == pytest.approx(0.4)
    assert context_precision_at_k(RETRIEVED, GOLD, 2) == 0.5


def test_ac_evl_02_a_short_result_list_divides_by_what_was_returned() -> None:
    assert context_precision_at_k(["b"], GOLD, 5) == 1.0
    assert context_precision_at_k([], GOLD, 5) == 0.0
    assert recall_at_k([], GOLD, 5) == 0.0


def test_ac_evl_02_an_item_without_gold_evidence_has_no_retrieval_score() -> None:
    for metric in (recall_at_k, hit_at_k, context_precision_at_k):
        assert metric(RETRIEVED, [], 5) is None
    assert reciprocal_rank(RETRIEVED, []) is None


def test_ac_evl_02_an_entry_with_no_gold_chunk_can_never_be_satisfied() -> None:
    assert recall_at_k(RETRIEVED, [frozenset({"b"}), frozenset()], 5) == 0.5


def test_ac_evl_02_k_must_be_at_least_one() -> None:
    with pytest.raises(ValueError, match="k must be"):
        recall_at_k(RETRIEVED, GOLD, 0)
