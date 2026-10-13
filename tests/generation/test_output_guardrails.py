"""The three validation layers from OUTPUTS.md (AC-GEN-01, AC-GEN-02)."""

from __future__ import annotations

import json

import pytest

from docdesk.generation.schema import ABSTAIN_SENTENCE
from docdesk.guardrails.citations import check_citations
from docdesk.guardrails.output import OutputError, check_fields, parse_answer, semantic_flags

LABELS = {"c1", "c2", "c3"}
GOOD = {
    "evidence_used": ["c1", "c2"],
    "answer": "Take 2 tablets daily.",
    "citations": ["c1"],
    "confidence": "medium",
    "abstained": False,
    "abstain_reason": "none",
}
ABSTAIN = {
    "evidence_used": [],
    "answer": ABSTAIN_SENTENCE,
    "citations": [],
    "confidence": "low",
    "abstained": True,
    "abstain_reason": "no_evidence",
}


def text(data: dict) -> str:
    return json.dumps(data)


def test_ac_gen_01_layer_one_parses_valid_json_into_the_schema() -> None:
    assert parse_answer(text(GOOD)).answer == "Take 2 tablets daily."


@pytest.mark.parametrize(
    "raw", ["", "not json", '{"answer": "x"', "[1, 2]", text({**GOOD, "confidence": "sure"})]
)
def test_ac_gen_01_layer_one_rejects_text_that_is_not_the_schema(raw: str) -> None:
    with pytest.raises(OutputError) as caught:
        parse_answer(raw)
    assert caught.value.layer == "schema"
    assert caught.value.message


def test_ac_gen_01_layer_two_accepts_a_consistent_answer_and_a_consistent_abstain() -> None:
    check_fields(parse_answer(text(GOOD)), LABELS)
    check_fields(parse_answer(text(ABSTAIN)), LABELS)


@pytest.mark.parametrize(
    ("change", "fragment"),
    [
        ({"abstain_reason": "no_evidence"}, "abstain_reason"),
        ({"citations": []}, "at least one citation"),
        ({"citations": ["c1"], "evidence_used": ["c2"]}, "subset"),
    ],
)
def test_ac_gen_01_layer_two_rejects_contradictory_fields_for_an_answer(
    change: dict, fragment: str
) -> None:
    with pytest.raises(OutputError, match=fragment) as caught:
        check_fields(parse_answer(text({**GOOD, **change})), LABELS)
    assert caught.value.layer == "fields"


@pytest.mark.parametrize(
    ("change", "fragment"),
    [
        ({"abstain_reason": "none"}, "abstain_reason"),
        ({"citations": ["c1"]}, "no citations"),
        ({"answer": "I think maybe yes"}, "fixed abstain sentence"),
    ],
)
def test_ac_gen_01_layer_two_rejects_contradictory_fields_for_an_abstain(
    change: dict, fragment: str
) -> None:
    with pytest.raises(OutputError, match=fragment):
        check_fields(parse_answer(text({**ABSTAIN, **change})), LABELS)


def test_ac_gen_02_a_citation_of_an_id_that_was_not_retrieved_is_rejected() -> None:
    output = parse_answer(text({**GOOD, "citations": ["c9"], "evidence_used": ["c9"]}))
    with pytest.raises(OutputError, match="c9") as caught:
        check_citations(output, LABELS)
    assert caught.value.layer == "citations"


def test_ac_gen_02_evidence_used_is_checked_too() -> None:
    output = parse_answer(text({**GOOD, "evidence_used": ["c1", "zzz"]}))
    with pytest.raises(OutputError, match="zzz"):
        check_citations(output, LABELS)


def test_ac_gen_02_check_fields_runs_the_membership_check() -> None:
    output = parse_answer(text({**GOOD, "citations": ["c7"], "evidence_used": ["c7"]}))
    with pytest.raises(OutputError, match="c7"):
        check_fields(output, LABELS)


def test_ac_gen_01_layer_three_flags_a_number_that_is_not_in_the_cited_evidence() -> None:
    output = parse_answer(text(GOOD))
    assert semantic_flags(output, {"c1": "Adults take 2 tablets a day."}) == []
    flags = semantic_flags(output, {"c1": "Adults take 4 tablets a day."})
    assert len(flags) == 1 and "2" in flags[0]


def test_ac_gen_01_layer_three_ignores_answers_that_abstained() -> None:
    assert semantic_flags(parse_answer(text(ABSTAIN)), {}) == []
