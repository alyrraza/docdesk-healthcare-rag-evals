"""Clearing the seed corpus lets the normal ingest rebuild it, without bypassing duplicates."""

from __future__ import annotations

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from docdesk.db.models.chunks import ChunkRow
from docdesk.db.models.documents import DocumentRow
from docdesk.db.repositories.documents import DocumentRepository
from docdesk.db.repositories.users import UserRepository
from docdesk.ingestion.pipeline import IngestConfig, ingest_document
from docdesk.ingestion.seed.loader import register_corpus
from docdesk.ingestion.seed.reset import clear_seed_corpus
from fakes.ingestion import FakeEncoder, WordCounter
from ingestion.seed.test_loader import TEXT, write_corpus

pytestmark = pytest.mark.integration


def count(session: Session, model: type) -> int:
    return session.execute(select(func.count()).select_from(model)).scalar_one()


@pytest.fixture
def loaded(pipeline_session: Session, tmp_path, store):
    """A seed document with chunks and an upload with chunks, both ingested."""
    admin = UserRepository(pipeline_session).add("reset-admin@example.com", "hash", "admin")
    pipeline_session.commit()
    folder = write_corpus(tmp_path, "openfda", {"a": TEXT})
    seeded = register_corpus(pipeline_session, store, [folder], admin.id)
    upload = DocumentRepository(pipeline_session).add(admin.id, "mine", "upload", "u" * 64)
    store.save(upload.id, TEXT.encode())
    pipeline_session.commit()
    config = IngestConfig(chunker="fixed", size=20, overlap=0)
    for document in [*seeded, upload]:
        ingest_document(pipeline_session, document.id, store, FakeEncoder(), WordCounter(), config)
    return folder, admin.id


def test_t080a_clearing_removes_seed_documents_and_their_chunks_only(
    pipeline_session: Session, loaded
) -> None:
    chunks_before = count(pipeline_session, ChunkRow)
    cleared = clear_seed_corpus(pipeline_session)
    pipeline_session.commit()
    assert cleared.documents == 1
    assert 0 < cleared.chunks < chunks_before
    sources = pipeline_session.execute(select(DocumentRow.source)).scalars().all()
    assert sources == ["upload"]
    assert count(pipeline_session, ChunkRow) == chunks_before - cleared.chunks


def test_t080a_after_clearing_the_normal_registration_creates_the_documents_again(
    pipeline_session: Session, loaded, store
) -> None:
    folder, admin_id = loaded
    assert register_corpus(pipeline_session, store, [folder], admin_id) == []
    clear_seed_corpus(pipeline_session)
    pipeline_session.commit()
    again = register_corpus(pipeline_session, store, [folder], admin_id)
    assert len(again) == 1
