"""Recursive chunker: keep paragraphs whole when they fit, split smaller only when they do not."""

from __future__ import annotations

import pytest

from docdesk.ingestion.chunkers.recursive import VERSION, chunk
from docdesk.ingestion.sentences import split_sentences
from docdesk.ingestion.types import Block


class WordCounter:
    """One token per whitespace separated word, so the expected numbers are easy to check."""

    def count(self, text: str) -> int:
        return len(text.split())


class CharCounter:
    """One token per character, to force the split of a single very long word."""

    def count(self, text: str) -> int:
        return len(text)


def sentence(n: int, words: int = 6) -> str:
    return " ".join([f"Sentence{n}"] + ["word"] * (words - 1)) + "."


def paragraph(n: int, sentences: int = 2) -> str:
    """A paragraph of `sentences` sentences of 6 words, unique per n."""
    return " ".join(sentence(n * 100 + k) for k in range(sentences))


def test_ac_ing_05_paragraphs_that_fit_are_grouped_and_kept_whole() -> None:
    text = "\n\n".join(paragraph(n) for n in range(3))
    chunks = chunk([Block(page=1, text=text)], 30, 0, WordCounter())
    assert [c.text for c in chunks] == [f"{paragraph(0)}\n\n{paragraph(1)}", paragraph(2)]


def test_ac_ing_05_metadata_is_filled_for_every_chunk() -> None:
    text = "\n\n".join(paragraph(n) for n in range(3))
    chunks = chunk([Block(page=4, text=text)], 30, 0, WordCounter())
    assert [c.position for c in chunks] == [0, 1]
    assert {c.page for c in chunks} == {4}
    assert {c.chunker_version for c in chunks} == {VERSION}
    assert all(c.token_count == WordCounter().count(c.text) for c in chunks)


def test_ac_ing_05_a_paragraph_over_the_limit_is_split_between_sentences() -> None:
    chunks = chunk([Block(page=1, text=paragraph(0, sentences=8))], 20, 0, WordCounter())
    assert len(chunks) > 1
    assert all(c.token_count <= 20 and c.text.endswith(".") for c in chunks)


def test_ac_ing_05_overlap_repeats_the_last_sentence_inside_a_long_paragraph() -> None:
    chunks = chunk([Block(page=1, text=paragraph(0, sentences=8))], 20, 6, WordCounter())
    for before, after in zip(chunks, chunks[1:], strict=False):
        assert after.text.startswith(split_sentences(before.text)[-1])


def test_ac_ing_05_every_sentence_survives_and_no_chunk_is_over_the_limit() -> None:
    text = "\n\n".join(paragraph(n, sentences=1 + n % 5) for n in range(12))
    chunks = chunk([Block(page=1, text=text)], 20, 6, WordCounter())
    joined = "\n".join(c.text for c in chunks)
    assert all(s in joined for s in split_sentences(text))
    assert all(c.token_count <= 20 for c in chunks)


def test_ac_ing_05_a_sentence_longer_than_the_limit_is_cut_by_words() -> None:
    long_sentence = " ".join(f"w{n}" for n in range(50)) + "."
    chunks = chunk([Block(page=1, text=long_sentence)], 10, 0, WordCounter())
    assert len(chunks) == 5
    assert " ".join(c.text for c in chunks) == long_sentence


def test_ac_ing_05_a_single_word_longer_than_the_limit_is_cut_by_characters() -> None:
    chunks = chunk([Block(page=1, text="a" * 50)], 10, 0, CharCounter())
    assert [c.text for c in chunks] == ["a" * 10] * 5


def test_ac_ing_05_chunks_never_cross_a_page() -> None:
    blocks = [Block(page=1, text=paragraph(0)), Block(page=2, text=paragraph(1))]
    chunks = chunk(blocks, 100, 0, WordCounter())
    assert [(c.page, c.position) for c in chunks] == [(1, 0), (2, 1)]


def test_ac_ing_05_no_blocks_gives_no_chunks() -> None:
    assert chunk([], 20, 5, WordCounter()) == []


@pytest.mark.parametrize(("size", "overlap"), [(0, 0), (10, 10), (10, -1)])
def test_ac_ing_05_bad_size_or_overlap_is_refused(size: int, overlap: int) -> None:
    with pytest.raises(ValueError, match="overlap"):
        chunk([Block(page=1, text="Some text.")], size, overlap, WordCounter())
