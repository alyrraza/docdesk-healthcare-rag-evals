"""Shared seed helpers: downloads stay under data/ or .cache/, files are safe and resumable."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from docdesk.ingestion.seed.common import (
    SeedDocument,
    ensure_download_dir,
    load_manifest,
    save_document,
)


def doc(source_id: str = "abc-123", text: str = "Some label text.") -> SeedDocument:
    return SeedDocument(source_id=source_id, title="Aspirin label", text=text, source_url="u")


def test_ac_ing_01_a_download_folder_under_data_is_allowed(tmp_path: Path) -> None:
    folder = tmp_path / "data" / "corpus"
    assert ensure_download_dir(folder, tmp_path) == folder.resolve()


def test_ac_ing_01_a_download_folder_under_cache_is_allowed(tmp_path: Path) -> None:
    ensure_download_dir(tmp_path / ".cache" / "x", tmp_path)


@pytest.mark.parametrize("relative", ["docs", "src/stuff", ".", "data/../src", "../elsewhere"])
def test_ac_ing_01_any_other_download_folder_is_refused(tmp_path: Path, relative: str) -> None:
    with pytest.raises(ValueError, match="data/ or .cache/"):
        ensure_download_dir(tmp_path / relative, tmp_path)


def test_ac_ing_01_save_writes_the_text_and_records_it_in_the_manifest(tmp_path: Path) -> None:
    path = save_document(tmp_path, doc())
    assert path.read_text(encoding="utf-8") == "Some label text."
    assert load_manifest(tmp_path)["abc-123"] == {
        "title": "Aspirin label",
        "source_url": "u",
        "query": "",
        "file": "abc-123.txt",
    }


def test_ac_ing_01_a_source_id_cannot_escape_the_folder(tmp_path: Path) -> None:
    path = save_document(tmp_path / "out", doc(source_id="../../evil"))
    assert path.parent == (tmp_path / "out")
    assert not (tmp_path / "evil.txt").exists()


def test_ac_ing_01_saving_a_second_document_keeps_the_first_in_the_manifest(
    tmp_path: Path,
) -> None:
    save_document(tmp_path, doc("one"))
    save_document(tmp_path, doc("two"))
    assert set(load_manifest(tmp_path)) == {"one", "two"}


def test_ac_ing_01_a_missing_manifest_reads_as_empty(tmp_path: Path) -> None:
    assert load_manifest(tmp_path) == {}


def test_ac_ing_01_a_corrupt_manifest_is_reported_not_ignored(tmp_path: Path) -> None:
    (tmp_path / "manifest.json").write_text("{not json", encoding="utf-8")
    with pytest.raises(json.JSONDecodeError):
        load_manifest(tmp_path)
