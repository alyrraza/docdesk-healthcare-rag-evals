"""What B0 retrieval finds for a question, shown to the owner to confirm nothing answers it."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy.orm import Session

from docdesk.retrieval.dense import dense_search
from docdesk.retrieval.keyword import keyword_search
from docdesk.retrieval.retriever import QueryEncoder
from docdesk.retrieval.types import ScoredChunk

PROBE_TOP = 3


@dataclass(frozen=True)
class ProbeChunk:
    """One retrieved chunk reduced to what the owner reads: document, score and text."""

    title: str
    score: float
    text: str


@dataclass(frozen=True)
class Probe:
    """The top chunks of each retrieval leg for one question."""

    dense: list[ProbeChunk]
    keyword: list[ProbeChunk]


def shrink(chunks: list[ScoredChunk]) -> list[ProbeChunk]:
    """Why: the sheet needs the title, score and text only, not ids or timings."""
    return [ProbeChunk(chunk.document_title, chunk.score, chunk.text) for chunk in chunks]


def probe_question(
    session: Session, encoder: QueryEncoder, question: str, user_id: uuid.UUID
) -> Probe:
    """Why: B0 is dense, and keyword search is the leg E3 adds, so the owner sees both."""
    vector = encoder.encode([question])[0]
    dense = dense_search(session, vector, user_id, PROBE_TOP)
    keyword = keyword_search(session, question, user_id, PROBE_TOP)
    return Probe(shrink(dense[:PROBE_TOP]), shrink(keyword[:PROBE_TOP]))


def render_leg(name: str, chunks: list[ProbeChunk]) -> list[str]:
    """One leg of the sheet; dashes become hyphens because the docs style check bans them."""
    if not chunks:
        return [f"- {name} top {PROBE_TOP}: no chunk matched"]
    lines = [f"- {name} top {PROBE_TOP}:"]
    for rank, chunk in enumerate(chunks, start=1):
        text = chunk.text.replace("—", "-").replace("–", "-")
        lines += [f"  {rank}. {chunk.title} (score {chunk.score:.2f})", f"     > {text}"]
    return lines


def render_probe(probe: Probe) -> list[str]:
    """Both legs, dense first, as sheet lines."""
    return [*render_leg("dense", probe.dense), *render_leg("keyword", probe.keyword)]
