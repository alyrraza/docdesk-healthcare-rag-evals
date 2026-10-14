"""Text edits that turn a natural answer into a synthetic calibration output (T099, AC-EVL-07).

Why fixed rules: a synthetic output is only a fair test of the judge if it is built the same way
every time, so every choice here is a plain rule, with no model call and no free text.
"""

from __future__ import annotations

import re

CONNECTOR = "In addition, "
# Sentences that start with one of these still read naturally after the connector once the first
# letter is lowercased. A sentence about a named drug or one that starts with "It" would not.
STARTERS = ("The", "Patients", "Doses", "Dosage", "Treatment", "Adults", "Children", "Pediatric")
SENTENCE_END = re.compile(r"(?<=[.!?])\s+(?=[A-Z\"“\[(])")
# A concrete claim here is a number with a unit: a dose, a schedule, a percentage or a count.
CONCRETE = re.compile(
    r"\b\d+(?:\.\d+)?\s*(?:mg|mcg|g|ml|%|percent|hours?|days?|weeks?|months?|years?)\b",
    re.IGNORECASE)
CROSS_REFERENCE = re.compile(r"\(see|\bsee\b|\[|\btable\b|\bfigure\b", re.IGNORECASE)
MIN_LENGTH, MAX_LENGTH = 30, 200


def split_sentences(text: str) -> list[str]:
    """Why: omission and insertion both need the answer as sentences, split the same way."""
    sentences: list[str] = []
    for line in text.splitlines():
        sentences += [part.strip() for part in SENTENCE_END.split(line) if part.strip()]
    return sentences


def keep_first_sentence(answer: str) -> str:
    """Why: an omission output must lose content while staying a clean, true answer."""
    return split_sentences(answer)[0]


def insertion_sentences(chunk_text: str, drug: str) -> list[str]:
    """Why: only a short, self-contained sentence with a concrete claim reads as an answer part."""
    found = []
    for sentence in split_sentences(chunk_text):
        if not MIN_LENGTH <= len(sentence) <= MAX_LENGTH:
            continue
        if not sentence.startswith(STARTERS) or not CONCRETE.search(sentence):
            continue
        if CROSS_REFERENCE.search(sentence) or drug.lower() in sentence.lower():
            continue
        found.append(sentence)
    return found


def add_insertion(answer: str, sentence: str) -> str:
    """Why: the unsupported claim is appended with the same neutral wording every time."""
    base = answer.rstrip()
    if base[-1] not in ".!?":
        base += "."
    return f"{base} {CONNECTOR}{sentence[0].lower()}{sentence[1:]}"
