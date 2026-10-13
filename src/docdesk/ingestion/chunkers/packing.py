"""Shared packing helpers: fill chunks up to a token budget, with overlap made of whole units."""

from __future__ import annotations

from docdesk.ingestion.types import TokenCounting


def cut_long_text(text: str, size: int, counter: TokenCounting) -> list[str]:
    """Cut text that is over the limit into word groups, and cut a giant word by characters."""
    pieces: list[str] = []
    current = ""
    for word in text.split():
        candidate = f"{current} {word}".strip()
        if counter.count(candidate) <= size:
            current = candidate
            continue
        if current:
            pieces.append(current)
        current = word
        while counter.count(current) > size:
            end = len(current) - 1
            while end > 1 and counter.count(current[:end]) > size:
                end -= 1
            pieces.append(current[:end])
            current = current[end:]
    if current:
        pieces.append(current)
    return pieces


def overlap_tail(units: list[str], overlap: int, counter: TokenCounting) -> list[str]:
    """Pick the last whole sentences that fit the overlap budget, always leaving the first out."""
    tail: list[str] = []
    for unit in reversed(units[1:]):
        if counter.count(" ".join([unit, *tail])) > overlap:
            break
        tail.insert(0, unit)
    return tail


def pack(units: list[str], size: int, overlap: int, counter: TokenCounting) -> list[str]:
    """Greedily fill each chunk with sentences, then start the next one from the overlap tail."""
    texts: list[str] = []
    current: list[str] = []
    for unit in units:
        if current and counter.count(" ".join([*current, unit])) > size:
            texts.append(" ".join(current))
            current = overlap_tail(current, overlap, counter)
            while current and counter.count(" ".join([*current, unit])) > size:
                current.pop(0)
        current.append(unit)
    if current:
        texts.append(" ".join(current))
    return texts
