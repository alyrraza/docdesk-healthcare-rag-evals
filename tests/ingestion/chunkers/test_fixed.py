"""Fixed size chunker invariants: size limit, coverage, overlap and order (AC-ING-05)."""

from __future__ import annotations

import pytest

from docdesk.ingestion.chunkers.fixed import VERSION, chunk
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
    """A sentence of exactly `words` words that is unique per n."""
    return " ".join([f"Sentence{n}"] + ["word"] * (words - 1)) + "."


def document(sentences: int, words: int = 6) -> str:
    return " ".join(sentence(n, words) for n in range(sentences))


def test_ac_ing_05_short_text_is_one_chunk_with_metadata() -> None:
    chunks = chunk([Block(page=3, text=sentence(0))], 20, 5, WordCounter())
    assert len(chunks) == 1
    only = chunks[0]
    assert (only.position, only.page, only.token_count) == (0, 3, 6)
    assert (only.text, only.chunker_version) == (sentence(0), VERSION)


def test_ac_ing_05_no_chunk_is_over_the_size_limit() -> None:
    chunks = chunk([Block(page=1, text=document(40))], 20, 6, WordCounter())
    assert len(chunks) > 1
    assert all(c.token_count <= 20 for c in chunks)
    assert all(c.token_count == WordCounter().count(c.text) for c in chunks)


def test_ac_ing_05_chunks_end_on_sentence_boundaries_when_sentences_fit() -> None:
    chunks = chunk([Block(page=1, text=document(40))], 20, 6, WordCounter())
    assert all(c.text.endswith(".") for c in chunks)


def test_ac_ing_05_every_sentence_appears_in_some_chunk() -> None:
    text = document(40)
    joined = "\n".join(c.text for c in chunk([Block(page=1, text=text)], 20, 6, WordCounter()))
    assert all(s in joined for s in split_sentences(text))


def test_ac_ing_05_the_next_chunk_starts_with_the_end_of_the_previous_one() -> None:
    chunks = chunk([Block(page=1, text=document(40))], 20, 6, WordCounter())
    for before, after in zip(chunks, chunks[1:], strict=False):
        last_sentence = split_sentences(before.text)[-1]
        assert after.text.startswith(last_sentence)


def test_ac_ing_05_zero_overlap_repeats_nothing() -> None:
    chunks = chunk([Block(page=1, text=document(40))], 20, 0, WordCounter())
    assert sum(c.token_count for c in chunks) == 40 * 6


def test_ac_ing_05_overlap_close_to_size_still_moves_forward() -> None:
    chunks = chunk([Block(page=1, text=document(30))], 14, 13, WordCounter())
    assert 15 <= len(chunks) < 100
    assert all(c.token_count <= 14 for c in chunks)


def test_ac_ing_05_positions_run_across_pages_and_chunks_stay_on_their_page() -> None:
    blocks = [Block(page=1, text=document(10)), Block(page=2, text=document(10))]
    chunks = chunk(blocks, 20, 0, WordCounter())
    assert [c.position for c in chunks] == list(range(len(chunks)))
    assert {c.page for c in chunks} == {1, 2}
    assert [c.page for c in chunks] == sorted(c.page for c in chunks)


def test_ac_ing_05_a_sentence_longer_than_the_limit_is_cut_by_words() -> None:
    long_sentence = " ".join(f"w{n}" for n in range(50)) + "."
    chunks = chunk([Block(page=1, text=long_sentence)], 10, 0, WordCounter())
    assert len(chunks) == 5
    assert all(c.token_count <= 10 for c in chunks)
    assert " ".join(c.text for c in chunks) == long_sentence


def test_ac_ing_05_a_single_word_longer_than_the_limit_is_cut_by_characters() -> None:
    chunks = chunk([Block(page=1, text="a" * 50)], 10, 0, CharCounter())
    assert [c.text for c in chunks] == ["a" * 10] * 5


def test_ac_ing_05_no_blocks_gives_no_chunks() -> None:
    assert chunk([], 20, 5, WordCounter()) == []


@pytest.mark.parametrize(("size", "overlap"), [(0, 0), (10, 10), (10, -1), (10, 11)])
def test_ac_ing_05_bad_size_or_overlap_is_refused(size: int, overlap: int) -> None:
    with pytest.raises(ValueError, match="overlap"):
        chunk([Block(page=1, text="Some text.")], size, overlap, WordCounter())
