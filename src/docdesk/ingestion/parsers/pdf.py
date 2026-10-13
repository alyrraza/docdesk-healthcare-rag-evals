"""PDF parser: one block per page that has text. No OCR, so scanned files fail clearly."""

from __future__ import annotations

import io

from pypdf import PdfReader
from pypdf.errors import PyPdfError

from docdesk.ingestion.errors import ParseError
from docdesk.ingestion.types import Block

NO_TEXT = "PDF has no text layer (scanned images need OCR, which is not supported)"


def parse_pdf(data: bytes) -> list[Block]:
    """Extract the text of each page, keeping page numbers so chunks can cite them."""
    try:
        reader = PdfReader(io.BytesIO(data))
        if reader.is_encrypted:
            raise ParseError("PDF is password protected")
        blocks = [
            Block(page=number, text=text)
            for number, page in enumerate(reader.pages, start=1)
            if (text := (page.extract_text() or "").strip())
        ]
    except PyPdfError as error:
        raise ParseError("PDF could not be read, the file may be damaged") from error
    if not blocks:
        raise ParseError(NO_TEXT)
    return blocks
