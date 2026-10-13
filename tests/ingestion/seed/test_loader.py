"""The corpus loader registers downloaded files as shared documents, then ingests them."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from docdesk.db.models.chunks import ChunkRow
from docdesk.db.models.documents import DocumentRow, DocumentStatus
from docdesk.db.repositories.users import UserRepository
from docdesk.db.session import make_engine, make_session_factory
from docdesk.ingestion.pipeline import IngestConfig
from docdesk.ingestion.seed.common import SeedDocument, save_document
from docdesk.ingestion.seed.loader import ingest_all, register_corpus
from fakes.ingestion import FakeEncoder, WordCounter

pytestmark = pytest.mark.integration

TEXT = " ".join(f"Sentence{n} has exactly six words here." for n in range(8))


def write_corpus(root: Path, name: str, texts: dict[str, str]) -> Path:
    folder = root / name
    for source_id, text in texts.items():
        save_document(
            folder, SeedDocument(source_id, f"Title {source_id}", text, f"url/{source_id}")
        )
    return folder


@pytest.fixture
def admin_id(pipeline_session: Session):
    admin = UserRepository(pipeline_session).add("corpus-admin@example.com", "hash", "admin")
    pipeline_session.commit()
    return admin.id


def test_ac_ret_05_corpus_files_become_shared_documents_owned_by_the_admin(
    pipeline_session, tmp_path, store, admin_id
) -> None:
    folder = write_corpus(tmp_path, "openfda", {"a": TEXT, "b": TEXT + " Extra."})
    created = register_corpus(pipeline_session, store, [folder], admin_id)
    assert {doc.title for doc in created} == {"Title a", "Title b"}
    rows = pipeline_session.execute(select(DocumentRow)).scalars().all()
    assert all(row.is_shared and row.owner_id == admin_id for row in rows)
    assert all(row.source == "seed:openfda" and row.status == "queued" for row in rows)
    assert {doc.id for doc in created} == set(store.files)


def test_ac_ing_04_registering_the_same_corpus_twice_creates_nothing_new(
    pipeline_session, tmp_path, store, admin_id
) -> None:
    folder = write_corpus(tmp_path, "openfda", {"a": TEXT})
    register_corpus(pipeline_session, store, [folder], admin_id)
    assert register_corpus(pipeline_session, store, [folder], admin_id) == []
    assert len(pipeline_session.execute(select(DocumentRow)).scalars().all()) == 1


def test_ac_ing_03_a_missing_corpus_folder_tells_the_user_to_fetch_it(
    pipeline_session, tmp_path, store, admin_id
) -> None:
    with pytest.raises(FileNotFoundError, match="fetch_openfda"):
        register_corpus(pipeline_session, store, [tmp_path / "openfda"], admin_id)


def test_ac_ing_02_ingest_all_marks_good_files_ready_and_reports_bad_ones(
    pipeline_session, tmp_path, store, admin_id, migrated_url
) -> None:
    folder = write_corpus(tmp_path, "medlineplus", {"good": TEXT, "bad": "   "})
    created = register_corpus(pipeline_session, store, [folder], admin_id)
    engine = make_engine(migrated_url)
    summary = ingest_all(
        make_session_factory(engine),
        store,
        FakeEncoder(),
        WordCounter(),
        [doc.id for doc in created],
        IngestConfig(chunker="fixed", size=20, overlap=0),
    )
    engine.dispose()
    pipeline_session.expire_all()
    assert summary.ready == 1
    assert [reason for _, reason in summary.failed] == ["file contains no text"]
    statuses = {
        row.title: row.status for row in pipeline_session.execute(select(DocumentRow)).scalars()
    }
    assert statuses == {"Title good": DocumentStatus.READY, "Title bad": DocumentStatus.FAILED}
    assert pipeline_session.execute(select(ChunkRow)).scalars().first() is not None
