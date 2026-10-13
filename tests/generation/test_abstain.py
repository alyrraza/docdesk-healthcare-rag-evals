"""Abstaining on weak retrieval, before any model is called (AC-GEN-03)."""

from __future__ import annotations

import uuid

from docdesk.generation.abstain import AbstainPolicy, abstain_reason
from docdesk.retrieval.types import RetrievalResult, ScoredChunk


def result(score: float | None, config_id: str = "dense-n20-k5-rrf60") -> RetrievalResult:
    if score is None:
        return RetrievalResult([], config_id)
    chunk = ScoredChunk(uuid.UUID(int=1), uuid.UUID(int=2), "Doc", "text", score, "dense")
    return RetrievalResult([chunk], config_id)


def test_ac_gen_03_no_retrieved_chunks_means_no_evidence() -> None:
    assert abstain_reason(result(None), AbstainPolicy({}, default=0.2)) == "no_evidence"


def test_ac_gen_03_a_best_score_below_the_threshold_means_weak_evidence() -> None:
    assert abstain_reason(result(0.1), AbstainPolicy({}, default=0.2)) == "weak_evidence"


def test_ac_gen_03_a_best_score_at_or_above_the_threshold_does_not_abstain() -> None:
    assert abstain_reason(result(0.2), AbstainPolicy({}, default=0.2)) is None
    assert abstain_reason(result(0.9), AbstainPolicy({}, default=0.2)) is None


def test_ac_gen_03_the_threshold_is_looked_up_per_config_id() -> None:
    policy = AbstainPolicy({"dense-n20-k5-rrf60": 0.5}, default=0.0)
    assert abstain_reason(result(0.3), policy) == "weak_evidence"
    assert abstain_reason(result(0.3, "hybrid-n20-k5-rrf60"), policy) is None
