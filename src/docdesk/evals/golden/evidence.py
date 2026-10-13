"""Turn evidence quotes into gold chunks, so a golden item survives any chunking (AC-EVL-01)."""

from __future__ import annotations

from collections.abc import Sequence

from docdesk.ingestion.cleaner import clean
from docdesk.ingestion.parsers.dispatch import parse_document

# A chunk is gold for a quote when it overlaps at least this share of the quote.
MIN_OVERLAP_SHARE = 0.5

Span = tuple[int, int]


class QuoteNotFound(ValueError):
    """A quote is not in the document text: it was mistyped, or the document or cleaner changed."""


class ChunkNotLocated(ValueError):
    """A stored chunk could not be found in its document, so gold chunks cannot be decided."""


def cleaned_document_text(data: bytes) -> str:
    """Parse and clean exactly as ingestion does, so quotes are checked against what was chunked."""
    return "\n\n".join(block.text for block in clean(parse_document(data)))


def normalize(text: str) -> str:
    """Fold every whitespace run to one space, because chunks join pieces with their own spaces."""
    return " ".join(text.split())


def check_quote(document_text: str, quote: str) -> None:
    """Require a quote to be an exact substring of the cleaned text, so a human can verify it."""
    if quote not in document_text:
        raise QuoteNotFound(f"quote is not an exact substring of the document: {quote!r}")


def quote_spans(document_text: str, quote: str) -> list[Span]:
    """Every place the quote occurs, as character spans in the whitespace folded document."""
    folded, target = normalize(document_text), normalize(quote)
    spans = []
    start = folded.find(target)
    while start != -1:
        spans.append((start, start + len(target)))
        start = folded.find(target, start + 1)
    if not spans:
        raise QuoteNotFound(f"quote is not in the document text: {quote!r}")
    return spans


def locate_chunks(
    document_text: str, chunk_texts: Sequence[str], labels: Sequence[str] | None = None
) -> list[Span]:
    """Find each chunk in the document, in order; chunk starts always move forward."""
    folded = normalize(document_text)
    spans: list[Span] = []
    search_from = 0
    for index, text in enumerate(chunk_texts):
        target = normalize(text)
        start = folded.find(target, search_from)
        if start == -1:
            label = labels[index] if labels else f"#{index}"
            raise ChunkNotLocated(f"chunk {label} was not found in its document text")
        spans.append((start, start + len(target)))
        search_from = start + 1
    return spans


def is_gold(chunk: Span, quote: Span) -> bool:
    """A chunk is gold when it holds the whole quote or at least half of it by position."""
    overlap = min(chunk[1], quote[1]) - max(chunk[0], quote[0])
    return overlap >= MIN_OVERLAP_SHARE * (quote[1] - quote[0]) and overlap > 0


def gold_chunk_ids(document_text: str, quote: str, chunks: Sequence[tuple[str, str]]) -> set[str]:
    """Ids of the chunks (id, text in document order) that count as gold for one quote."""
    occurrences = quote_spans(document_text, quote)
    placed = locate_chunks(document_text, [text for _, text in chunks], [i for i, _ in chunks])
    return {
        chunk_id
        for (chunk_id, _), span in zip(chunks, placed, strict=True)
        if any(is_gold(span, occurrence) for occurrence in occurrences)
    }
