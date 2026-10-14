"""AC-EVL-01: an unanswerable item must name the terms whose absence proves it (schema rules)."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from docdesk.evals.golden.schema import GoldenItem

SOURCE = "seed:openfda:0005aafa-08f8-4990-a54d-cc097195708f"


def unanswerable(**changes: Any) -> dict[str, Any]:
    """A valid corpus scoped unanswerable draft; tests change one field at a time."""
    item: dict[str, Any] = {
        "id": "gi-055",
        "type": "unanswerable",
        "split": "dev",
        "question": "What is the usual adult dose of warfarin for atrial fibrillation?",
        "answerable": False,
        "gold_route": "documents",
        "no_evidence_reason": "No document in the corpus is about warfarin.",
        "absent_terms": ["warfarin"],
        "absence_scope": "corpus",
    }
    return {**item, **changes}


def test_ac_evl_01_an_unanswerable_item_with_terms_and_a_scope_is_accepted() -> None:
    item = GoldenItem.model_validate(unanswerable())
    assert item.absent_terms == ["warfarin"]
    assert item.absence_scope == "corpus"


def test_ac_evl_01_the_scope_may_be_one_source_key() -> None:
    item = GoldenItem.model_validate(unanswerable(absence_scope=SOURCE))
    assert item.absence_scope == SOURCE


@pytest.mark.parametrize("missing", ["absent_terms", "absence_scope"])
def test_ac_evl_01_an_unanswerable_item_needs_absent_terms_and_a_scope(missing: str) -> None:
    data = unanswerable()
    del data[missing]
    with pytest.raises(ValidationError, match=missing):
        GoldenItem.model_validate(data)


@pytest.mark.parametrize("scope", ["document", "seed:openfda", "", "everywhere"])
def test_ac_evl_01_a_scope_is_corpus_or_a_source_key_and_nothing_else(scope: str) -> None:
    with pytest.raises(ValidationError, match="absence_scope"):
        GoldenItem.model_validate(unanswerable(absence_scope=scope))


@pytest.mark.parametrize("terms", [[], [""], ["  "], ["warfarin", "warfarin"]])
def test_ac_evl_01_absent_terms_are_non_empty_and_listed_once(terms: list[str]) -> None:
    with pytest.raises(ValidationError, match="absent_terms"):
        GoldenItem.model_validate(unanswerable(absent_terms=terms))


def test_ac_evl_01_two_terms_that_differ_only_by_case_count_as_one() -> None:
    with pytest.raises(ValidationError, match="absent_terms"):
        GoldenItem.model_validate(unanswerable(absent_terms=["Warfarin", "warfarin"]))


def test_ac_evl_01_an_answerable_item_cannot_carry_absent_terms() -> None:
    answerable = {
        "id": "gi-001",
        "type": "single_fact",
        "split": "dev",
        "question": "What is the maximum daily dose on the acetaminophen label?",
        "answerable": True,
        "gold_route": "documents",
        "gold_facts": ["The maximum is 3 doses in 24 hours"],
        "gold_evidence": [{"source": SOURCE, "text": "do not take more than 3 doses"}],
        "absent_terms": ["warfarin"],
        "absence_scope": "corpus",
    }
    with pytest.raises(ValidationError, match="absent_terms"):
        GoldenItem.model_validate(answerable)
