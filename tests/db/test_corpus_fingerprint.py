"""The corpus fingerprint says how the stored chunks were made, so a run can check it first."""

from __future__ import annotations

import pytest
from sqlalchemy.orm import Session

from docdesk.db.repositories.fingerprint import (
    CorpusFingerprint,
    FingerprintRepository,
    differences,
)

pytestmark = pytest.mark.integration

RECURSIVE = CorpusFingerprint("recursive", 200, 40, "all-MiniLM-L6-v2@rev1")


def test_t080a_there_is_no_fingerprint_before_the_first_ingest(db_session: Session) -> None:
    assert FingerprintRepository(db_session).read() is None


def test_t080a_a_written_fingerprint_can_be_read_back(db_session: Session) -> None:
    repo = FingerprintRepository(db_session)
    repo.write(RECURSIVE)
    assert repo.read() == RECURSIVE


def test_t080a_a_second_write_replaces_the_first_instead_of_adding_a_row(
    db_session: Session,
) -> None:
    repo = FingerprintRepository(db_session)
    repo.write(CorpusFingerprint("fixed", 200, 40, "all-MiniLM-L6-v2@rev1"))
    repo.write(RECURSIVE)
    assert repo.read() == RECURSIVE


def test_t080a_differences_names_every_field_that_does_not_match() -> None:
    stored = CorpusFingerprint("fixed", 128, 40, "all-MiniLM-L6-v2@rev1")
    assert differences(stored, RECURSIVE) == ["chunker", "chunk_size"]


def test_t080a_differences_is_empty_when_the_fingerprints_are_equal() -> None:
    assert differences(RECURSIVE, RECURSIVE) == []
