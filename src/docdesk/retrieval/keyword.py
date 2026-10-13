"""Keyword leg: Postgres full text search, which finds exact terms like drug names (AC-RET-02)."""

from __future__ import annotations

import uuid

from sqlalchemy import Text, cast, func, select
from sqlalchemy.orm import Session

from docdesk.db.models.chunks import ChunkRow
from docdesk.db.models.documents import DocumentRow
from docdesk.retrieval.access import restrict_to_visible
from docdesk.retrieval.types import ScoredChunk


def keyword_search(
    session: Session, question: str, user_id: uuid.UUID, top_n: int
) -> list[ScoredChunk]:
    """Find chunks that contain the question's words, so exact terms are never missed."""
    # websearch_to_tsquery accepts any user text and never raises on punctuation or operators,
    # but it joins words with AND, so one unmatched word of a question would return nothing.
    # Swapping AND for OR keeps every hit and lets ts_rank_cd rank chunks by how many words match.
    all_words = func.websearch_to_tsquery("english", question)
    tsquery = func.to_tsquery("simple", func.replace(cast(all_words, Text), "&", "|"))
    rank = func.ts_rank_cd(ChunkRow.tsv, tsquery).label("rank")
    query = select(ChunkRow, DocumentRow.title, rank).where(ChunkRow.tsv.op("@@")(tsquery))
    query = restrict_to_visible(query, user_id).order_by(rank.desc(), ChunkRow.id).limit(top_n)
    return [
        ScoredChunk(
            chunk_id=chunk.id,
            document_id=chunk.document_id,
            document_title=title,
            text=chunk.text,
            score=float(score),
            source="keyword",
            page=chunk.page,
        )
        for chunk, title, score in session.execute(query)
    ]
