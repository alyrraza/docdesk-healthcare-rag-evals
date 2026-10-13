"""Load downloaded corpus files as shared documents owned by the admin, then ingest them."""

from __future__ import annotations

import logging
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from sqlalchemy.orm import Session, sessionmaker

from docdesk.db.repositories.documents import Document, DocumentRepository
from docdesk.ingestion.errors import ParseError
from docdesk.ingestion.hashing import content_hash
from docdesk.ingestion.pipeline import (
    FileStore,
    IngestConfig,
    TextEncoder,
    build_chunks,
    check_config,
    failure_reason,
    ingest_document,
)
from docdesk.ingestion.seed.common import load_manifest
from docdesk.ingestion.types import TokenCounting

logger = logging.getLogger(__name__)


class SavingStore(FileStore):
    """A file store that can also write, which registering a corpus needs."""

    def save(self, document_id: uuid.UUID, data: bytes) -> None:
        """Keep the original bytes for the ingest step."""
        ...


@dataclass
class IngestSummary:
    """How a bulk ingest went, so a failure is reported instead of lost in the log."""

    ready: int = 0
    failed: list[tuple[uuid.UUID, str]] = field(default_factory=list)


def register_corpus(
    session: Session, store: SavingStore, directories: list[Path], admin_id: uuid.UUID
) -> list[Document]:
    """Create a queued, shared document per downloaded file that is not already registered."""
    repo = DocumentRepository(session)
    created = []
    for directory in directories:
        if not directory.is_dir():
            raise FileNotFoundError(
                f"corpus folder {directory} not found, run scripts/fetch_{directory.name}.py first"
            )
        for source_id, entry in load_manifest(directory).items():
            data = (directory / entry["file"]).read_bytes()
            digest = content_hash(data)
            if repo.find_by_hash(admin_id, digest) is not None:
                continue
            # One key per document, so golden items can name it and it survives a re-ingest.
            source = f"seed:{directory.name}:{source_id}"
            document = repo.add(admin_id, entry["title"], source, digest, is_shared=True)
            store.save(document.id, data)
            session.commit()
            created.append(document)
    return created


def ingest_all(
    session_factory: sessionmaker[Session],
    store: FileStore,
    encoder: TextEncoder,
    counter: TokenCounting,
    document_ids: list[uuid.UUID],
    config: IngestConfig,
    progress: Callable[[int, int], None] | None = None,
) -> IngestSummary:
    """Ingest each document in its own session so one bad file cannot stop the rest."""
    summary = IngestSummary()
    for done, document_id in enumerate(document_ids, start=1):
        try:
            with session_factory() as session:
                ingest_document(session, document_id, store, encoder, counter, config)
            summary.ready += 1
        except Exception as error:  # the pipeline already stored the reason and logged it
            summary.failed.append((document_id, failure_reason(error)))
        if progress:
            progress(done, len(document_ids))
    return summary


@dataclass
class DryRunReport:
    """What a bulk ingest would produce, measured without writing anything."""

    documents: int = 0
    chunks: int = 0
    tokens: int = 0
    max_chunk_tokens: int = 0
    failed: list[tuple[str, str]] = field(default_factory=list)


def dry_run(
    directories: list[Path], encoder: TextEncoder, counter: TokenCounting, config: IngestConfig
) -> DryRunReport:
    """Parse, chunk and embed every corpus file but store nothing, to check sizes and speed."""
    check_config(config, encoder)
    report = DryRunReport()
    for directory in directories:
        for source_id, entry in load_manifest(directory).items():
            try:
                chunks = build_chunks((directory / entry["file"]).read_bytes(), config, counter)
            except ParseError as error:
                report.failed.append((source_id, error.reason))
                continue
            encoder.encode([chunk.text for chunk in chunks])
            report.documents += 1
            report.chunks += len(chunks)
            report.tokens += sum(chunk.token_count for chunk in chunks)
            report.max_chunk_tokens = max(report.max_chunk_tokens, *(c.token_count for c in chunks))
    return report
