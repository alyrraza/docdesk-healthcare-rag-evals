"""AnswerOutput follows OUTPUTS.md: flat, evidence first, short enums (AC-GEN-01)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from docdesk.generation.schema import ABSTAIN_SENTENCE, AnswerOutput

VALID = {
    "evidence_used": ["c1"],
    "answer": "Aspirin can cause stomach bleeding.",
    "citations": ["c1"],
    "confidence": "high",
    "abstained": False,
    "abstain_reason": "none",
}


def test_ac_gen_01_a_valid_answer_parses() -> None:
    output = AnswerOutput.model_validate(VALID)
    assert output.citations == ["c1"]
    assert output.abstain_reason == "none"


def test_ac_gen_01_evidence_comes_before_the_answer_and_conclusions_come_last() -> None:
    names = list(AnswerOutput.model_fields)
    assert names[0] == "evidence_used"
    assert names.index("evidence_used") < names.index("answer") < names.index("abstained")


@pytest.mark.parametrize(
    ("field", "value"),
    [("confidence", "certain"), ("abstain_reason", "dunno"), ("abstained", "maybe")],
)
def test_ac_gen_01_a_value_outside_the_enum_is_rejected(field: str, value: str) -> None:
    with pytest.raises(ValidationError):
        AnswerOutput.model_validate({**VALID, field: value})


def test_ac_gen_01_a_missing_field_is_rejected() -> None:
    broken = {k: v for k, v in VALID.items() if k != "citations"}
    with pytest.raises(ValidationError):
        AnswerOutput.model_validate(broken)


def test_ac_gen_01_an_unexpected_field_is_rejected() -> None:
    with pytest.raises(ValidationError):
        AnswerOutput.model_validate({**VALID, "disclaimer": "added by the model"})


def test_ac_gen_01_the_abstain_sentence_is_the_fixed_text_from_the_prompt() -> None:
    assert ABSTAIN_SENTENCE == (
        "The provided documents do not contain enough information to answer this."
    )
