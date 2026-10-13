"""Ingestion is all or nothing: ready with chunks, or failed with a reason and none."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from docdesk.db.models.chunks import ChunkRow
from docdesk.db.models.documents import DocumentStatus
from docdesk.db.repositories.documents import Document, DocumentRepository
from docdesk.ingestion.errors import ParseError
from docdesk.ingestion.pipeline import IngestConfig, ingest_document
from fakes.ingestion import FakeEncoder, FakeStore, WordCounter

pytestmark = pytest.mark.integration

CONFIG = IngestConfig(chunker="fixed", size=20, overlap=0)
TEXT = " ".join(f"Sentence{n} has exactly six words here." for n in range(12)).encode()


def chunk_count(session: Session) -> int:
    return session.execute(select(func.count()).select_from(ChunkRow)).scalar_one()


def run(
    session: Session,
    document: Document,
    store: FakeStore,
    encoder: FakeEncoder | None = None,
    config: IngestConfig = CONFIG,
) -> Document:
    return ingest_document(
        session, document.id, store, encoder or FakeEncoder(), WordCounter(), config
    )


def test_ac_ing_02_a_good_file_becomes_ready_with_its_chunk_count(
    pipeline_session, store, make_document
) -> None:
    result = run(pipeline_session, make_document(TEXT), store)
    stored = pipeline_session.execute(select(ChunkRow)).scalars().all()
    assert result.status == DocumentStatus.READY
    assert result.chunk_count == len(stored) > 1


def test_ac_ing_05_every_chunk_records_position_tokens_and_versions(
    pipeline_session, store, make_document
) -> None:
    document = make_document(TEXT)
    run(pipeline_session, document, store)
    query = select(ChunkRow).order_by(ChunkRow.position)
    rows = pipeline_session.execute(query).scalars().all()
    assert [row.position for row in rows] == list(range(len(rows)))
    assert all(row.document_id == document.id for row in rows)
    assert all(0 < row.token_count <= 20 for row in rows)
    assert {row.chunker_version for row in rows} == {"fixed-v1"}
    assert {row.embed_model_version for row in rows} == {"fake-model@rev1"}


def test_ac_ing_03_a_file_with_no_text_fails_with_its_reason_and_no_chunks(
    pipeline_session, store, make_document
) -> None:
    document = make_document(b"   \n ")
    with pytest.raises(ParseError):
        run(pipeline_session, document, store)
    saved = DocumentRepository(pipeline_session).get(document.id)
    assert saved.status == DocumentStatus.FAILED
    assert saved.fail_reason == "file contains no text"
    assert chunk_count(pipeline_session) == 0


def test_ac_ing_03_a_model_crash_fails_the_document_without_leaking_details(
    pipeline_session, store, make_document
) -> None:
    document = make_document(TEXT)
    with pytest.raises(RuntimeError):
        run(pipeline_session, document, store, FakeEncoder(fail=True))
    saved = DocumentRepository(pipeline_session).get(document.id)
    assert saved.status == DocumentStatus.FAILED
    assert "secret" not in saved.fail_reason
    assert "RuntimeError" in saved.fail_reason
    assert chunk_count(pipeline_session) == 0


def test_ac_ing_03_a_database_error_on_the_last_chunk_leaves_no_partial_chunks(
    pipeline_session, store, make_document
) -> None:
    document = make_document(TEXT)
    with pytest.raises(Exception, match="(?i)nan"):
        run(pipeline_session, document, store, FakeEncoder(nan_in_last_row=True))
    saved = DocumentRepository(pipeline_session).get(document.id)
    assert saved.status == DocumentStatus.FAILED
    assert chunk_count(pipeline_session) == 0


def test_ac_ing_04_ingesting_a_ready_document_again_adds_no_chunks(
    pipeline_session, store, make_document
) -> None:
    document = make_document(TEXT)
    first = run(pipeline_session, document, store)
    run(pipeline_session, document, store)
    assert chunk_count(pipeline_session) == first.chunk_count


def test_ac_ing_03_a_failed_document_can_be_retried_and_becomes_ready(
    pipeline_session, store, make_document
) -> None:
    document = make_document(TEXT)
    with pytest.raises(RuntimeError):
        run(pipeline_session, document, store, FakeEncoder(fail=True))
    result = run(pipeline_session, document, store)
    assert result.status == DocumentStatus.READY
    assert result.fail_reason is None


def test_ac_ing_05_a_chunk_size_the_model_would_truncate_is_refused_up_front(
    pipeline_session, store, make_document
) -> None:
    document = make_document(TEXT)
    too_big = IngestConfig(chunker="fixed", size=300, overlap=0)
    with pytest.raises(ValueError, match="256"):
        run(pipeline_session, document, store, config=too_big)
    saved = DocumentRepository(pipeline_session).get(document.id)
    assert saved.status == DocumentStatus.QUEUED


def test_ac_ing_03_an_unknown_document_id_is_an_error(pipeline_session, store) -> None:
    with pytest.raises(LookupError):
        ingest_document(pipeline_session, uuid.uuid4(), store, FakeEncoder(), WordCounter(), CONFIG)
