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
# A concrete claim here is a dose (a number with a mass, volume or percent unit) or a schedule
# ("every 3 months"). Bare ages and durations are left out: they read oddly out of context.
CONCRETE = re.compile(
    r"\b\d+(?:\.\d+)?\s*(?:mg|mcg|g|ml|%)(?![a-z])"
    r"|\bevery\s+\d+\s+(?:hours?|days?|weeks?|months?)\b",
    re.IGNORECASE)
# A sentence that points at something outside itself does not read as a standalone claim.
CROSS_REFERENCE = re.compile(
    r"\(see|\bsee\b|\[|\btable\b|\bfigure\b|\b(?:this|these|those|such|above|below|following)\b"
    r"|\b(?:trials?|stud(?:y|ies))\b", re.IGNORECASE)
# A heading run into the text shows as a word in capitals, which is case sensitive on purpose.
HEADING_WORD = re.compile(r"\b[A-Z]{4,}\b")
# Table symbols and dotted abbreviations such as b.i.d. mean the text came from a table.
TABLE_TEXT = re.compile(r"[<>=±]|\b[a-z]\.[a-z]\.")
MIN_LENGTH, MAX_LENGTH = 30, 200
MAX_CAPITALISED = 2


def split_sentences(text: str) -> list[str]:
    """Why: omission and insertion both need the answer as sentences, split the same way."""
    sentences: list[str] = []
    for line in text.splitlines():
        sentences += [part.strip() for part in SENTENCE_END.split(line) if part.strip()]
    return sentences


def keep_first_sentence(answer: str) -> str:
    """Why: an omission output must lose content while staying a clean, true answer."""
    return split_sentences(answer)[0]


def reads_cleanly(sentence: str) -> bool:
    """Why: a cut off bracket or a run of capitalised words shows the text came from a heading."""
    capitalised = [word for word in sentence.split()[1:] if word[0].isupper()]
    return sentence.count("(") == sentence.count(")") and len(capitalised) <= MAX_CAPITALISED


def insertion_sentences(chunk_text: str, drug: str) -> list[str]:
    """Why: only a short, self-contained sentence with a concrete claim reads as an answer part."""
    found = []
    for sentence in split_sentences(chunk_text):
        if not MIN_LENGTH <= len(sentence) <= MAX_LENGTH:
            continue
        if not sentence.startswith(STARTERS) or not CONCRETE.search(sentence):
            continue
        if not sentence.endswith((".", "!", "?")) or TABLE_TEXT.search(sentence):
            continue
        if not reads_cleanly(sentence) or HEADING_WORD.search(sentence):
            continue
        if CROSS_REFERENCE.search(sentence):
            continue
        if drug.lower() in sentence.lower():
            continue
        found.append(sentence)
    return found


def add_insertion(answer: str, sentence: str) -> str:
    """Why: the unsupported claim is appended with the same neutral wording every time."""
    base = answer.rstrip()
    if base[-1] not in ".!?":
        base += "."
    return f"{base} {CONNECTOR}{sentence[0].lower()}{sentence[1:]}"
