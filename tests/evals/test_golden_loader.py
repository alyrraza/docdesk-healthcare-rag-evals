"""The golden loader: reads YAML, validates, resolves source keys and guards the test split."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest

from docdesk.evals.golden.loader import (
    GoldenValidationError,
    SplitLockedError,
    count_items,
    gold_sets,
    load_golden,
)

SOURCE = "seed:openfda:abc"
TEXT = "Take with food. Store in a dry place. Keep out of reach of children."
DOC_ID = uuid.UUID(int=1)

ITEM = """
- id: {id}
  type: single_fact
  split: {split}
  question: "Where should the medicine be stored?"
  answerable: true
  gold_route: documents
  gold_facts: ["Store in a dry place"]
  gold_evidence:
    - source: {source}
      text: "{quote}"
  verified: {verified}
  verified_by: ali
  verified_on: 2026-10-20
"""


class FakeCorpus:
    """Two lookups backed by a dict, so loader tests need no database."""

    def __init__(self) -> None:
        self.ids = {SOURCE: DOC_ID}
        self.texts = {DOC_ID: TEXT}

    def document_id(self, source: str) -> uuid.UUID | None:
        return self.ids.get(source)

    def cleaned_text(self, document_id: uuid.UUID) -> str:
        return self.texts[document_id]

    def chunks(self, document_id: uuid.UUID) -> list[tuple[str, str]]:
        return [
            ("c0", "Take with food."),
            ("c1", "Store in a dry place."),
            ("c2", "Keep out of reach of children."),
        ]


def write_item(directory: Path, name: str = "a.yaml", **values: str) -> Path:
    fields = {
        "id": "gi-001",
        "split": "dev",
        "source": SOURCE,
        "quote": "dry place",
        "verified": "true",
        **values,
    }
    path = directory / name
    path.write_text(ITEM.format(**fields), encoding="utf-8")
    return path


def test_ac_evl_01_a_valid_file_loads_and_source_keys_become_document_ids(tmp_path: Path) -> None:
    write_item(tmp_path)
    loaded = load_golden(tmp_path, "dev", FakeCorpus())
    assert [entry.item.id for entry in loaded] == ["gi-001"]
    assert loaded[0].evidence[0].document_id == DOC_ID


def test_ac_evl_01_loading_dev_never_returns_test_items(tmp_path: Path) -> None:
    write_item(tmp_path, "a.yaml", id="gi-001", split="dev")
    write_item(tmp_path, "b.yaml", id="gi-002", split="test")
    assert [e.item.id for e in load_golden(tmp_path, "dev", FakeCorpus())] == ["gi-001"]


def test_ac_evl_01_the_test_split_needs_an_explicit_permission(tmp_path: Path) -> None:
    write_item(tmp_path, split="test")
    with pytest.raises(SplitLockedError):
        load_golden(tmp_path, "test", FakeCorpus())
    assert load_golden(tmp_path, "test", FakeCorpus(), allow_test=True)


def test_ac_evl_01_a_source_key_with_no_document_is_a_validation_error(tmp_path: Path) -> None:
    write_item(tmp_path, source="seed:openfda:missing")
    with pytest.raises(GoldenValidationError, match="seed:openfda:missing"):
        load_golden(tmp_path, "dev", FakeCorpus())


def test_ac_evl_01_a_quote_not_in_the_document_is_a_validation_error(tmp_path: Path) -> None:
    write_item(tmp_path, quote="a wet place")
    with pytest.raises(GoldenValidationError, match="gi-001.*a wet place"):
        load_golden(tmp_path, "dev", FakeCorpus())


def test_ac_evl_01_schema_errors_name_the_file_and_the_item(tmp_path: Path) -> None:
    path = write_item(tmp_path)
    path.write_text(path.read_text().replace("  verified_by: ali\n", ""), encoding="utf-8")
    with pytest.raises(GoldenValidationError, match=r"a\.yaml.*gi-001.*verified_by"):
        load_golden(tmp_path, "dev", FakeCorpus())


def test_ac_evl_01_all_problems_are_reported_together(tmp_path: Path) -> None:
    write_item(tmp_path, "a.yaml", id="gi-001", source="seed:openfda:missing")
    write_item(tmp_path, "b.yaml", id="gi-002", quote="a wet place")
    with pytest.raises(GoldenValidationError) as caught:
        load_golden(tmp_path, "dev", FakeCorpus())
    assert len(caught.value.problems) == 2


def test_ac_evl_01_the_same_id_in_two_files_is_an_error(tmp_path: Path) -> None:
    write_item(tmp_path, "a.yaml")
    write_item(tmp_path, "b.yaml")
    with pytest.raises(GoldenValidationError, match="duplicate id gi-001"):
        load_golden(tmp_path, "dev", FakeCorpus())


def test_ac_evl_01_unsafe_yaml_tags_are_refused(tmp_path: Path) -> None:
    (tmp_path / "bad.yaml").write_text("- !!python/object/apply:os.system ['echo hi']\n")
    with pytest.raises(GoldenValidationError, match="bad.yaml"):
        load_golden(tmp_path, "dev", FakeCorpus())


def test_ac_evl_01_a_file_that_is_not_a_list_of_items_is_an_error(tmp_path: Path) -> None:
    (tmp_path / "bad.yaml").write_text("id: gi-001\n")
    with pytest.raises(GoldenValidationError, match="list of items"):
        load_golden(tmp_path, "dev", FakeCorpus())


def test_ac_evl_01_an_empty_folder_loads_no_items(tmp_path: Path) -> None:
    assert load_golden(tmp_path, "dev", FakeCorpus()) == []


def test_ac_evl_01_gold_sets_gives_one_set_of_chunk_ids_per_evidence_entry(tmp_path: Path) -> None:
    write_item(tmp_path, quote="dry place")
    loaded = load_golden(tmp_path, "dev", FakeCorpus())
    assert gold_sets(loaded[0], FakeCorpus()) == [frozenset({"c1"})]


def test_ac_evl_01_the_loader_returns_only_verified_items_unless_drafts_are_asked_for(
    tmp_path: Path,
) -> None:
    write_item(tmp_path, "a.yaml", id="gi-001", verified="true")
    write_item(tmp_path, "b.yaml", id="gi-002", verified="false")
    assert [e.item.id for e in load_golden(tmp_path, "dev", FakeCorpus())] == ["gi-001"]
    everything = load_golden(tmp_path, "dev", FakeCorpus(), include_drafts=True)
    assert [e.item.id for e in everything] == ["gi-001", "gi-002"]


def test_ac_evl_01_a_draft_with_a_bad_quote_is_still_a_validation_error(tmp_path: Path) -> None:
    write_item(tmp_path, quote="a wet place", verified="false")
    with pytest.raises(GoldenValidationError, match="a wet place"):
        load_golden(tmp_path, "dev", FakeCorpus())


def test_ac_evl_01_the_report_counts_verified_and_unverified_items_separately(
    tmp_path: Path,
) -> None:
    write_item(tmp_path, "a.yaml", id="gi-001", verified="true")
    write_item(tmp_path, "b.yaml", id="gi-002", verified="false", split="test")
    write_item(tmp_path, "c.yaml", id="gi-003", verified="false")
    report = count_items(tmp_path)
    assert (report.verified, report.unverified) == (1, 2)
    assert report.by_split == {"dev": (1, 1), "test": (0, 1)}
    assert "verified 1, unverified 2" in report.summary()
