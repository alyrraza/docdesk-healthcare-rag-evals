"""The local file store keeps uploaded bytes under one folder, named by document id."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest

from docdesk.ingestion.filestore import LocalFileStore


def test_ac_ing_01_saved_bytes_are_read_back_unchanged(tmp_path: Path) -> None:
    store = LocalFileStore(tmp_path)
    document_id = uuid.uuid4()
    store.save(document_id, b"\x00binary\xffbytes")
    assert store.read(document_id) == b"\x00binary\xffbytes"


def test_ac_ing_01_the_folder_is_created_on_first_save(tmp_path: Path) -> None:
    store = LocalFileStore(tmp_path / "uploads" / "nested")
    document_id = uuid.uuid4()
    store.save(document_id, b"hi")
    assert (tmp_path / "uploads" / "nested" / str(document_id)).read_bytes() == b"hi"


def test_ac_ing_03_reading_a_missing_document_fails_with_its_id(tmp_path: Path) -> None:
    document_id = uuid.uuid4()
    with pytest.raises(FileNotFoundError, match=str(document_id)):
        LocalFileStore(tmp_path).read(document_id)
