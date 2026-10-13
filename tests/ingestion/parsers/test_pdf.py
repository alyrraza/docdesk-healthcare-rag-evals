"""The PDF parser returns one block per page, or a typed error with a reason (AC-ING-03)."""

from __future__ import annotations

import pytest

from docdesk.ingestion.errors import ParseError
from docdesk.ingestion.parsers.dispatch import parse_document
from docdesk.ingestion.parsers.pdf import parse_pdf
from docdesk.ingestion.types import Block
from fakes.pdfs import make_blank_pdf, make_encrypted_pdf, make_text_pdf


def test_ac_ing_05_each_page_becomes_a_block_with_its_page_number() -> None:
    blocks = parse_pdf(make_text_pdf(["Aspirin lowers fever", "Take with food"]))
    assert blocks == [Block(1, "Aspirin lowers fever"), Block(2, "Take with food")]


def test_ac_ing_03_pages_without_text_are_skipped_but_keep_the_other_numbers() -> None:
    blocks = parse_pdf(make_text_pdf(["First page", "   ", "Third page"]))
    assert [block.page for block in blocks] == [1, 3]


def test_ac_ing_03_a_pdf_with_no_text_layer_fails_and_says_ocr_is_not_supported() -> None:
    with pytest.raises(ParseError, match="no text layer.*OCR"):
        parse_pdf(make_blank_pdf(pages=2))


def test_ac_ing_03_a_password_protected_pdf_fails_with_a_reason() -> None:
    with pytest.raises(ParseError, match="password"):
        parse_pdf(make_encrypted_pdf())


def test_ac_ing_03_a_corrupt_pdf_fails_with_a_reason_not_a_crash() -> None:
    with pytest.raises(ParseError, match="could not be read"):
        parse_pdf(b"%PDF-1.4\nthis is not really a pdf")


def test_ac_ing_03_a_pdf_with_zero_pages_fails() -> None:
    with pytest.raises(ParseError, match="no text layer"):
        parse_pdf(make_blank_pdf(pages=0))


def test_ac_ing_03_dispatch_sends_pdf_bytes_to_the_pdf_parser() -> None:
    assert parse_document(make_text_pdf(["Hello page"])) == [Block(1, "Hello page")]
