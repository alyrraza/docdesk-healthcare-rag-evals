"""Dense leg: nearest chunks by cosine distance with pgvector (AC-RET-01)."""

from __future__ import annotations

import uuid
from collections.abc import Sequence

from sqlalchemy import select
from sqlalchemy.orm import Session

from docdesk.db.models.chunks import ChunkRow
from docdesk.db.models.documents import DocumentRow
from docdesk.retrieval.access import restrict_to_visible
from docdesk.retrieval.types import ScoredChunk


def dense_search(
    session: Session, query_vector: Sequence[float], user_id: uuid.UUID, top_n: int
) -> list[ScoredChunk]:
    """Find the chunks closest in meaning to the question, so paraphrases still match."""
    distance = ChunkRow.embedding.cosine_distance(list(query_vector)).label("distance")
    query = select(ChunkRow, DocumentRow.title, distance)
    query = restrict_to_visible(query, user_id).order_by(distance, ChunkRow.id).limit(top_n)
    return [
        ScoredChunk(
            chunk_id=chunk.id,
            document_id=chunk.document_id,
            document_title=title,
            text=chunk.text,
            # Cosine similarity is 1 minus the distance, so a bigger score is a better match.
            score=1.0 - float(dist),
            source="dense",
            page=chunk.page,
        )
        for chunk, title, dist in session.execute(query)
    ]
