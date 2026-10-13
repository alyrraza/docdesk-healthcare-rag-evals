"""Sentence splitting, the one boundary rule every chunker shares."""

from __future__ import annotations

import re

PARAGRAPH_BREAK = re.compile(r"\n\s*\n")
# End mark, whitespace, then a capital letter, digit or opening quote. A lowercase word after
# a period ("e.g. water") or no space ("2.5 mg") is not a boundary. Known limit: "Dr. Smith"
# and "No. 5" still split; this is a cheap rule, not a language model.
SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z0-9\"'(\[])")


def split_sentences(text: str) -> list[str]:
    """Split text into sentences so chunks can break between them instead of inside them."""
    sentences = []
    for paragraph in PARAGRAPH_BREAK.split(text):
        flat = " ".join(paragraph.split())
        sentences.extend(part for part in SENTENCE_END.split(flat) if part)
    return sentences
