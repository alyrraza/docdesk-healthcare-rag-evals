"""Shared packing helpers: fill chunks up to a token budget, with overlap made of whole units."""

from __future__ import annotations

from docdesk.ingestion.types import TokenCounting


def check_limits(size: int, overlap: int) -> None:
    """Refuse sizes that would make a chunker loop forever or return nothing useful."""
    if size <= 0 or not 0 <= overlap < size:
        raise ValueError(
            f"need size > 0 and 0 <= overlap < size, got size={size} overlap={overlap}"
        )


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


def overlap_tail(
    units: list[str], overlap: int, counter: TokenCounting, joiner: str = " "
) -> list[str]:
    """Pick the last whole sentences that fit the overlap budget, always leaving the first out."""
    tail: list[str] = []
    for unit in reversed(units[1:]):
        if counter.count(joiner.join([unit, *tail])) > overlap:
            break
        tail.insert(0, unit)
    return tail


def pack(
    units: list[str], size: int, overlap: int, counter: TokenCounting, joiner: str = " "
) -> list[str]:
    """Greedily fill each chunk with units, then start the next one from the overlap tail."""
    texts: list[str] = []
    current: list[str] = []
    for unit in units:
        if current and counter.count(joiner.join([*current, unit])) > size:
            texts.append(joiner.join(current))
            current = overlap_tail(current, overlap, counter, joiner)
            while current and counter.count(joiner.join([*current, unit])) > size:
                current.pop(0)
        current.append(unit)
    if current:
        texts.append(joiner.join(current))
    return texts
