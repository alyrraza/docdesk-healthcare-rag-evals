"""Transactional ingest: store all of a document's chunks or none (AC-ING-02, AC-ING-03)."""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Protocol

import numpy as np
from sqlalchemy.orm import Session

from docdesk.db.models.chunks import ChunkRow
from docdesk.db.models.documents import DocumentStatus
from docdesk.db.repositories.documents import Document, DocumentRepository
from docdesk.ingestion.chunkers.registry import get_chunker
from docdesk.ingestion.cleaner import clean
from docdesk.ingestion.errors import ParseError
from docdesk.ingestion.parsers.dispatch import parse_document
from docdesk.ingestion.types import Chunk, TokenCounting

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class IngestConfig:
    """Chunking choices, kept in one object so experiments can vary them without code changes."""

    chunker: str = "fixed"
    size: int = 200
    overlap: int = 40


class FileStore(Protocol):
    """Where uploaded bytes live; the real store arrives with the upload route (T048)."""

    def read(self, document_id: uuid.UUID) -> bytes:
        """Return the original bytes of an uploaded document."""
        ...


class TextEncoder(Protocol):
    """The part of the encoder the pipeline needs, so tests can pass a fake."""

    model_name: str
    revision: str
    max_length: int

    def encode(self, texts: list[str]) -> np.ndarray:
        """Return one vector per text."""
        ...


def check_config(config: IngestConfig, encoder: TextEncoder) -> None:
    """Refuse settings that would quietly lose data, before any document is touched."""
    if config.size > encoder.max_length:
        raise ValueError(
            f"chunk size {config.size} is above the model limit of {encoder.max_length} tokens, "
            "the end of each chunk would be cut off when embedding"
        )
    if config.chunker == "parent_child":
        raise ValueError("parent_child needs a parent text column that the chunks table lacks")
    get_chunker(config.chunker)


def build_chunks(data: bytes, config: IngestConfig, counter: TokenCounting) -> list[Chunk]:
    """Turn raw bytes into chunks, or fail with a reason the user can read."""
    blocks = clean(parse_document(data))
    chunks = get_chunker(config.chunker)(blocks, config.size, config.overlap, counter)
    if not chunks:
        raise ParseError("document produced no chunks")
    return chunks


def to_rows(
    document_id: uuid.UUID, chunks: list[Chunk], vectors: np.ndarray, model_version: str
) -> list[ChunkRow]:
    """Pair every chunk with its vector and the versions AC-ING-05 requires."""
    if len(vectors) != len(chunks):
        raise ValueError(f"encoder returned {len(vectors)} vectors for {len(chunks)} chunks")
    return [
        ChunkRow(
            document_id=document_id,
            position=chunk.position,
            text=chunk.text,
            token_count=chunk.token_count,
            page=chunk.page,
            embedding=vector.tolist(),
            chunker_version=chunk.chunker_version,
            embed_model_version=model_version,
        )
        for chunk, vector in zip(chunks, vectors, strict=True)
    ]


def failure_reason(error: Exception) -> str:
    """Give users a safe reason: parse errors are written for them, anything else is only a type."""
    if isinstance(error, ParseError):
        return error.reason
    return f"unexpected error ({type(error).__name__}), see the server log"


def ingest_document(
    session: Session,
    document_id: uuid.UUID,
    store: FileStore,
    encoder: TextEncoder,
    counter: TokenCounting,
    config: IngestConfig | None = None,
) -> Document:
    """Ingest one document so it ends up ready with all its chunks, or failed with none."""
    config = config or IngestConfig()
    check_config(config, encoder)
    repo = DocumentRepository(session)
    document = repo.get(document_id)
    if document is None:
        raise LookupError(f"document {document_id} not found")
    if document.status == DocumentStatus.READY:
        return document
    repo.set_status(document_id, DocumentStatus.PROCESSING)
    session.commit()
    try:
        chunks = build_chunks(store.read(document_id), config, counter)
        vectors = encoder.encode([chunk.text for chunk in chunks])
        model_version = f"{encoder.model_name}@{encoder.revision}"
        with session.begin_nested():
            session.add_all(to_rows(document_id, chunks, vectors, model_version))
        ready = repo.set_status(document_id, DocumentStatus.READY, chunk_count=len(chunks))
        session.commit()
        return ready
    except Exception as error:
        session.rollback()
        repo.set_status(document_id, DocumentStatus.FAILED, fail_reason=failure_reason(error))
        session.commit()
        logger.exception("ingestion failed for document %s", document_id)
        raise
