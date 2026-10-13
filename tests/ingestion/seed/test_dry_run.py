"""A dry run chunks and embeds the corpus without touching any database (AC-ING-02)."""

from __future__ import annotations

from pathlib import Path

from docdesk.ingestion.pipeline import IngestConfig
from docdesk.ingestion.seed.common import SeedDocument, save_document
from docdesk.ingestion.seed.loader import dry_run
from fakes.ingestion import FakeEncoder, WordCounter

TEXT = " ".join(f"Sentence{n} has exactly six words here." for n in range(8))
CONFIG = IngestConfig(chunker="fixed", size=20, overlap=0)


def corpus(root: Path) -> Path:
    folder = root / "openfda"
    for source_id, text in {"a": TEXT, "b": TEXT, "blank": "  "}.items():
        save_document(folder, SeedDocument(source_id, source_id, text, "u"))
    return folder


def test_ac_ing_02_dry_run_counts_documents_chunks_and_tokens(tmp_path: Path) -> None:
    report = dry_run([corpus(tmp_path)], FakeEncoder(), WordCounter(), CONFIG)
    assert report.documents == 2
    assert report.chunks == 6
    assert report.tokens == 2 * 8 * 6
    assert report.max_chunk_tokens <= 20


def test_ac_ing_03_dry_run_reports_unreadable_files_instead_of_hiding_them(
    tmp_path: Path,
) -> None:
    report = dry_run([corpus(tmp_path)], FakeEncoder(), WordCounter(), CONFIG)
    assert [(name, reason) for name, reason in report.failed] == [
        ("blank", "file contains no text")
    ]


def test_ac_ing_02_dry_run_writes_nothing_and_needs_no_database(tmp_path: Path) -> None:
    folder = corpus(tmp_path)
    before = sorted(path.name for path in folder.iterdir())
    dry_run([folder], FakeEncoder(), WordCounter(), CONFIG)
    assert sorted(path.name for path in folder.iterdir()) == before
