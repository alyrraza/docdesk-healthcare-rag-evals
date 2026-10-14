"""T100 (AC-EVL-07): joining stored judge labels to the reference labels on run, item and hash."""

from __future__ import annotations

from typing import Any

import pytest

from docdesk.evals.calib_join import JoinError, join_natural, join_synthetic
from docdesk.evals.calib_sample import answer_hash
from docdesk.evals.report_data import ResultRecord

RUN = "run-1"
ANSWER = "The tablets are 25 mg."


def record(item_id: str = "gi-001", answer: str = ANSWER, **over: Any) -> ResultRecord:
    metrics = {"faithfulness": 1.0, "faithfulness_status": "scored",
               "correctness": 0.5, "correctness_status": "scored"}
    trace = {"answer": answer,
             "faithfulness_labels": [{"claim": "25 mg", "label": "supported", "evidence_id": "c1"}],
             "correctness_labels": [{"point": 2, "label": "missing"},
                                    {"point": 1, "label": "covered"}]}
    metrics.update(over.pop("metrics", {}))
    trace.update(over.pop("trace", {}))
    return ResultRecord(item_id, metrics, None, trace)


def manifest(**over: Any) -> dict:
    entry = {"n": 1, "run_id": RUN, "item_id": "gi-001", "answer_hash": answer_hash(ANSWER),
             "key_points": 2}
    return {"outputs": [{**entry, **over}]}


def labels(**over: Any) -> dict:
    entry = {"n": 1, "run_id": RUN, "item_id": "gi-001", "answer_hash": answer_hash(ANSWER),
             "key_points": ["covered", "missing"], "unsupported_claims": [], "contradicted": False}
    return {"labels": [{**entry, **over}]}


FACTS = {"gi-001": ["Tablets come in 25 mg", "Take with food"]}


def natural(records=None, man=None, lab=None, borderline=frozenset()):
    rows = {RUN: records if records is not None else [record()]}
    return join_natural(man or manifest(), lab or labels(), rows, FACTS, borderline)


def test_ac_evl_07_join_01_a_natural_output_gets_both_sides_and_its_key_point_texts() -> None:
    (out,) = natural(borderline=frozenset({1}))
    assert out.set_name == "natural" and out.output_id == "1" and out.borderline
    assert out.key_points == FACTS["gi-001"]
    assert out.ref_keys == ["covered", "missing"] and out.ref_claims == []
    assert out.judge.key_labels == ["covered", "missing"]  # sorted by point, not stored order
    assert out.judge.faith_score == 1.0 and out.judge.claims == [("25 mg", "supported")]


def test_ac_evl_07_join_02_a_changed_answer_stops_the_join() -> None:
    with pytest.raises(JoinError, match="gi-001.*hash"):
        natural(records=[record(answer="A different answer.")])


def test_ac_evl_07_join_03_a_missing_run_row_stops_the_join() -> None:
    with pytest.raises(JoinError, match="gi-001.*no stored row"):
        natural(records=[record("gi-099")])


def test_ac_evl_07_join_04_missing_judge_labels_stop_the_join() -> None:
    bad = record(metrics={"correctness_status": "parse_failed"}, trace={"correctness_labels": []})
    with pytest.raises(JoinError, match="correctness.*parse_failed"):
        natural(records=[bad])
    bad = record(metrics={"faithfulness_status": "RateLimitError", "faithfulness": None})
    with pytest.raises(JoinError, match="faithfulness.*RateLimitError"):
        natural(records=[bad])


def test_ac_evl_07_join_05_labels_that_do_not_match_the_manifest_stop_the_join() -> None:
    with pytest.raises(JoinError, match="answer_hash"):
        natural(lab=labels(answer_hash="0" * 64))
    with pytest.raises(JoinError, match="2 key points"):
        natural(lab=labels(key_points=["covered"]))


def test_ac_evl_07_join_06_zero_claims_is_kept_with_no_score() -> None:
    quiet = record(metrics={"faithfulness": None, "faithfulness_status": "no_claims"},
                   trace={"faithfulness_labels": []})
    (out,) = natural(records=[quiet])
    assert out.judge.faith_score is None and out.judge.faith_status == "no_claims"


def synthetic_manifest(**over: Any) -> dict:
    entry = {"n": 1, "synthetic_id": "syn-01", "parent_item_id": "gi-001",
             "parent_run_id": RUN, "answer": "Tablets are 25 mg. Extra claim.",
             "answer_hash": answer_hash("Tablets are 25 mg. Extra claim."), "key_points": 2}
    return {"outputs": [{**entry, **over}]}


def synthetic_labels(**over: Any) -> dict:
    return {"labels": [{"synthetic_id": "syn-01", **labels(**over)["labels"][0],
                        "answer_hash": answer_hash("Tablets are 25 mg. Extra claim."),
                        "unsupported_claims": ["Extra claim"]}]}


def judged(**over: Any) -> dict:
    entry = {"synthetic_id": "syn-01", "n": 1, "parent_item_id": "gi-001",
             "answer_hash": answer_hash("Tablets are 25 mg. Extra claim."),
             "faithfulness": {"status": "scored", "score": 0.5, "claims": [
                 {"claim": "25 mg", "label": "supported", "evidence_id": "c1"},
                 {"claim": "Extra claim", "label": "unsupported", "evidence_id": None}]},
             "correctness": {"status": "scored", "score": 0.5, "key_points": [
                 {"point": 1, "label": "covered"}, {"point": 2, "label": "missing"}]}}
    return {"results": [{**entry, **over}]}


def test_ac_evl_07_join_07_a_synthetic_output_is_joined_by_its_id_and_hash() -> None:
    (out,) = join_synthetic(synthetic_manifest(), synthetic_labels(), judged(), FACTS, frozenset())
    assert out.set_name == "synthetic" and out.output_id == "syn-01"
    assert out.ref_claims == ["Extra claim"]
    assert out.judge.claims[1] == ("Extra claim", "unsupported") and out.judge.faith_score == 0.5


def test_ac_evl_07_join_08_a_synthetic_result_for_another_text_stops_the_join() -> None:
    with pytest.raises(JoinError, match="syn-01.*hash"):
        join_synthetic(synthetic_manifest(), synthetic_labels(),
                       judged(answer_hash="1" * 64), FACTS, frozenset())
    with pytest.raises(JoinError, match="syn-01.*no judge result"):
        join_synthetic(synthetic_manifest(), synthetic_labels(), {"results": []}, FACTS,
                       frozenset())
