"""T100 (AC-EVL-07): agreement maths, checked on tables where the answer is known by hand."""

from __future__ import annotations

import pytest

from docdesk.evals.calib_stats import (
    SINGLE_CLASS,
    agreement,
    cohen_kappa,
    confusion,
    kappa_interval,
    majority_share,
)

BINARY = ("no", "yes")


def pairs(*cells: tuple[str, str, int]) -> list[tuple[str, str]]:
    """Expand (reference, judge, count) cells into one pair per label."""
    return [(ref, judge) for ref, judge, count in cells for _ in range(count)]


def test_ac_evl_07_stats_01_confusion_counts_reference_rows_and_judge_columns() -> None:
    table = confusion(pairs(("yes", "yes", 3), ("yes", "no", 1), ("no", "no", 2)), BINARY)
    assert table == [[2, 0], [1, 3]]  # rows: reference no, yes; columns: judge no, yes


def test_ac_evl_07_stats_02_raw_agreement_is_the_diagonal_share() -> None:
    assert agreement([[2, 0], [1, 3]]) == pytest.approx(5 / 6)


def test_ac_evl_07_stats_03_kappa_matches_a_hand_computed_value() -> None:
    # 20 yes/yes, 5 yes/no, 10 no/yes, 15 no/no: po 0.7, pe 0.5, kappa 0.4 (textbook example)
    table = confusion(pairs(("yes", "yes", 20), ("yes", "no", 5), ("no", "yes", 10),
                            ("no", "no", 15)), BINARY)
    assert cohen_kappa(table) == pytest.approx(0.4)


def test_ac_evl_07_stats_04_perfect_agreement_with_two_classes_is_one() -> None:
    assert cohen_kappa(confusion(pairs(("yes", "yes", 4), ("no", "no", 4)), BINARY)) == 1.0


def test_ac_evl_07_stats_05_chance_level_agreement_is_zero() -> None:
    table = confusion(pairs(("yes", "yes", 5), ("yes", "no", 5), ("no", "yes", 5),
                            ("no", "no", 5)), BINARY)
    assert cohen_kappa(table) == pytest.approx(0.0)


def test_ac_evl_07_stats_06_a_single_class_has_no_kappa() -> None:
    assert cohen_kappa(confusion(pairs(("yes", "yes", 9)), BINARY)) is None
    # the reference uses one class only: kappa is not reported even if the judge varies
    assert cohen_kappa(confusion(pairs(("yes", "yes", 8), ("yes", "no", 1)), BINARY)) is None
    assert SINGLE_CLASS == "undefined, single class"


def test_ac_evl_07_stats_07_three_classes_use_the_same_formula() -> None:
    labels = ("covered", "missing", "contradicted")
    table = confusion(pairs(("covered", "covered", 6), ("covered", "missing", 2),
                            ("missing", "missing", 2)), labels)
    # po = 0.8; pe = 0.8 * 0.6 + 0.2 * 0.4 = 0.56; kappa = 0.24 / 0.44
    assert cohen_kappa(table) == pytest.approx(0.24 / 0.44)


def test_ac_evl_07_stats_08_majority_share_looks_at_the_larger_side() -> None:
    table = confusion(pairs(("yes", "yes", 18), ("yes", "no", 1), ("no", "no", 1)), BINARY)
    assert majority_share(table) == pytest.approx(0.95)  # the reference is 19 of 20 yes


def test_ac_evl_07_stats_09_the_interval_is_repeatable_and_holds_the_estimate() -> None:
    cells = pairs(("yes", "yes", 20), ("yes", "no", 5), ("no", "yes", 10), ("no", "no", 15))
    groups = list(range(len(cells)))  # every pair is its own resampling unit
    first = kappa_interval(cells, groups, BINARY, resamples=500, seed=1)
    second = kappa_interval(cells, groups, BINARY, resamples=500, seed=1)
    assert first == second
    assert first.low <= 0.4 <= first.high and first.valid == 500


def test_ac_evl_07_stats_10_pairs_of_one_group_are_resampled_together() -> None:
    cells = pairs(("yes", "yes", 4), ("no", "no", 4))
    # two groups: all the yes pairs, all the no pairs. A resample of one group only is single
    # class and has no kappa, so those resamples are counted out, not turned into numbers.
    groups = [0] * 4 + [1] * 4
    result = kappa_interval(cells, groups, BINARY, resamples=400, seed=3)
    assert 0 < result.valid < 400 and result.low == result.high == 1.0


def test_ac_evl_07_stats_11_no_interval_when_the_estimate_itself_is_undefined() -> None:
    cells = pairs(("yes", "yes", 6))
    assert kappa_interval(cells, list(range(6)), BINARY, resamples=100, seed=1) is None
