"""Refuse personal diagnosis and dose requests, answer what a document says (AC-GEN-05)."""

from __future__ import annotations

import pytest

from docdesk.guardrails.input import check_policy

DOSE_REQUESTS = [
    "What dose of famotidine should I take for my stomach pain?",
    "How much ibuprofen should I take for my back pain?",
    "Can I take aspirin with my warfarin?",
    "What is the right dosage for me?",
    "Is it safe for me to take naproxen every day?",
    "How much metformin should my mother take?",
    "My son is 6, what dose of amoxicillin should he get?",
    "What should the patient take for high blood pressure?",
    "According to the label, what dose should I take?",
    "how many tablets of paracetamol can i have today",
]

DIAGNOSIS_REQUESTS = [
    "Do I have diabetes if I am always thirsty?",
    "I have a rash and a fever, what do I have?",
    "Please diagnose my symptoms: headache and nausea.",
    "What is wrong with me? I feel dizzy every morning.",
    "My father has chest pain and sweating, does he have a heart attack?",
    "What could this be? I have had a cough for three weeks.",
]

ANSWERABLE = [
    "What does the famotidine label say about the recommended dose?",
    "What is the usual adult dose of famotidine according to its label?",
    "What are the common side effects of metoclopramide?",
    "What does the label say about taking naproxen with food?",
    "Which condition is glimepiride used to treat?",
    "What is type 2 diabetes?",
    "How is hypothyroidism diagnosed?",
    "What does the label say about the maximum daily dose of acetaminophen?",
    "Does the label say whether it is safe to use in pregnancy?",
    "I read the metoclopramide label. What side effects does it list?",
    "What should I know about aspirin and bleeding?",
    "What does the document say about dose adjustment in kidney disease?",
]


@pytest.mark.parametrize("question", DOSE_REQUESTS)
def test_ac_gen_05_a_request_for_what_this_person_should_take_is_refused_as_a_dose(
    question: str,
) -> None:
    decision = check_policy(question)
    assert decision.refused
    assert decision.reason == "personal_dose"


@pytest.mark.parametrize("question", DIAGNOSIS_REQUESTS)
def test_ac_gen_05_a_request_to_say_whether_this_person_has_a_condition_is_refused(
    question: str,
) -> None:
    decision = check_policy(question)
    assert decision.refused
    assert decision.reason == "personal_diagnosis"


@pytest.mark.parametrize("question", ANSWERABLE)
def test_ac_gen_05_a_question_about_what_a_document_says_is_not_refused(question: str) -> None:
    decision = check_policy(question)
    assert not decision.refused
    assert decision.reason == "allowed"


def test_ac_gen_05_case_and_extra_spaces_do_not_hide_a_personal_request() -> None:
    assert check_policy("WHAT   DOSE   SHOULD   I   TAKE?").refused
