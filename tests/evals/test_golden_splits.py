"""The planned dev and test split of the whole golden set, decided before any item is written."""

from __future__ import annotations

from docdesk.evals.golden.splits import TYPE_COUNTS, split_for


def all_splits() -> dict[str, list[str]]:
    """Every planned item's split, grouped by type, in position order."""
    return {kind: [split_for(kind, n) for n in range(count)] for kind, count in TYPE_COUNTS.items()}


def test_ac_evl_01_the_plan_has_100_items_with_the_documented_type_mix() -> None:
    assert sum(TYPE_COUNTS.values()) == 100
    assert TYPE_COUNTS["single_fact"] == 31
    assert TYPE_COUNTS["unanswerable"] == 19


def test_ac_evl_01_the_whole_plan_is_60_dev_and_40_test() -> None:
    flat = [split for splits in all_splits().values() for split in splits]
    assert (flat.count("dev"), flat.count("test")) == (60, 40)


def test_ac_evl_01_each_type_gets_about_two_fifths_of_its_items_as_test() -> None:
    for kind, splits in all_splits().items():
        share = splits.count("test") / len(splits)
        assert abs(share - 0.4) <= 0.07, kind


def test_ac_evl_01_batch_one_of_single_facts_is_6_dev_and_4_test() -> None:
    first_ten = [split_for("single_fact", n) for n in range(10)]
    assert (first_ten.count("dev"), first_ten.count("test")) == (6, 4)


def test_ac_evl_01_the_assignment_is_the_same_on_every_call() -> None:
    assert all_splits() == all_splits()


def test_ac_evl_01_a_position_outside_the_plan_is_an_error() -> None:
    import pytest

    with pytest.raises(ValueError):
        split_for("single_fact", 31)
    with pytest.raises(ValueError):
        split_for("essay", 0)
