"""F5: kappa resamples with one constant side count as 0, and outputs resample by item."""

from __future__ import annotations

from docdesk.evals.calib_join import JudgedOutput, JudgeSide
from docdesk.evals.calib_measures import evaluate
from docdesk.evals.calib_stats import kappa_interval

BINARY = ("no", "yes")


def test_ac_evl_07_cluster_01_a_resample_with_one_constant_side_counts_as_kappa_zero() -> None:
    # reference: 3 yes, 3 no. judge: agrees on all but one, so kappa is defined and below 1.
    cells = [("yes", "yes")] * 3 + [("no", "no")] * 2 + [("no", "yes")]
    result = kappa_interval(cells, list(range(6)), BINARY, resamples=2000, seed=0)
    assert result is not None
    assert result.zero_single_class > 0
    assert result.undefined > 0  # both sides constant: no kappa, left out and counted
    assert result.valid + result.undefined == result.resamples
    assert result.low <= 0.0  # the zeros are inside the interval, not silently removed


def test_ac_evl_07_cluster_02_both_sides_constant_is_the_only_undefined_case() -> None:
    cells = [("yes", "yes")] * 4 + [("no", "no")] * 4
    result = kappa_interval(cells, [0] * 4 + [1] * 4, BINARY, resamples=400, seed=3)
    assert result.zero_single_class == 0
    assert result.undefined > 0 and result.low == result.high == 1.0


def judged(output_id: str, item_id: str, judge_score: float, ref_unsupported: bool):
    side = JudgeSide("scored", judge_score, [], [])
    claims = ["unsupported claim"] if ref_unsupported else []
    return JudgedOutput("natural", 1, output_id, item_id, False, [], [], claims, False, side)


def test_ac_evl_07_cluster_03_outputs_of_one_item_are_one_resampling_unit() -> None:
    outputs = [
        judged("a1", "gi-001", 1.0, False), judged("a2", "gi-001", 1.0, False),
        judged("b1", "gi-002", 0.5, True), judged("b2", "gi-002", 0.5, True),
        judged("c1", "gi-003", 1.0, False), judged("d1", "gi-004", 0.5, True),
        judged("e1", "gi-005", 0.5, False),
    ]
    by_item = evaluate(outputs, resamples=600, seed=0).measures["faithfulness_item"]
    pairs = [("faithful" if not o.ref_claims else "not faithful",
              "faithful" if o.judge.faith_score == 1.0 else "not faithful") for o in outputs]
    ids = {"gi-001": 0, "gi-002": 1, "gi-003": 2, "gi-004": 3, "gi-005": 4}
    expected = kappa_interval(
        pairs, [ids[o.item_id] for o in outputs], ("faithful", "not faithful"),
        resamples=600, seed=0,
    )
    assert by_item.interval == expected
