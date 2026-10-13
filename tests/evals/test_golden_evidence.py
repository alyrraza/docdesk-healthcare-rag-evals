"""Which chunks count as gold for an evidence quote, and the exact-substring check."""

from __future__ import annotations

import pytest

from docdesk.evals.golden.evidence import (
    ChunkNotLocated,
    QuoteNotFound,
    check_quote,
    cleaned_document_text,
    gold_chunk_ids,
    locate_chunks,
)

DOC = "Alpha beta gamma delta. Epsilon zeta eta theta. Iota kappa lambda mu."


def chunks(*texts: str) -> list[tuple[str, str]]:
    """Give each text an id c0, c1, ... like a stored chunk."""
    return [(f"c{index}", text) for index, text in enumerate(texts)]


def test_ac_evl_01_the_cleaned_text_is_what_ingestion_would_chunk() -> None:
    assert cleaned_document_text(b"Hello   world\n\n\n\nBye") == "Hello world\n\nBye"


def test_ac_evl_01_a_quote_that_is_an_exact_substring_passes() -> None:
    check_quote(DOC, "Epsilon zeta eta")


def test_ac_evl_01_a_quote_with_different_whitespace_is_not_an_exact_substring() -> None:
    with pytest.raises(QuoteNotFound):
        check_quote("one two\nthree four", "one two three")


def test_ac_evl_01_a_quote_missing_after_a_cleaner_change_is_an_error() -> None:
    with pytest.raises(QuoteNotFound, match="lambda  mu"):
        check_quote(DOC, "lambda  mu")
    with pytest.raises(QuoteNotFound):
        gold_chunk_ids(DOC, "not in the text", chunks(DOC))


def test_ac_evl_01_a_chunk_that_holds_the_whole_quote_is_gold() -> None:
    parts = chunks("Alpha beta gamma delta.", "Epsilon zeta eta theta.", "Iota kappa lambda mu.")
    assert gold_chunk_ids(DOC, "zeta eta", parts) == {"c1"}


def test_ac_evl_01_overlapping_chunks_that_both_hold_the_quote_are_both_gold() -> None:
    parts = chunks("Alpha beta gamma delta. Epsilon zeta", "gamma delta. Epsilon zeta eta theta.")
    assert gold_chunk_ids(DOC, "gamma delta. Epsilon", parts) == {"c0", "c1"}


def test_ac_evl_01_a_quote_across_a_boundary_is_gold_for_the_chunk_holding_most_of_it() -> None:
    parts = chunks("Alpha beta gamma delta. Epsilon zeta", "eta theta. Iota kappa lambda mu.")
    # The quote has 23 characters. c0 holds "Epsilon zeta" (12), c1 holds "eta theta." (10).
    assert gold_chunk_ids(DOC, "Epsilon zeta eta theta.", parts) == {"c0"}


def test_ac_evl_01_overlap_of_exactly_half_the_quote_counts() -> None:
    doc = "aaaa bbbb cccc dddd"
    parts = chunks("aaaa bbbb", "cccc dddd")
    # The quote "bbbb ccc" has 8 characters. c0 holds "bbbb" (4, exactly half), c1 holds "ccc" (3).
    assert gold_chunk_ids(doc, "bbbb ccc", parts) == {"c0"}


def test_ac_evl_01_a_chunk_that_only_touches_a_few_characters_of_the_quote_is_not_gold() -> None:
    parts = chunks("Alpha beta gamma delta. Epsilon", "zeta eta theta. Iota kappa lambda mu.")
    assert gold_chunk_ids(DOC, "Epsilon zeta eta theta.", parts) == {"c1"}


def test_ac_evl_01_a_quote_that_appears_twice_makes_a_chunk_around_either_one_gold() -> None:
    doc = "Take with food. Store dry. Take with food. Keep cool."
    parts = chunks("Take with food. Store dry.", "Take with food. Keep cool.")
    assert gold_chunk_ids(doc, "Take with food.", parts) == {"c0", "c1"}


def test_ac_evl_01_chunks_are_located_through_line_breaks_in_the_document() -> None:
    doc = "one two\nthree four\n\nfive six"
    spans = locate_chunks(doc, ["one two three four", "five six"])
    assert spans == [(0, 18), (19, 27)]


def test_ac_evl_01_a_repeated_chunk_text_is_located_at_successive_places() -> None:
    doc = "same words. other. same words."
    spans = locate_chunks(doc, ["same words.", "same words."])
    assert spans[0][0] < spans[1][0]


def test_ac_evl_01_a_chunk_that_is_not_in_the_document_is_an_error_not_a_guess() -> None:
    with pytest.raises(ChunkNotLocated, match="c1"):
        gold_chunk_ids(DOC, "zeta eta", chunks("Alpha beta", "text from another document"))
