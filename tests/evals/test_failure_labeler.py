"""T093 (AC-EVL-03): one deterministic failure label per failed item, first match wins."""

from __future__ import annotations

import re
from dataclasses import replace
from pathlib import Path

from docdesk.evals.labeler import LABEL_ORDER, LabelInput, label_failure

ROOT = Path(__file__).resolve().parents[2]
GOOD = LabelInput(
    behavior="answer",
    outcome="answered",
    retrieval_ran=True,
    packed=True,
    gold_sets=[frozenset({"g1"}), frozenset({"g2"})],
    candidate_ids=["g1", "g2", "x", "y"],
    retrieved_ids=["g1", "g2", "x"],
    used_ids=["g1", "g2", "x"],
    faithfulness=1.0,
    correctness=1.0,
)


def labeled(**changes) -> str | None:
    return label_failure(replace(GOOD, **changes))


def test_ac_evl_03_label_01_a_passing_item_has_no_label() -> None:
    assert labeled() is None
    assert labeled(behavior="abstain", outcome="abstained", gold_sets=[]) is None
    assert labeled(behavior="refuse", outcome="refused", retrieval_ran=False) is None
    assert labeled(faithfulness=1.0, correctness=1.0, contradicted=0) is None


def test_ac_evl_03_label_01b_an_answer_with_missing_judge_scores_is_not_a_pass() -> None:
    # F1 of the phase 4 review: the old test here let a judge failure count as a pass.
    assert labeled(faithfulness=None, correctness=None) == "other"
    assert labeled(faithfulness=None, correctness=None, judge_failed=True) == "judge_failure"


def test_ac_evl_03_label_02_retrieval_miss_gold_not_among_the_candidates() -> None:
    assert labeled(candidate_ids=["g1", "x"], retrieved_ids=["g1", "x"],
                   outcome="abstained") == "retrieval_miss"


def test_ac_evl_03_label_03_ranking_miss_gold_is_a_candidate_but_not_in_top_k() -> None:
    assert labeled(retrieved_ids=["g1", "x"], used_ids=["g1", "x"],
                   outcome="abstained") == "ranking_miss"


def test_ac_evl_03_label_04_context_overflow_gold_retrieved_but_not_packed() -> None:
    assert labeled(used_ids=["g1", "x"], outcome="abstained") == "context_overflow"


def test_ac_evl_03_label_05_context_overflow_needs_the_packer_to_have_run() -> None:
    # An abstain before packing (weak evidence) is not the packer's fault.
    assert labeled(packed=False, used_ids=[], outcome="abstained") == "wrong_abstain"


def test_ac_evl_03_label_06_context_distraction_gold_in_prompt_but_not_first() -> None:
    assert labeled(used_ids=["x", "g1", "g2"], outcome="abstained") == "context_distraction"
    assert labeled(used_ids=["x", "g1", "g2"], correctness=0.5) == "context_distraction"


def test_ac_evl_03_label_07_wrong_abstain() -> None:
    assert labeled(outcome="abstained") == "wrong_abstain"


def test_ac_evl_03_label_08_missed_abstain() -> None:
    assert labeled(behavior="abstain", outcome="answered", gold_sets=[]) == "missed_abstain"


def test_ac_evl_03_label_09_wrong_refusal_even_without_retrieval() -> None:
    assert labeled(outcome="refused", retrieval_ran=False, packed=False,
                   candidate_ids=[], retrieved_ids=[], used_ids=[]) == "wrong_refusal"


def test_ac_evl_03_label_10_missed_refusal() -> None:
    assert labeled(behavior="refuse", outcome="answered", gold_sets=[]) == "missed_refusal"
    assert labeled(behavior="refuse", outcome="abstained", gold_sets=[]) == "missed_refusal"


def test_ac_evl_03_label_11_unfaithful_before_incorrect() -> None:
    assert labeled(faithfulness=0.5) == "unfaithful"
    assert labeled(faithfulness=0.5, correctness=0.0) == "unfaithful"


def test_ac_evl_03_label_12_incorrect() -> None:
    assert labeled(correctness=0.5) == "incorrect"
    assert labeled(correctness=1.0, contradicted=1) == "incorrect"


def test_ac_evl_03_label_13_a_system_error_is_other_not_a_retrieval_label() -> None:
    assert labeled(outcome="error", candidate_ids=[], retrieved_ids=[]) == "other"


def test_ac_evl_03_label_14_a_correct_answer_with_imperfect_retrieval_still_passes() -> None:
    assert labeled(retrieved_ids=["g1", "x"], used_ids=["g1", "x"]) is None


def test_ac_evl_03_order_01_the_first_matching_label_wins() -> None:
    everything_wrong = replace(
        GOOD, outcome="answered", candidate_ids=["x"], retrieved_ids=["x"], used_ids=["x"],
        faithfulness=0.0, correctness=0.0,
    )
    assert label_failure(everything_wrong) == "retrieval_miss"
    ranking = replace(everything_wrong, candidate_ids=["g1", "g2", "x"])
    assert label_failure(ranking) == "ranking_miss"
    overflow = replace(ranking, retrieved_ids=["g1", "g2", "x"])
    assert label_failure(overflow) == "context_overflow"
    distraction = replace(overflow, used_ids=["x", "g1", "g2"])
    assert label_failure(distraction) == "context_distraction"
    clean_prompt = replace(distraction, used_ids=["g1", "g2", "x"])
    assert label_failure(clean_prompt) == "unfaithful"
    assert label_failure(replace(clean_prompt, faithfulness=1.0)) == "incorrect"


def test_ac_evl_03_order_02_the_order_is_the_documented_one() -> None:
    assert LABEL_ORDER == (
        "retrieval_miss", "ranking_miss", "context_overflow", "context_distraction",
        "wrong_abstain", "missed_abstain", "wrong_refusal", "missed_refusal",
        "judge_failure", "unfaithful", "incorrect", "other",
    )
    text = (ROOT / "docs" / "modules" / "evals.md").read_text(encoding="utf-8")
    section = text.split("### First match order", 1)[1].split("\n\n", 1)[0]
    assert tuple(re.findall(r"`(\w+)`", section)) == LABEL_ORDER
