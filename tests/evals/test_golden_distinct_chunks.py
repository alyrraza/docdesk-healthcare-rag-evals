"""A multi chunk item fails when two of its quotes land in the same chunk."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest

from docdesk.evals.golden.loader import GoldenValidationError, load_golden

SOURCE = "seed:openfda:abc"
TEXT = "First part about storage. Second part about children. Third part about food."

ITEM = """
- id: gi-033
  type: multi_chunk
  split: dev
  question: "What do the storage and children parts say together?"
  answerable: true
  gold_route: documents
  gold_facts: ["a", "b"]
  gold_evidence:
    - source: {source}
      text: "{first}"
    - source: {source}
      text: "{second}"
"""


class ChunkedCorpus:
    """One document cut into the chunks given by the test."""

    def __init__(self, chunks: list[str]) -> None:
        self._chunks = chunks

    def document_id(self, source: str) -> uuid.UUID | None:
        return uuid.UUID(int=1) if source == SOURCE else None

    def cleaned_text(self, document_id: uuid.UUID) -> str:
        return TEXT

    def chunks(self, document_id: uuid.UUID) -> list[tuple[str, str]]:
        return [(f"c{n}", text) for n, text in enumerate(self._chunks)]

    def source_titles(self) -> dict[str, str]:
        return {SOURCE: "Example"}


def write(tmp_path: Path, first: str, second: str) -> Path:
    (tmp_path / "m.yaml").write_text(
        ITEM.format(source=SOURCE, first=first, second=second), encoding="utf-8"
    )
    return tmp_path


def test_ac_evl_01_quotes_in_different_chunks_pass(tmp_path: Path) -> None:
    folder = write(tmp_path, "First part about storage.", "Second part about children.")
    corpus = ChunkedCorpus(
        ["First part about storage.", "Second part about children. Third part about food."]
    )
    assert len(load_golden(folder, "dev", corpus, include_drafts=True)) == 1


def test_ac_evl_01_quotes_in_one_chunk_fail_the_multi_chunk_item(tmp_path: Path) -> None:
    folder = write(tmp_path, "First part about storage.", "Second part about children.")
    corpus = ChunkedCorpus([TEXT])
    with pytest.raises(GoldenValidationError, match="same chunk"):
        load_golden(folder, "dev", corpus, include_drafts=True)
