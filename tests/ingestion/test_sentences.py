"""Sentence splitting is the shared boundary rule for every chunker (AC-ING-05)."""

from __future__ import annotations

from docdesk.ingestion.sentences import split_sentences


def test_ac_ing_05_text_is_split_after_sentence_end_marks() -> None:
    assert split_sentences("Take one tablet. Do not crush it! Is it safe? Ask a doctor.") == [
        "Take one tablet.",
        "Do not crush it!",
        "Is it safe?",
        "Ask a doctor.",
    ]


def test_ac_ing_05_a_period_before_a_lowercase_word_is_not_a_boundary() -> None:
    assert split_sentences("Use e.g. water. Then rest.") == ["Use e.g. water.", "Then rest."]


def test_ac_ing_05_a_decimal_number_is_not_split() -> None:
    assert split_sentences("Dose is 2.5 mg daily. Stop if ill.") == [
        "Dose is 2.5 mg daily.",
        "Stop if ill.",
    ]


def test_ac_ing_05_paragraph_breaks_always_end_a_sentence() -> None:
    assert split_sentences("Warnings\n\nDo not drive") == ["Warnings", "Do not drive"]


def test_ac_ing_05_single_line_breaks_inside_a_sentence_become_spaces() -> None:
    assert split_sentences("Take one\ntablet daily.") == ["Take one tablet daily."]


def test_ac_ing_05_empty_text_has_no_sentences() -> None:
    assert split_sentences("  \n\n ") == []
