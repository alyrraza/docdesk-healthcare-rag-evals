"""T100 (AC-EVL-07): the measures on five hand-made outputs whose tables are counted by hand."""

from __future__ import annotations

import pytest

from docdesk.evals.calib_join import JudgedOutput, JudgeSide
from docdesk.evals.calib_measures import disagreements, evaluate, measure
from docdesk.evals.calib_stats import SINGLE_CLASS


def out(name: str, ref_keys, judge_keys, *, ref_claims=(), contradicted=False, score=1.0,
        claims=(), borderline=False) -> JudgedOutput:
    side = JudgeSide("scored" if score is not None else "no_claims", score, list(claims),
                     list(judge_keys))
    texts = [f"point {k}" for k in range(1, len(ref_keys) + 1)]
    return JudgedOutput("natural", 1, name, "gi-001", borderline, texts, list(ref_keys),
                        list(ref_claims), contradicted, side)


def five() -> list[JudgedOutput]:
    return [
        out("A", ["covered", "covered"], ["covered", "missing"]),
        out("B", ["covered"], ["covered"], ref_claims=["bad dose"], score=0.5,
            claims=[("bad dose", "unsupported")]),
        out("C", ["missing"], ["missing"], ref_claims=["bad dose"], score=1.0),
        out("D", ["covered"], ["covered"], score=0.5, claims=[("fine claim", "unsupported")],
            borderline=True),
        out("E", ["covered"], ["covered"], score=None),
    ]


def test_ac_evl_07_measures_01_faithfulness_item_table_and_detection_counts() -> None:
    result = evaluate(five(), resamples=50, seed=0)
    item = result.measures["faithfulness_item"]
    assert item.labels == ("not faithful", "faithful") and item.n == 4
    assert item.table == [[1, 1], [1, 1]]  # reference rows, judge columns
    assert (result.detection.tp, result.detection.fn) == (1, 1)
    assert (result.detection.fp, result.detection.tn) == (1, 1)
    assert result.detection.recall == 0.5 and result.detection.precision == 0.5
    assert result.excluded == ["E"]  # no judge score: listed and left out


def test_ac_evl_07_measures_02_key_point_tables_three_class_and_binary() -> None:
    result = evaluate(five(), resamples=50, seed=0)
    three = result.measures["key_point_3class"]
    assert three.n == 6 and three.table == [[4, 1, 0], [0, 1, 0], [0, 0, 0]]
    assert three.agreement == pytest.approx(5 / 6)
    two = result.measures["key_point_binary"]
    assert two.labels == ("not covered", "covered") and two.table == [[1, 0], [1, 4]]


def test_ac_evl_07_measures_03_item_correct_means_all_covered_and_none_contradicted() -> None:
    result = evaluate(five(), resamples=50, seed=0)
    item = result.measures["correct_item"]
    assert item.labels == ("not correct", "correct") and item.n == 5
    assert item.table == [[1, 0], [1, 3]]
    contradicted = [out("F", ["covered", "contradicted"], ["covered", "covered"])]
    assert evaluate(contradicted, resamples=10, seed=0).measures["correct_item"].table == [
        [0, 1], [0, 0]]


def test_ac_evl_07_measures_04_a_single_class_is_reported_as_such_with_counts() -> None:
    same = [out(str(i), ["covered"], ["covered"]) for i in range(5)]
    item = evaluate(same, resamples=50, seed=0).measures["correct_item"]
    assert item.kappa is None and item.kappa_text == SINGLE_CLASS and item.interval is None
    assert item.agreement == 1.0 and item.table == [[0, 0], [0, 5]]


def test_ac_evl_07_measures_05_a_class_over_ninety_percent_is_flagged_unstable() -> None:
    rows = [out(str(i), ["covered"], ["covered"]) for i in range(19)]
    rows.append(out("x", ["missing"], ["covered"]))
    item = evaluate(rows, resamples=50, seed=0).measures["correct_item"]
    assert item.unstable and item.majority == pytest.approx(1.0)
    assert not measure("m", [("a", "a"), ("b", "b")], [0, 1], ("a", "b")).unstable


def test_ac_evl_07_measures_06_every_disagreement_is_listed_with_its_facts() -> None:
    found = disagreements(five())
    by_level = {(d.output_id, d.level): d for d in found}
    key = by_level[("A", "key point")]
    assert (key.reference, key.judge, key.text) == ("covered", "missing", "key 2: point 2")
    assert not key.borderline
    faith = by_level[("D", "faithfulness item")]
    assert (faith.reference, faith.judge) == ("faithful", "not faithful") and faith.borderline
    assert faith.text == ("reference: unsupported claims none, contradicted no; "
                          "judge: score 0.5, flagged claims fine claim (unsupported)")
    missed = by_level[("C", "faithfulness item")]
    assert missed.text == ('reference: unsupported claims "bad dose", contradicted no; '
                           "judge: score 1.0, flagged claims none")
    assert ("A", "correctness item") in by_level
    assert ("E", "faithfulness item") not in by_level  # no judge score, so excluded
    assert len(found) == 4
