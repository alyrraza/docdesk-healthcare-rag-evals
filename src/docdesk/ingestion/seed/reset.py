"""Remove the seed corpus so the normal ingest can rebuild it with another chunking config."""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from docdesk.db.models.chunks import ChunkRow
from docdesk.db.models.documents import DocumentRow

SEED_PREFIX = "seed:"


@dataclass(frozen=True)
class ClearedCounts:
    """How much was removed, so the script can report it."""

    documents: int
    chunks: int


def clear_seed_corpus(session: Session) -> ClearedCounts:
    """Delete seed documents and their chunks; uploads stay, and duplicate detection stays on."""
    seed = DocumentRow.source.like(f"{SEED_PREFIX}%")
    chunks = session.execute(
        select(func.count())
        .select_from(ChunkRow)
        .join(DocumentRow, ChunkRow.document_id == DocumentRow.id)
        .where(seed)
    ).scalar_one()
    removed = session.execute(delete(DocumentRow).where(seed))  # chunks go by ON DELETE CASCADE
    return ClearedCounts(documents=removed.rowcount, chunks=chunks)
