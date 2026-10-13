"""AC-EVL-05: bootstrap intervals and paired comparison, with fixed seeds and known answers."""

from __future__ import annotations

import pytest

from docdesk.evals.stats import bootstrap_ci, paired_comparison


def test_ac_evl_05_the_interval_of_identical_values_is_that_value() -> None:
    interval = bootstrap_ci([0.5] * 20, seed=1)
    assert (interval.low, interval.estimate, interval.high) == (0.5, 0.5, 0.5)


def test_ac_evl_05_the_estimate_is_the_plain_mean_and_lies_inside_the_interval() -> None:
    interval = bootstrap_ci([0.0, 1.0, 1.0, 0.0, 1.0, 1.0, 1.0, 0.0], seed=1)
    assert interval.estimate == 0.625
    assert interval.low <= interval.estimate <= interval.high


def test_ac_evl_05_the_same_seed_gives_the_same_interval_and_another_seed_may_not() -> None:
    values = [(n * 0.37) % 1.0 for n in range(30)]  # many distinct values
    assert bootstrap_ci(values, seed=7) == bootstrap_ci(values, seed=7)
    assert bootstrap_ci(values, seed=7) != bootstrap_ci(values, seed=8)


def test_ac_evl_05_more_items_give_a_narrower_interval() -> None:
    few = bootstrap_ci([0.0, 1.0] * 5, seed=1)
    many = bootstrap_ci([0.0, 1.0] * 50, seed=1)
    assert (many.high - many.low) < (few.high - few.low)


def test_ac_evl_05_a_higher_confidence_gives_a_wider_interval() -> None:
    values = [0.0, 1.0] * 20
    narrow = bootstrap_ci(values, confidence=0.80, seed=1)
    wide = bootstrap_ci(values, confidence=0.99, seed=1)
    assert (wide.high - wide.low) > (narrow.high - narrow.low)


def test_ac_evl_05_items_that_share_a_document_are_resampled_together() -> None:
    values = [0.0] * 4 + [1.0] * 4
    by_item = bootstrap_ci(values, seed=3, n_resamples=4000)
    by_document = bootstrap_ci(values, groups=["a"] * 4 + ["b"] * 4, seed=3, n_resamples=4000)
    assert by_document.low < 0.05 and by_document.high > 0.95  # whole documents drop out
    assert by_item.low > 0.1 and by_item.high < 0.9


def test_ac_evl_05_a_paired_difference_that_always_has_the_same_sign_is_clear() -> None:
    baseline = [0.2, 0.4, 0.6, 0.5, 0.3, 0.7, 0.4, 0.5]
    candidate = [value + 0.2 for value in baseline]
    result = paired_comparison(baseline, candidate, seed=1)
    assert result.mean_difference == pytest.approx(0.2)
    assert result.low == pytest.approx(0.2) and result.high == pytest.approx(0.2)
    assert result.clear and result.verdict == "candidate is better"


def test_ac_evl_05_a_clearly_worse_candidate_is_reported_as_worse() -> None:
    result = paired_comparison([1.0] * 10, [0.5] * 10, seed=1)
    assert result.clear and result.verdict == "candidate is worse"


def test_ac_evl_05_a_difference_smaller_than_the_interval_is_no_clear_difference() -> None:
    baseline = [1.0, 0.0, 1.0, 0.0, 1.0, 0.0, 1.0, 0.0, 1.0, 0.0]
    candidate = [0.0, 1.0, 1.0, 0.0, 0.0, 1.0, 1.0, 0.0, 1.0, 0.0]  # flips two items each way
    result = paired_comparison(baseline, candidate, seed=1)
    assert result.mean_difference == 0.0
    assert result.low < 0.0 < result.high
    assert not result.clear and result.verdict == "no clear difference"


def test_ac_evl_05_pairing_matters_the_same_items_must_line_up() -> None:
    with pytest.raises(ValueError, match="same items"):
        paired_comparison([1.0, 0.0], [1.0], seed=1)


def test_ac_evl_05_empty_input_and_bad_settings_are_errors() -> None:
    with pytest.raises(ValueError, match="no values"):
        bootstrap_ci([], seed=1)
    with pytest.raises(ValueError, match="confidence"):
        bootstrap_ci([1.0], confidence=1.5, seed=1)
    with pytest.raises(ValueError, match="groups"):
        bootstrap_ci([1.0, 2.0], groups=["a"], seed=1)
