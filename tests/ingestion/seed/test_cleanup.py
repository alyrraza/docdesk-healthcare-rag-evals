"""Removing smoke test leftovers: chosen non-seed documents and files no document owns."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from docdesk.db.models.documents import DocumentRow
from docdesk.db.repositories.documents import DocumentRepository
from docdesk.db.repositories.users import UserRepository
from docdesk.ingestion.cleanup import delete_documents, find_orphan_files

pytestmark = pytest.mark.integration


@pytest.fixture
def two_documents(pipeline_session: Session):
    """One seed document and one upload, both owned by the same admin."""
    admin = UserRepository(pipeline_session).add("cleanup-admin@example.com", "hash", "admin")
    repo = DocumentRepository(pipeline_session)
    seed = repo.add(admin.id, "seeded", "seed:openfda:abc", "s" * 64, is_shared=True)
    upload = repo.add(admin.id, "smoke", "upload", "u" * 64)
    pipeline_session.commit()
    return seed, upload


def test_t080c_a_chosen_upload_is_deleted_and_the_seed_document_stays(
    pipeline_session: Session, two_documents
) -> None:
    seed, upload = two_documents
    assert delete_documents(pipeline_session, [upload.id]) == 1
    pipeline_session.commit()
    ids = pipeline_session.execute(select(DocumentRow.id)).scalars().all()
    assert ids == [seed.id]


def test_t080c_a_seed_document_cannot_be_deleted_by_this_path(
    pipeline_session: Session, two_documents
) -> None:
    seed, _ = two_documents
    with pytest.raises(ValueError, match="seed"):
        delete_documents(pipeline_session, [seed.id])


def test_t080c_an_unknown_document_id_is_an_error_not_a_silent_skip(
    pipeline_session: Session, two_documents
) -> None:
    with pytest.raises(LookupError, match="not found"):
        delete_documents(pipeline_session, [uuid.uuid4()])


def test_t080c_orphan_files_are_the_ones_no_document_owns(
    pipeline_session: Session, two_documents, tmp_path: Path
) -> None:
    seed, upload = two_documents
    (tmp_path / str(seed.id)).write_bytes(b"kept")
    (tmp_path / str(upload.id)).write_bytes(b"kept")
    orphan = tmp_path / str(uuid.uuid4())
    orphan.write_bytes(b"old")
    (tmp_path / "notes.txt").write_bytes(b"not a document file")
    assert find_orphan_files(pipeline_session, tmp_path) == [orphan]
