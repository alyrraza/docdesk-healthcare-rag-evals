"""Picks the parser from the file's own bytes, since a file name or mime type can lie."""

from __future__ import annotations

from docdesk.ingestion.errors import ParseError
from docdesk.ingestion.parsers.text import parse_text
from docdesk.ingestion.types import Block

PDF_MAGIC = b"%PDF-"


def parse_document(data: bytes) -> list[Block]:
    """Turn an uploaded file into page blocks, or fail with a reason the user can read."""
    if data.startswith(PDF_MAGIC):
        raise ParseError("PDF files are not supported yet")
    return parse_text(data)
