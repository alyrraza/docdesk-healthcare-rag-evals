"""Accepting an upload: dedupe by content, store the file, queue the job (AC-ING-01, AC-ING-04)."""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable
from typing import Protocol

from sqlalchemy.orm import Session

from docdesk.core.errors import AppError
from docdesk.db.models.documents import DocumentStatus
from docdesk.db.repositories.documents import Document, DocumentRepository, DuplicateDocumentError
from docdesk.ingestion.hashing import content_hash

logger = logging.getLogger(__name__)

Enqueue = Callable[[uuid.UUID], None]


class Saver(Protocol):
    """The write side of the file store."""

    def save(self, document_id: uuid.UUID, data: bytes) -> None:
        """Keep the uploaded bytes for the worker."""
        ...


def queue_job(
    session: Session, repo: DocumentRepository, enqueue: Enqueue, doc_id: uuid.UUID
) -> None:
    """Send the job, and if the queue is down mark the document failed so it is not stuck."""
    try:
        enqueue(doc_id)
    except Exception as error:
        logger.exception("could not queue ingestion for document %s", doc_id)
        reason = "could not queue the job, please upload the file again"
        repo.set_status(doc_id, DocumentStatus.FAILED, fail_reason=reason)
        session.commit()
        raise AppError("queue_unavailable", "Processing is unavailable, try again", 503) from error


def find_or_create(
    repo: DocumentRepository, owner_id: uuid.UUID, title: str, digest: str
) -> tuple[Document, bool]:
    """Return (document, already_existed); the unique key settles two uploads racing each other."""
    existing = repo.find_by_hash(owner_id, digest)
    if existing is not None:
        return existing, True
    try:
        return repo.add(owner_id, title, "upload", digest), False
    except DuplicateDocumentError:
        winner = repo.find_by_hash(owner_id, digest)
        if winner is None:
            raise
        return winner, True


def submit_document(
    session: Session,
    store: Saver,
    enqueue: Enqueue,
    owner_id: uuid.UUID,
    title: str,
    data: bytes,
) -> tuple[Document, bool]:
    """Accept an upload and return (document, is_duplicate) without waiting for embedding."""
    if not data:
        raise AppError("empty_file", "The uploaded file is empty", 422)
    repo = DocumentRepository(session)
    document, existed = find_or_create(repo, owner_id, title, content_hash(data))
    if existed:
        if document.status != DocumentStatus.FAILED:
            return document, True
        document = repo.set_status(document.id, DocumentStatus.QUEUED)  # a failed file may retry
    store.save(document.id, data)
    session.commit()
    queue_job(session, repo, enqueue, document.id)
    return document, False


def list_documents(session: Session, user_id: uuid.UUID) -> list[Document]:
    """List what this user may see: their own documents and the shared corpus."""
    return DocumentRepository(session).list_visible(user_id)


def get_visible_document(session: Session, user_id: uuid.UUID, document_id: uuid.UUID) -> Document:
    """Fetch one document, answering 404 for another user's private one so it is not revealed."""
    document = DocumentRepository(session).get(document_id)
    if document is None or not (document.owner_id == user_id or document.is_shared):
        raise AppError("not_found", "Document not found", 404)
    return document
