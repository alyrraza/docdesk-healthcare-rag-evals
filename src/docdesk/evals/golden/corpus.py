"""Where the golden loader gets document ids, cleaned text and chunks: the real database."""

from __future__ import annotations

import uuid
from typing import Protocol

from sqlalchemy import select
from sqlalchemy.orm import Session

from docdesk.db.models.chunks import ChunkRow
from docdesk.db.models.documents import DocumentRow
from docdesk.evals.golden.evidence import cleaned_document_text
from docdesk.ingestion.pipeline import FileStore


class GoldenCorpus(Protocol):
    """What resolving evidence needs, so tests can use a small fake."""

    def document_id(self, source: str) -> uuid.UUID | None:
        """Id of the document with this stable source key, or None."""
        ...

    def cleaned_text(self, document_id: uuid.UUID) -> str:
        """The document text as ingestion cleaned it."""
        ...

    def chunks(self, document_id: uuid.UUID) -> list[tuple[str, str]]:
        """The stored chunks as (id, text), in document order."""
        ...


class DatabaseCorpus:
    """Reads the live corpus: ids and chunks from the database, text from the file store."""

    def __init__(self, session: Session, store: FileStore) -> None:
        self._session = session
        self._store = store

    def document_id(self, source: str) -> uuid.UUID | None:
        """Look a document up by its seed key, which is stable across re-ingests."""
        query = select(DocumentRow.id).where(DocumentRow.source == source)
        return self._session.execute(query).scalar_one_or_none()

    def cleaned_text(self, document_id: uuid.UUID) -> str:
        """Re-parse and re-clean the stored file, so quotes are checked against current rules."""
        return cleaned_document_text(self._store.read(document_id))

    def chunks(self, document_id: uuid.UUID) -> list[tuple[str, str]]:
        """Chunks in position order, which is the order locate_chunks relies on."""
        query = (
            select(ChunkRow.id, ChunkRow.text)
            .where(ChunkRow.document_id == document_id)
            .order_by(ChunkRow.position)
        )
        return [(str(chunk_id), text) for chunk_id, text in self._session.execute(query)]
