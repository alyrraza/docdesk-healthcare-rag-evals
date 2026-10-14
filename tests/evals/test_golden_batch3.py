"""Batch 3 (T084): the multi chunk drafts follow the schema, the split plan and the set rules."""

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


def test_ac_evl_01_batch_three_has_19_multi_chunk_items_split_11_dev_and_8_test() -> None:
    items = batch("batch3_multi_chunk.yaml")
    assert {item.type for item in items} == {"multi_chunk"}
    assert [item.split for item in items] == [split_for("multi_chunk", n) for n in range(19)]
    assert Counter(item.split for item in items) == {"dev": 11, "test": 8}


def test_ac_evl_01_a_multi_chunk_item_has_two_or_three_quotes_that_differ() -> None:
    for item in batch("batch3_multi_chunk.yaml"):
        assert 2 <= len(item.gold_evidence) <= 3
        assert len({entry.text for entry in item.gold_evidence}) == len(item.gold_evidence)


def test_ac_evl_01_batch_three_mixes_both_corpora() -> None:
    items = batch("batch3_multi_chunk.yaml")
    corpora = {e.source.split(":")[1] for item in items for e in item.gold_evidence}
    assert corpora == {"openfda", "medlineplus"}
