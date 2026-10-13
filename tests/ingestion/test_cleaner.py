"""The cleaner removes extraction noise without changing the meaning of the text (AC-ING-02)."""

from __future__ import annotations

from docdesk.ingestion.cleaner import clean
from docdesk.ingestion.types import Block


def one(text: str) -> list[Block]:
    return [Block(page=1, text=text)]


def test_ac_ing_02_runs_of_spaces_and_tabs_become_one_space() -> None:
    assert clean(one("take\t\t two   tablets  "))[0].text == "take two tablets"


def test_ac_ing_02_three_blank_lines_become_one_paragraph_break() -> None:
    assert clean(one("first\n\n\n\n\nsecond"))[0].text == "first\n\nsecond"


def test_ac_ing_02_a_word_split_across_lines_by_a_hyphen_is_joined() -> None:
    assert clean(one("the treat-\nment works"))[0].text == "the treatment works"


def test_ac_ing_02_a_real_hyphen_before_a_capital_or_digit_is_kept() -> None:
    assert clean(one("non-\nHodgkin and COVID-\n19"))[0].text == "non-\nHodgkin and COVID-\n19"


def test_ac_ing_02_a_dash_between_words_on_one_line_is_untouched() -> None:
    assert clean(one("well-known drug"))[0].text == "well-known drug"


def pages(count: int) -> list[Block]:
    """Pages that each carry the same header and a footer whose number changes."""
    return [
        Block(page=n, text=f"ACME DRUG LABEL\nBody text of page {n}.\nPage {n} of 9")
        for n in range(1, count + 1)
    ]


def test_ac_ing_02_a_header_and_numbered_footer_repeated_on_every_page_are_removed() -> None:
    cleaned = clean(pages(4))
    assert [block.text for block in cleaned] == [f"Body text of page {n}." for n in range(1, 5)]


def test_ac_ing_02_page_numbers_are_kept_on_the_block_for_citations() -> None:
    assert [block.page for block in clean(pages(4))] == [1, 2, 3, 4]


def test_ac_ing_02_a_line_that_appears_on_only_one_page_is_kept() -> None:
    blocks = pages(4)
    blocks[1] = Block(page=2, text="WARNING: do not crush\nBody text of page 2.\nPage 2 of 9")
    assert clean(blocks)[1].text == "WARNING: do not crush\nBody text of page 2."


def test_ac_ing_02_two_page_documents_are_not_stripped_of_repeated_lines() -> None:
    """With too few pages a repeat could be real content, so nothing is removed."""
    assert [block.text for block in clean(pages(2))] == [block.text for block in pages(2)]


def test_ac_ing_02_a_block_that_becomes_empty_is_dropped() -> None:
    blocks = pages(3) + [Block(page=4, text="ACME DRUG LABEL\nPage 4 of 9")]
    assert [block.page for block in clean(blocks)] == [1, 2, 3]


def test_ac_ing_02_empty_input_gives_empty_output() -> None:
    assert clean([]) == []
