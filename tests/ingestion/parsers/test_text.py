"""The text parser returns one page of text, or a typed error with a reason (AC-ING-03)."""

from __future__ import annotations

import pytest

from docdesk.ingestion.errors import ParseError
from docdesk.ingestion.parsers.text import parse_text
from docdesk.ingestion.types import Block


def test_ac_ing_03_plain_text_becomes_one_block_on_page_one() -> None:
    assert parse_text(b"Aspirin lowers fever.\nTake with food.") == [
        Block(page=None, text="Aspirin lowers fever.\nTake with food.")
    ]


def test_ac_ing_03_a_utf8_byte_order_mark_is_removed() -> None:
    assert parse_text(b"\xef\xbb\xbfhello")[0].text == "hello"


def test_ac_ing_03_non_ascii_text_is_decoded() -> None:
    assert parse_text("café, naïve, 5 µg".encode())[0].text == "café, naïve, 5 µg"


def test_ac_ing_03_windows_line_endings_become_newlines() -> None:
    assert parse_text(b"one\r\ntwo\rthree")[0].text == "one\ntwo\nthree"


@pytest.mark.parametrize("data", [b"", b"   \n\t  \n"])
def test_ac_ing_03_empty_or_blank_files_fail_with_a_reason(data: bytes) -> None:
    with pytest.raises(ParseError, match="no text"):
        parse_text(data)


def test_ac_ing_03_bytes_that_are_not_utf8_fail_with_a_reason() -> None:
    with pytest.raises(ParseError, match="UTF-8"):
        parse_text(b"\xff\xfe\x00\x01 binary")


def test_ac_ing_03_a_file_with_null_bytes_is_rejected_as_binary() -> None:
    with pytest.raises(ParseError, match="binary"):
        parse_text(b"looks fine\x00but is not")
