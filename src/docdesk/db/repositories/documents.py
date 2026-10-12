"""Reads and writes for the documents table."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from docdesk.core import clock
from docdesk.db.models.documents import DocumentRow, DocumentStatus


class DuplicateDocumentError(Exception):
    """Raised when this owner already has a document with the same content hash."""


@dataclass(frozen=True)
class Document:
    """A document as plain data."""

    id: uuid.UUID
    owner_id: uuid.UUID
    title: str
    source: str
    content_hash: str
    status: DocumentStatus
    fail_reason: str | None
    chunk_count: int
    is_shared: bool
    created_at: datetime


def to_document(row: DocumentRow) -> Document:
    """Convert a table row to the dataclass the rest of the app uses."""
    return Document(
        id=row.id,
        owner_id=row.owner_id,
        title=row.title,
        source=row.source,
        content_hash=row.content_hash,
        status=DocumentStatus(row.status),
        fail_reason=row.fail_reason,
        chunk_count=row.chunk_count,
        is_shared=row.is_shared,
        created_at=row.created_at,
    )


class DocumentRepository:
    """All document queries live here."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def add(
        self,
        owner_id: uuid.UUID,
        title: str,
        source: str,
        content_hash: str,
        is_shared: bool = False,
    ) -> Document:
        """Insert a queued document; the unique key stops the same content twice per owner."""
        row = DocumentRow(
            owner_id=owner_id,
            title=title,
            source=source,
            content_hash=content_hash,
            status=DocumentStatus.QUEUED.value,
            chunk_count=0,
            is_shared=is_shared,
            created_at=clock.utc_now(),
        )
        try:
            with self._session.begin_nested():
                self._session.add(row)
        except IntegrityError as error:
            raise DuplicateDocumentError(content_hash) from error
        return to_document(row)

    def get(self, document_id: uuid.UUID) -> Document | None:
        """Fetch one document by id."""
        row = self._session.get(DocumentRow, document_id)
        return to_document(row) if row else None

    def find_by_hash(self, owner_id: uuid.UUID, content_hash: str) -> Document | None:
        """Find an earlier upload of the same content so the caller can skip re-ingesting."""
        query = select(DocumentRow).where(
            DocumentRow.owner_id == owner_id, DocumentRow.content_hash == content_hash
        )
        row = self._session.execute(query).scalar_one_or_none()
        return to_document(row) if row else None

    def set_status(
        self,
        document_id: uuid.UUID,
        status: DocumentStatus,
        fail_reason: str | None = None,
        chunk_count: int | None = None,
    ) -> Document:
        """Move a document through ingestion, recording why it failed or how many chunks it has."""
        row = self._session.get(DocumentRow, document_id)
        if row is None:
            raise LookupError(f"document {document_id} not found")
        row.status = status.value
        row.fail_reason = fail_reason
        if chunk_count is not None:
            row.chunk_count = chunk_count
        self._session.flush()
        return to_document(row)

    def list_visible(self, user_id: uuid.UUID) -> list[Document]:
        """List the user's own documents plus shared corpus documents, newest first."""
        query = (
            select(DocumentRow)
            .where(or_(DocumentRow.owner_id == user_id, DocumentRow.is_shared.is_(True)))
            .order_by(DocumentRow.created_at.desc())
        )
        return [to_document(row) for row in self._session.execute(query).scalars()]
