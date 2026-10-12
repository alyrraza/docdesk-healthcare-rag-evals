"""Tests for the chunks table: vector column, generated tsvector column, cascade."""

from __future__ import annotations

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from docdesk.db.models.chunks import EMBEDDING_DIM, ChunkRow
from docdesk.db.repositories.documents import DocumentRepository
from docdesk.db.repositories.users import UserRepository

pytestmark = pytest.mark.integration


def make_document(session: Session):
    owner = UserRepository(session).add("chunks@example.com", "hash", "user")
    return DocumentRepository(session).add(owner.id, "Aspirin label", "upload", "hash-1")


def make_chunk(document_id, position: int = 0, body: str = "Aspirin may cause stomach bleeding."):
    return ChunkRow(
        document_id=document_id,
        position=position,
        text=body,
        token_count=7,
        embedding=[0.5] * EMBEDDING_DIM,
        chunker_version="fixed.v1",
        embed_model_version="test-model@rev1",
    )


def test_ac_ing_05_chunk_stores_position_token_count_and_versions(db_session: Session) -> None:
    doc = make_document(db_session)
    db_session.add(make_chunk(doc.id, position=3))
    db_session.flush()
    stored = db_session.execute(select(ChunkRow)).scalar_one()
    assert stored.document_id == doc.id
    assert stored.position == 3
    assert stored.token_count == 7
    assert stored.chunker_version == "fixed.v1"
    assert stored.embed_model_version == "test-model@rev1"


def test_embedding_round_trips_with_the_right_dimension(db_session: Session) -> None:
    doc = make_document(db_session)
    db_session.add(make_chunk(doc.id))
    db_session.flush()
    stored = db_session.execute(select(ChunkRow)).scalar_one()
    assert len(stored.embedding) == EMBEDDING_DIM
    assert abs(float(stored.embedding[0]) - 0.5) < 1e-6


def test_wrong_embedding_dimension_is_rejected(db_session: Session) -> None:
    doc = make_document(db_session)
    bad = make_chunk(doc.id)
    bad.embedding = [0.1] * (EMBEDDING_DIM - 1)
    db_session.add(bad)
    with pytest.raises(Exception):  # noqa: B017 - driver error type varies by version
        db_session.flush()


def test_keyword_column_is_filled_by_the_database(db_session: Session) -> None:
    doc = make_document(db_session)
    db_session.add(make_chunk(doc.id))
    db_session.flush()
    hit = db_session.execute(
        text("SELECT count(*) FROM chunks WHERE tsv @@ plainto_tsquery('english', 'bleeding')")
    ).scalar_one()
    miss = db_session.execute(
        text("SELECT count(*) FROM chunks WHERE tsv @@ plainto_tsquery('english', 'insulin')")
    ).scalar_one()
    assert (hit, miss) == (1, 0)


def test_position_is_unique_within_a_document(db_session: Session) -> None:
    doc = make_document(db_session)
    db_session.add(make_chunk(doc.id, position=0))
    db_session.flush()
    db_session.add(make_chunk(doc.id, position=0, body="different text"))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_deleting_a_document_deletes_its_chunks(db_session: Session) -> None:
    doc = make_document(db_session)
    db_session.add(make_chunk(doc.id))
    db_session.flush()
    db_session.execute(text("DELETE FROM documents WHERE id = :id"), {"id": doc.id})
    assert db_session.execute(text("SELECT count(*) FROM chunks")).scalar_one() == 0


def test_keyword_search_uses_a_gin_index(db_session: Session) -> None:
    names = db_session.execute(
        text("SELECT indexdef FROM pg_indexes WHERE tablename = 'chunks'")
    ).scalars()
    assert any("USING gin" in definition and "tsv" in definition for definition in names)


def test_ac_ret_01_embedding_column_has_an_hnsw_cosine_index(db_session: Session) -> None:
    definitions = db_session.execute(
        text("SELECT indexdef FROM pg_indexes WHERE tablename = 'chunks'")
    ).scalars()
    assert any("USING hnsw" in d and "vector_cosine_ops" in d for d in definitions)
