"""Batch 1 (T082): ten single fact drafts follow the schema, the split plan and the batch rules."""

from __future__ import annotations

from pathlib import Path

from docdesk.evals.golden.loader import read_items
from docdesk.evals.golden.splits import split_for

GOLDEN = Path(__file__).resolve().parents[2] / "evals" / "golden"


def batch1() -> list:
    """The items of the batch 1 file, in file order."""
    items, problems = read_items(GOLDEN)
    assert problems == []
    return [item for path, item in items if path.name == "batch1_single_fact.yaml"]


def test_ac_evl_01_batch_one_has_ten_single_fact_items_that_pass_the_schema() -> None:
    items = batch1()
    assert len(items) == 10
    assert {item.type for item in items} == {"single_fact"}


def test_ac_evl_01_batch_one_uses_each_document_at_most_once() -> None:
    sources = [item.gold_evidence[0].source for item in batch1()]
    assert len(set(sources)) == 10
    assert {source.split(":")[1] for source in sources} == {"openfda", "medlineplus"}


def test_ac_evl_01_batch_one_splits_follow_the_plan_and_are_6_dev_4_test() -> None:
    items = batch1()
    assert [item.split for item in items] == [split_for("single_fact", n) for n in range(10)]
    assert sorted(item.split for item in items) == ["dev"] * 6 + ["test"] * 4
