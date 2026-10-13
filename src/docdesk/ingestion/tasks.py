"""The Celery task: a thin wrapper that builds the worker's dependencies and runs the pipeline."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from celery import shared_task
from sqlalchemy.orm import Session, sessionmaker

from docdesk.core.config import get_settings
from docdesk.db.session import default_session_factory
from docdesk.embeddings.encoder import Encoder
from docdesk.embeddings.tokenizer import TokenCounter
from docdesk.ingestion.filestore import LocalFileStore
from docdesk.ingestion.pipeline import FileStore, IngestConfig, TextEncoder, ingest_document
from docdesk.ingestion.types import TokenCounting


@dataclass(frozen=True)
class WorkerDeps:
    """Everything a job needs, built once per worker process because loading the model is slow."""

    session_factory: sessionmaker[Session]
    store: FileStore
    encoder: TextEncoder
    counter: TokenCounting
    config: IngestConfig


@lru_cache
def get_deps() -> WorkerDeps:
    """Build the real database, file store and model from settings on first use."""
    settings = get_settings()
    model_dir = Path(settings.model_dir)
    return WorkerDeps(
        session_factory=default_session_factory(),
        store=LocalFileStore(Path(settings.upload_dir)),
        encoder=Encoder.from_directory(model_dir),
        counter=TokenCounter.from_file(model_dir / "tokenizer.json"),
        config=IngestConfig(),
    )


@shared_task(name="docdesk.ingest_document")
def ingest_document_task(document_id: str) -> str:
    """Run one ingestion; errors propagate so Celery records the job as failed (AC-ING-03)."""
    deps = get_deps()
    with deps.session_factory() as session:
        document = ingest_document(
            session, uuid.UUID(document_id), deps.store, deps.encoder, deps.counter, deps.config
        )
    return document.status.value
