"""Reciprocal rank fusion (AC-RET-03): pure, rank based, deterministic."""

from __future__ import annotations

import random
import uuid

from docdesk.retrieval.fusion import reciprocal_rank_fusion
from docdesk.retrieval.types import ScoredChunk

IDS = [uuid.UUID(int=i) for i in range(1, 8)]


def hit(chunk_id: uuid.UUID, source: str) -> ScoredChunk:
    return ScoredChunk(chunk_id, uuid.UUID(int=0), "Doc", "text", 0.5, source, None)


def test_ac_ret_03_scores_are_hand_computed_sums_of_one_over_k_plus_rank() -> None:
    dense = [hit(IDS[0], "dense"), hit(IDS[1], "dense")]
    keyword = [hit(IDS[1], "keyword"), hit(IDS[2], "keyword")]
    fused = reciprocal_rank_fusion([dense, keyword], rrf_k=60)
    scores = {h.chunk_id: h.score for h in fused}
    assert scores[IDS[0]] == 1 / 61
    assert scores[IDS[1]] == 1 / 62 + 1 / 61
    assert scores[IDS[2]] == 1 / 62
    assert [h.chunk_id for h in fused] == [IDS[1], IDS[0], IDS[2]]


def test_ac_ret_03_a_chunk_found_by_both_legs_is_marked_both() -> None:
    fused = reciprocal_rank_fusion([[hit(IDS[0], "dense")], [hit(IDS[0], "keyword")]], rrf_k=60)
    assert fused[0].source == "both"


def test_ac_ret_03_ties_break_on_chunk_id() -> None:
    # Each chunk tops one list, so the scores are equal and the smaller id must come first.
    fused = reciprocal_rank_fusion([[hit(IDS[3], "dense")], [hit(IDS[1], "keyword")]], rrf_k=60)
    assert [h.chunk_id for h in fused] == [IDS[1], IDS[3]]


def test_ac_ret_03_empty_lists_fuse_to_an_empty_list() -> None:
    assert reciprocal_rank_fusion([[], []], rrf_k=60) == []


def test_ac_ret_03_output_is_a_sorted_permutation_of_the_union_of_the_inputs() -> None:
    rng = random.Random(7)
    for _ in range(200):
        first = rng.sample(IDS, rng.randint(0, len(IDS)))
        second = rng.sample(IDS, rng.randint(0, len(IDS)))
        fused = reciprocal_rank_fusion(
            [[hit(i, "dense") for i in first], [hit(i, "keyword") for i in second]], rrf_k=60
        )
        assert sorted(h.chunk_id for h in fused) == sorted(set(first) | set(second))
        scores = [h.score for h in fused]
        assert scores == sorted(scores, reverse=True)
