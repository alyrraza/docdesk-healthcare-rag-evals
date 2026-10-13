"""Parent-child chunker: small children for matching, each carrying its larger parent (E2)."""

from __future__ import annotations

import pytest

from docdesk.ingestion.chunkers.parent_child import PARENT_FACTOR, VERSION, chunk
from docdesk.ingestion.types import Block


class WordCounter:
    """One token per whitespace separated word, so the expected numbers are easy to check."""

    def count(self, text: str) -> int:
        return len(text.split())


def sentence(n: int) -> str:
    return " ".join([f"Sentence{n}"] + ["word"] * 5) + "."


def document(sentences: int) -> str:
    """Paragraphs of four sentences, so parents have paragraph structure to keep."""
    paragraphs = []
    for start in range(0, sentences, 4):
        paragraphs.append(" ".join(sentence(n) for n in range(start, min(start + 4, sentences))))
    return "\n\n".join(paragraphs)


def squash(text: str) -> str:
    return " ".join(text.split())


def test_ac_ing_05_children_are_within_size_and_parents_within_the_parent_limit() -> None:
    chunks = chunk([Block(page=1, text=document(48))], 12, 0, WordCounter())
    assert all(c.token_count <= 12 for c in chunks)
    assert all(WordCounter().count(c.parent_text or "") <= PARENT_FACTOR * 12 for c in chunks)


def test_ac_ing_05_every_child_is_found_inside_its_parent() -> None:
    chunks = chunk([Block(page=1, text=document(48))], 12, 3, WordCounter())
    assert all(squash(c.text) in squash(c.parent_text or "") for c in chunks)


def test_ac_ing_05_several_children_share_one_parent_and_a_long_text_has_many_parents() -> None:
    chunks = chunk([Block(page=1, text=document(48))], 12, 0, WordCounter())
    parents = {c.parent_text for c in chunks}
    assert 1 < len(parents) < len(chunks)


def test_ac_ing_05_every_sentence_is_covered_by_some_child() -> None:
    text = document(48)
    joined = "\n".join(c.text for c in chunk([Block(page=1, text=text)], 12, 0, WordCounter()))
    assert all(sentence(n) in joined for n in range(48))


def test_ac_ing_05_positions_pages_and_version_are_filled() -> None:
    blocks = [Block(page=1, text=document(16)), Block(page=2, text=document(16))]
    chunks = chunk(blocks, 12, 0, WordCounter())
    assert [c.position for c in chunks] == list(range(len(chunks)))
    assert [c.page for c in chunks] == sorted(c.page for c in chunks)
    assert {c.page for c in chunks} == {1, 2}
    assert {c.chunker_version for c in chunks} == {VERSION}


def test_ac_ing_05_text_that_fits_in_one_child_has_itself_as_parent() -> None:
    only = chunk([Block(page=1, text=sentence(0))], 12, 0, WordCounter())[0]
    assert only.parent_text == sentence(0)


def test_ac_ing_05_other_chunkers_leave_parent_text_empty() -> None:
    from docdesk.ingestion.chunkers import fixed

    assert (
        fixed.chunk([Block(page=1, text=sentence(0))], 12, 0, WordCounter())[0].parent_text is None
    )


def test_ac_ing_05_no_blocks_gives_no_chunks() -> None:
    assert chunk([], 12, 0, WordCounter()) == []


@pytest.mark.parametrize(("size", "overlap"), [(0, 0), (10, 10), (10, -1)])
def test_ac_ing_05_bad_size_or_overlap_is_refused(size: int, overlap: int) -> None:
    with pytest.raises(ValueError, match="overlap"):
        chunk([Block(page=1, text="Some text.")], size, overlap, WordCounter())
