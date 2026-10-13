"""The disclaimer and refusal text are fixed in code, never written by the model (AC-GEN-06)."""

from __future__ import annotations

from docdesk.guardrails.policy import DISCLAIMER, REFUSAL_MESSAGE, with_disclaimer


def test_ac_gen_06_the_disclaimer_says_this_is_not_medical_advice() -> None:
    assert "not medical advice" in DISCLAIMER.lower()


def test_ac_gen_06_every_answer_gets_the_disclaimer_appended_by_code() -> None:
    assert with_disclaimer("Aspirin thins blood.") == f"Aspirin thins blood.\n\n{DISCLAIMER}"


def test_ac_gen_06_an_abstain_sentence_also_gets_the_disclaimer() -> None:
    assert with_disclaimer("Nothing found.").endswith(DISCLAIMER)


def test_ac_gen_06_the_disclaimer_is_not_added_twice() -> None:
    once = with_disclaimer("Text.")
    assert with_disclaimer(once) == once


def test_ac_gen_05_the_refusal_message_points_to_a_professional() -> None:
    assert "pharmacist" in REFUSAL_MESSAGE or "doctor" in REFUSAL_MESSAGE
