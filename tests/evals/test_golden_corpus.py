"""The database backed corpus: stable keys to ids, cleaned text, and chunks in order."""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session

from docdesk.db.repositories.documents import DocumentRepository
from docdesk.db.repositories.users import UserRepository
from docdesk.db.session import make_engine, make_session_factory
from docdesk.evals.golden.corpus import DatabaseCorpus
from docdesk.evals.golden.evidence import gold_chunk_ids
from docdesk.ingestion.pipeline import IngestConfig, ingest_document
from fakes.ingestion import FakeEncoder, FakeStore, WordCounter

pytestmark = pytest.mark.integration

BODY = " ".join(f"Sentence{n} has exactly six words here." for n in range(8))


@pytest.fixture
def session(migrated_url: str) -> Iterator[Session]:
    """Real commits, cleaned up by deleting the users, as the ingestion tests do."""
    engine = make_engine(migrated_url)
    with make_session_factory(engine)() as db:
        yield db
        db.rollback()
        db.execute(text("DELETE FROM users"))
        db.commit()
    engine.dispose()


def test_ac_evl_01_the_database_corpus_resolves_a_seed_key_and_gives_gold_chunks(
    session: Session,
) -> None:
    store = FakeStore()
    admin = UserRepository(session).add("golden-admin@example.com", "hash", "admin")
    document = DocumentRepository(session).add(
        admin.id, "label", "seed:openfda:abc", "g" * 64, is_shared=True
    )
    session.commit()
    store.save(document.id, BODY.encode())
    config = IngestConfig(chunker="fixed", size=12, overlap=0)
    ingest_document(session, document.id, store, FakeEncoder(), WordCounter(), config)

    corpus = DatabaseCorpus(session, store)
    assert corpus.document_id("seed:openfda:abc") == document.id
    assert corpus.document_id("seed:openfda:other") is None
    cleaned = corpus.cleaned_text(document.id)
    assert cleaned == BODY
    chunks = corpus.chunks(document.id)
    assert len(chunks) > 1
    quote = "Sentence5 has exactly six words here."
    gold = gold_chunk_ids(cleaned, quote, chunks)
    assert gold and all(chunk_id in dict(chunks) for chunk_id in gold)
    assert all(
        quote in dict(chunks)[chunk_id] or "Sentence5" in dict(chunks)[chunk_id]
        for chunk_id in gold
    )
