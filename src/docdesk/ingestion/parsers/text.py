"""Plain text parser: the whole file is one block on page 1."""

from __future__ import annotations

from docdesk.ingestion.errors import ParseError
from docdesk.ingestion.types import Block


def parse_text(data: bytes) -> list[Block]:
    """Decode an uploaded text file, failing with a reason instead of storing garbage."""
    try:
        text = data.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise ParseError("file is not valid UTF-8 text") from error
    if "\x00" in text:
        raise ParseError("file looks binary (it contains null bytes)")
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if not text.strip():
        raise ParseError("file contains no text")
    return [Block(page=1, text=text)]
