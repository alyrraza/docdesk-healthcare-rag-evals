"""Picks the parser from the file's own bytes, since a file name or mime type can lie."""

from __future__ import annotations

from docdesk.ingestion.parsers.pdf import parse_pdf
from docdesk.ingestion.parsers.text import parse_text
from docdesk.ingestion.types import Block

PDF_MAGIC = b"%PDF-"


def parse_document(data: bytes) -> list[Block]:
    """Turn an uploaded file into page blocks, or fail with a reason the user can read."""
    if data.startswith(PDF_MAGIC):
        return parse_pdf(data)
    return parse_text(data)
