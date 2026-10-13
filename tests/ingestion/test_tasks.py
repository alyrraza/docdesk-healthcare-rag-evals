"""The Celery task is a thin wrapper: build the dependencies, run the pipeline, let errors out."""

from __future__ import annotations

import pytest
from sqlalchemy import select

from docdesk.db.models.chunks import ChunkRow
from docdesk.db.models.documents import DocumentStatus
from docdesk.db.repositories.documents import DocumentRepository
from docdesk.db.session import make_engine, make_session_factory
from docdesk.ingestion import tasks
from docdesk.ingestion.errors import ParseError
from docdesk.ingestion.pipeline import IngestConfig
from fakes.ingestion import FakeEncoder, WordCounter

pytestmark = pytest.mark.integration

TEXT = " ".join(f"Sentence{n} has exactly six words here." for n in range(12)).encode()


@pytest.fixture
def worker_deps(monkeypatch, migrated_url, store):
    """Replace the real model and file store with fakes, but keep the real test database."""
    engine = make_engine(migrated_url)
    deps = tasks.WorkerDeps(
        session_factory=make_session_factory(engine),
        store=store,
        encoder=FakeEncoder(),
        counter=WordCounter(),
        config=IngestConfig(chunker="fixed", size=20, overlap=0),
    )
    monkeypatch.setattr(tasks, "get_deps", lambda: deps)
    yield deps
    engine.dispose()


def test_ac_ing_02_running_the_task_makes_the_document_ready(
    pipeline_session, make_document, worker_deps
) -> None:
    document = make_document(TEXT)
    tasks.ingest_document_task.run(str(document.id))
    pipeline_session.expire_all()
    saved = DocumentRepository(pipeline_session).get(document.id)
    assert saved.status == DocumentStatus.READY
    assert saved.chunk_count == len(pipeline_session.execute(select(ChunkRow)).scalars().all())


def test_ac_ing_03_a_failing_file_raises_so_celery_records_the_failure(
    pipeline_session, make_document, worker_deps
) -> None:
    document = make_document(b"  ")
    with pytest.raises(ParseError):
        tasks.ingest_document_task.run(str(document.id))
    pipeline_session.expire_all()
    assert DocumentRepository(pipeline_session).get(document.id).status == DocumentStatus.FAILED


def test_ac_ing_01_the_task_has_a_stable_public_name() -> None:
    assert tasks.ingest_document_task.name == "docdesk.ingest_document"
