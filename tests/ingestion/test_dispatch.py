"""Choosing a parser and a chunker by name or by file content (AC-ING-03)."""

from __future__ import annotations

import pytest

from docdesk.ingestion.chunkers import fixed, parent_child, recursive
from docdesk.ingestion.chunkers.registry import get_chunker
from docdesk.ingestion.errors import ParseError
from docdesk.ingestion.parsers.dispatch import parse_document
from docdesk.ingestion.types import Block


def test_ac_ing_03_plain_bytes_go_to_the_text_parser() -> None:
    assert parse_document(b"Aspirin label") == [Block(page=None, text="Aspirin label")]


def test_ac_ing_03_a_pdf_is_recognised_by_its_header_not_its_file_name() -> None:
    with pytest.raises(ParseError, match="PDF"):
        parse_document(b"%PDF-1.7 rest of the file")


def test_ac_ing_03_a_parse_failure_keeps_its_reason() -> None:
    with pytest.raises(ParseError, match="no text"):
        parse_document(b"")


def test_ac_ing_05_chunkers_are_found_by_name() -> None:
    assert get_chunker("fixed") is fixed.chunk
    assert get_chunker("recursive") is recursive.chunk
    assert get_chunker("parent_child") is parent_child.chunk


def test_ac_ing_05_an_unknown_chunker_name_lists_the_valid_ones() -> None:
    with pytest.raises(ValueError, match="fixed, parent_child, recursive"):
        get_chunker("sliding")
