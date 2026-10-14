"""Rules that hold across all the golden batch files: ids, documents and the corpus mix."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from docdesk.evals.golden.loader import read_items

GOLDEN = Path(__file__).resolve().parents[2] / "evals" / "golden"
MAX_ITEMS_PER_DOCUMENT = 2


def test_ac_evl_01_every_golden_file_parses_and_ids_are_unique() -> None:
    items, problems = read_items(GOLDEN)
    assert problems == []
    ids = [item.id for _, item in items]
    assert len(ids) == len(set(ids))


def test_ac_evl_01_no_document_serves_more_than_two_items_in_the_whole_set() -> None:
    items, _ = read_items(GOLDEN)
    per_document: Counter[str] = Counter()
    for _, item in items:
        per_document.update({entry.source for entry in item.gold_evidence})
    assert max(per_document.values()) <= MAX_ITEMS_PER_DOCUMENT
