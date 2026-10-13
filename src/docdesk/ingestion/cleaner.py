"""Cleans extracted text: repeated page headers and footers, split words and stray whitespace."""

from __future__ import annotations

import re
from collections import Counter
from math import ceil

from docdesk.ingestion.types import Block

# Fewer pages than this and a repeated line could be real content, so nothing is removed.
MIN_PAGES_FOR_HEADER_REMOVAL = 3
SPACES = re.compile(r"[ \t\u00a0]+")
HYPHEN_BREAK = re.compile(r"(\w)-\n(?=[a-z])")
BLANK_RUNS = re.compile(r"\n{3,}")


def line_key(line: str) -> str:
    """Make 'Page 3 of 9' and 'Page 4 of 9' compare equal by masking digits."""
    return re.sub(r"\d+", "#", " ".join(line.split()).lower())


def edge_lines(text: str) -> set[str]:
    """Return the keys of the first and last non-empty lines, where headers and footers sit."""
    lines = [line for line in text.split("\n") if line.strip()]
    return {line_key(lines[0]), line_key(lines[-1])} if lines else set()


def find_repeated_edges(blocks: list[Block]) -> set[str]:
    """Find edge lines repeated on at least half the pages, which marks them as page furniture."""
    if len(blocks) < MIN_PAGES_FOR_HEADER_REMOVAL:
        return set()
    seen = Counter(key for block in blocks for key in edge_lines(block.text))
    needed = max(MIN_PAGES_FOR_HEADER_REMOVAL, ceil(len(blocks) / 2))
    return {key for key, pages in seen.items() if pages >= needed}


def strip_edges(text: str, repeated: set[str]) -> str:
    """Drop the first and last non-empty lines of a page when they are known page furniture."""
    lines = text.split("\n")
    filled = [index for index, line in enumerate(lines) if line.strip()]
    drop = {index for index in (filled[:1] + filled[-1:]) if line_key(lines[index]) in repeated}
    return "\n".join(line for index, line in enumerate(lines) if index not in drop)


def normalize_whitespace(text: str) -> str:
    """Collapse spaces, trim each line and keep at most one blank line between paragraphs."""
    lines = (SPACES.sub(" ", line).strip() for line in text.split("\n"))
    return BLANK_RUNS.sub("\n\n", "\n".join(lines)).strip()


def clean(blocks: list[Block]) -> list[Block]:
    """Make extracted text uniform so noise cannot distort chunk boundaries or embeddings."""
    repeated = find_repeated_edges(blocks)
    cleaned = []
    for block in blocks:
        text = strip_edges(block.text, repeated)
        text = HYPHEN_BREAK.sub(r"\1", text)
        text = normalize_whitespace(text)
        if text:
            cleaned.append(Block(page=block.page, text=text))
    return cleaned
