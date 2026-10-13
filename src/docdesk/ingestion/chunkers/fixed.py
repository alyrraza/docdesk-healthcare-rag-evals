"""Fixed size chunker: pack whole sentences up to a token budget, with sentence overlap."""

from __future__ import annotations

from docdesk.ingestion.sentences import split_sentences
from docdesk.ingestion.types import Block, Chunk, TokenCounting

VERSION = "fixed-v1"


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


def sentence_units(text: str, size: int, counter: TokenCounting) -> list[str]:
    """List the sentences of a page, cutting any single sentence that alone exceeds the limit."""
    units: list[str] = []
    for sentence in split_sentences(text):
        if counter.count(sentence) > size:
            units.extend(cut_long_text(sentence, size, counter))
        else:
            units.append(sentence)
    return units


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


def chunk(blocks: list[Block], size: int, overlap: int, counter: TokenCounting) -> list[Chunk]:
    """Split each page into chunks of at most `size` tokens, never mixing two pages."""
    if size <= 0 or not 0 <= overlap < size:
        raise ValueError(
            f"need size > 0 and 0 <= overlap < size, got size={size} overlap={overlap}"
        )
    chunks: list[Chunk] = []
    for block in blocks:
        for text in pack(sentence_units(block.text, size, counter), size, overlap, counter):
            chunks.append(Chunk(len(chunks), block.page, text, counter.count(text), VERSION))
    return chunks
