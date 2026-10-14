"""Batch 2 (T083): the single fact drafts follow the schema, the split plan and the set rules."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from docdesk.evals.golden.loader import read_file
from docdesk.evals.golden.schema import GoldenItem
from docdesk.evals.golden.splits import split_for

GOLDEN = Path(__file__).resolve().parents[2] / "evals" / "golden"


def batch(name: str) -> list[GoldenItem]:
    """The items of one batch file, which must parse without problems."""
    items, problems = read_file(GOLDEN / name)
    assert problems == []
    return items


def test_ac_evl_01_batch_two_has_21_single_fact_items_split_13_dev_and_8_test() -> None:
    items = batch("batch2_single_fact.yaml")
    assert {item.type for item in items} == {"single_fact"}
    assert [item.split for item in items] == [split_for("single_fact", n) for n in range(10, 31)]
    assert Counter(item.split for item in items) == {"dev": 13, "test": 8}


def test_ac_evl_01_batch_two_mixes_both_corpora() -> None:
    items = batch("batch2_single_fact.yaml")
    corpora = {e.source.split(":")[1] for item in items for e in item.gold_evidence}
    assert corpora == {"openfda", "medlineplus"}
