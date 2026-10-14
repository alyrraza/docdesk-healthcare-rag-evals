"""Batch 4 (T085): the unanswerable drafts follow the schema, the split plan and the mix."""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path

from docdesk.evals.golden.loader import read_file
from docdesk.evals.golden.schema import GoldenItem
from docdesk.evals.golden.splits import split_for

GOLDEN = Path(__file__).resolve().parents[2] / "evals" / "golden"
FIRST_PERSON = re.compile(r"\b(i|me|my|mine|we|us|our|myself)\b", re.IGNORECASE)


def batch() -> list[GoldenItem]:
    """The items of batch 4, which must parse without problems."""
    items, problems = read_file(GOLDEN / "batch4_unanswerable.yaml")
    assert problems == []
    return items


def test_ac_evl_01_batch_four_has_19_unanswerable_items_split_11_dev_and_8_test() -> None:
    items = batch()
    assert {item.type for item in items} == {"unanswerable"}
    assert [item.split for item in items] == [split_for("unanswerable", n) for n in range(19)]
    assert Counter(item.split for item in items) == {"dev": 11, "test": 8}


def test_ac_evl_01_batch_four_ids_continue_after_gi_054() -> None:
    assert [item.id for item in batch()] == [f"gi-{n:03d}" for n in range(55, 74)]


def test_ac_evl_01_batch_four_has_8_near_misses_and_11_corpus_wide_items() -> None:
    scopes = Counter("corpus" if i.absence_scope == "corpus" else "document" for i in batch())
    assert scopes == {"document": 8, "corpus": 11}


def test_ac_evl_01_every_near_miss_names_a_different_document() -> None:
    documents = [i.absence_scope for i in batch() if i.absence_scope != "corpus"]
    assert len(set(documents)) == len(documents) == 8


def test_ac_evl_01_both_splits_hold_every_kind_of_unanswerable_question() -> None:
    kinds = Counter((i.split, i.absence_scope == "corpus") for i in batch())
    assert all(kinds[(split, wide)] >= 2 for split in ("dev", "test") for wide in (True, False))


def test_ac_evl_01_batch_four_items_are_drafts_with_a_reason_and_terms() -> None:
    for item in batch():
        assert item.verified is False
        assert item.no_evidence_reason.strip().endswith(".")
        assert item.absent_terms


def test_ac_evl_01_no_batch_four_question_asks_about_the_user_personally() -> None:
    for item in batch():
        assert FIRST_PERSON.search(item.question) is None, item.id
