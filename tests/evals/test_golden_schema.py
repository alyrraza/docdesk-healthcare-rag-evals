"""AC-EVL-01: a golden item must validate against its schema, with its evidence quotes."""

from __future__ import annotations

from typing import Any

import pytest
from pydantic import ValidationError

from docdesk.evals.golden.schema import GoldenItem

SOURCE = "seed:openfda:0005aafa-08f8-4990-a54d-cc097195708f"


def single_fact(**changes: Any) -> dict[str, Any]:
    """A valid single fact item; tests change one field at a time."""
    item: dict[str, Any] = {
        "id": "gi-001",
        "type": "single_fact",
        "split": "dev",
        "question": "What is the maximum daily dose on the acetaminophen label?",
        "answerable": True,
        "gold_route": "documents",
        "gold_facts": ["The maximum is 3 doses in 24 hours"],
        "gold_evidence": [{"source": SOURCE, "text": "do not take more than 3 doses"}],
        "verified_by": "ali",
        "verified_on": "2026-10-20",
    }
    return {**item, **changes}


def unanswerable(**changes: Any) -> dict[str, Any]:
    item = single_fact(
        id="gi-002",
        type="unanswerable",
        answerable=False,
        gold_facts=[],
        gold_evidence=[],
        no_evidence_reason="No label in the corpus covers this drug",
    )
    return {**item, **changes}


def test_ac_evl_01_a_valid_single_fact_item_is_accepted() -> None:
    item = GoldenItem.model_validate(single_fact())
    assert item.gold_evidence[0].source == SOURCE
    assert item.verified_on.isoformat() == "2026-10-20"


def test_ac_evl_01_a_valid_unanswerable_item_has_no_evidence_and_a_reason() -> None:
    assert GoldenItem.model_validate(unanswerable()).gold_evidence == []


@pytest.mark.parametrize("missing", ["verified_by", "verified_on"])
def test_ac_evl_01_every_item_must_carry_verified_by_and_verified_on(missing: str) -> None:
    data = single_fact()
    del data[missing]
    with pytest.raises(ValidationError, match=missing):
        GoldenItem.model_validate(data)


def test_ac_evl_01_an_unknown_field_is_rejected_so_a_typo_cannot_hide() -> None:
    with pytest.raises(ValidationError, match="gold_chunk_ids"):
        GoldenItem.model_validate(single_fact(gold_chunk_ids=["c1"]))


@pytest.mark.parametrize(
    "changes",
    [
        {"id": "item-1"},
        {"type": "essay"},
        {"split": "validation"},
        {"gold_route": "web"},
        {"verified_by": ""},
        {"verified_on": "yesterday"},
    ],
)
def test_ac_evl_01_bad_field_values_are_rejected(changes: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        GoldenItem.model_validate(single_fact(**changes))


def test_ac_evl_01_a_quote_longer_than_300_characters_is_rejected() -> None:
    evidence = [{"source": SOURCE, "text": "x" * 301}]
    with pytest.raises(ValidationError, match="300"):
        GoldenItem.model_validate(single_fact(gold_evidence=evidence))


def test_ac_evl_01_a_quote_with_edge_whitespace_or_no_text_is_rejected() -> None:
    for text in [" padded", "padded\n", ""]:
        with pytest.raises(ValidationError):
            GoldenItem.model_validate(single_fact(gold_evidence=[{"source": SOURCE, "text": text}]))


def test_ac_evl_01_a_source_that_is_not_a_seed_key_is_rejected() -> None:
    evidence = [{"source": "seed:openfda", "text": "a quote"}]
    with pytest.raises(ValidationError, match="seed:<corpus>:<source id>"):
        GoldenItem.model_validate(single_fact(gold_evidence=evidence))


def test_ac_evl_01_a_document_item_needs_at_least_one_quote() -> None:
    with pytest.raises(ValidationError, match="evidence"):
        GoldenItem.model_validate(single_fact(gold_evidence=[]))


def test_ac_evl_01_a_single_fact_item_has_exactly_one_quote() -> None:
    two = [{"source": SOURCE, "text": "first"}, {"source": SOURCE, "text": "second"}]
    with pytest.raises(ValidationError, match="exactly one"):
        GoldenItem.model_validate(single_fact(gold_evidence=two))


def test_ac_evl_01_a_multi_chunk_item_needs_two_quotes() -> None:
    with pytest.raises(ValidationError, match="at least two"):
        GoldenItem.model_validate(single_fact(type="multi_chunk"))
    two = [{"source": SOURCE, "text": "first"}, {"source": SOURCE, "text": "second"}]
    assert GoldenItem.model_validate(single_fact(type="multi_chunk", gold_evidence=two))


def test_ac_evl_01_the_same_quote_twice_in_one_item_is_rejected() -> None:
    same = [{"source": SOURCE, "text": "same"}, {"source": SOURCE, "text": "same"}]
    with pytest.raises(ValidationError, match="duplicate"):
        GoldenItem.model_validate(single_fact(type="multi_chunk", gold_evidence=same))


def test_ac_evl_01_an_unanswerable_item_must_explain_why_it_has_no_evidence() -> None:
    with pytest.raises(ValidationError, match="no_evidence_reason"):
        GoldenItem.model_validate(unanswerable(no_evidence_reason=""))


def test_ac_evl_01_an_unanswerable_item_cannot_carry_facts_or_quotes() -> None:
    with pytest.raises(ValidationError, match="unanswerable"):
        GoldenItem.model_validate(unanswerable(gold_facts=["a fact"]))
    evidence = [{"source": SOURCE, "text": "a quote"}]
    with pytest.raises(ValidationError, match="unanswerable"):
        GoldenItem.model_validate(unanswerable(gold_evidence=evidence))


def test_ac_evl_01_a_reason_is_not_allowed_when_quotes_exist() -> None:
    with pytest.raises(ValidationError, match="no_evidence_reason"):
        GoldenItem.model_validate(single_fact(no_evidence_reason="not needed"))


def test_ac_evl_01_an_answerable_item_needs_gold_facts() -> None:
    with pytest.raises(ValidationError, match="gold_facts"):
        GoldenItem.model_validate(single_fact(gold_facts=[]))


def test_ac_evl_01_a_structured_item_needs_sql_and_a_result() -> None:
    base = single_fact(type="structured", gold_route="structured", gold_evidence=[])
    with pytest.raises(ValidationError, match="gold_sql"):
        GoldenItem.model_validate(base)
    ok = {**base, "gold_sql": "SELECT count(*) FROM synthea_patients", "gold_result": [[12]]}
    assert GoldenItem.model_validate(ok).gold_result == [[12]]


def test_ac_evl_01_sql_on_a_document_item_is_rejected() -> None:
    with pytest.raises(ValidationError, match="gold_sql"):
        GoldenItem.model_validate(single_fact(gold_sql="SELECT 1", gold_result=[[1]]))


def test_ac_evl_01_adversarial_kind_must_match_the_type() -> None:
    with pytest.raises(ValidationError, match="adversarial_kind"):
        GoldenItem.model_validate(unanswerable(type="adversarial"))
    with pytest.raises(ValidationError, match="adversarial_kind"):
        GoldenItem.model_validate(single_fact(adversarial_kind="dose_request"))
    refused = unanswerable(type="adversarial", adversarial_kind="dose_request")
    assert GoldenItem.model_validate(refused)
