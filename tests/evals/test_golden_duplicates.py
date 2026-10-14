"""Duplicate evidence check: a quote in several documents needs a named source or alternates."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest

from docdesk.evals.golden.duplicates import also_in, document_names, question_names_document
from docdesk.evals.golden.loader import GoldenValidationError, load_golden
from docdesk.evals.golden.schema import Evidence

OWN, OTHER, THIRD = "seed:openfda:own", "seed:openfda:other", "seed:openfda:third"
SHARED = "Keep out of reach of children."

ITEM = """
- id: gi-001
  type: single_fact
  split: dev
  question: "{question}"
  answerable: true
  gold_route: documents
  gold_facts: ["Keep it away from children"]
  gold_evidence:
    - source: {own}
      text: "{quote}"
{alt}
"""


class DuplicateCorpus:
    """Three documents; the first two share a sentence and the third does not."""

    texts = {
        OWN: f"Alpha tablets. {SHARED}",
        OTHER: f"Beta tablets. {SHARED}",
        THIRD: "Gamma tablets. Store in a dry place.",
    }
    titles = {OWN: "alphamab drug label", OTHER: "betamab drug label", THIRD: "Gamma"}

    def document_id(self, source: str) -> uuid.UUID | None:
        return uuid.uuid5(uuid.NAMESPACE_URL, source) if source in self.texts else None

    def cleaned_text(self, document_id: uuid.UUID) -> str:
        return next(t for s, t in self.texts.items() if self.document_id(s) == document_id)

    def chunks(self, document_id: uuid.UUID) -> list[tuple[str, str]]:
        return [("c", self.cleaned_text(document_id))]

    def source_titles(self) -> dict[str, str]:
        return self.titles


def write(tmp_path: Path, question: str, alt: str = "") -> Path:
    path = tmp_path / "a.yaml"
    text = ITEM.format(question=question, own=OWN, quote=SHARED, alt=alt)
    path.write_text(text, encoding="utf-8")
    return tmp_path


def test_ac_evl_01_also_in_lists_every_other_document_that_holds_the_quote() -> None:
    texts = {key: " ".join(text.split()) for key, text in DuplicateCorpus.texts.items()}
    assert also_in(SHARED, OWN, texts) == (OTHER,)
    assert also_in("Store in a dry place.", THIRD, texts) == ()


def test_ac_evl_01_also_in_folds_whitespace_like_the_validator() -> None:
    texts = {OWN: "keep out", OTHER: "please keep\n\nout of reach"}
    assert also_in("keep out", OWN, {k: " ".join(v.split()) for k, v in texts.items()}) == (OTHER,)


def test_ac_evl_01_document_names_come_from_the_brand_and_the_generic_name() -> None:
    assert document_names("Pacerone (amiodarone hydrochloride) drug label") == [
        "pacerone",
        "amiodarone hydrochloride",
    ]
    assert document_names("ramipril drug label") == ["ramipril"]
    assert document_names("Eating Disorders") == ["eating disorders"]


def test_ac_evl_01_a_question_names_a_document_by_any_of_its_names() -> None:
    question = "What does the Alphamab label warn about?"
    assert question_names_document(question, "alphamab drug label")
    assert question_names_document("What is an eating disorder?", "Eating Disorders")
    assert not question_names_document("What does the label warn about?", "alphamab drug label")


def test_ac_evl_01_a_duplicate_quote_with_an_unnamed_source_fails_the_load(tmp_path: Path) -> None:
    folder = write(tmp_path, "Where should the tablets be kept away from?")
    with pytest.raises(GoldenValidationError, match="also in seed:openfda:other"):
        load_golden(folder, "dev", DuplicateCorpus(), include_drafts=True)


def test_ac_evl_01_naming_the_document_in_the_question_clears_the_duplicate(tmp_path: Path) -> None:
    folder = write(tmp_path, "Who must the alphamab tablets be kept away from?")
    loaded = load_golden(folder, "dev", DuplicateCorpus(), include_drafts=True)
    assert loaded[0].evidence[0].also_in == (OTHER,)


def test_ac_evl_01_alt_sources_clear_the_duplicate_and_count_as_gold(tmp_path: Path) -> None:
    alt = f"      alt_sources: [{OTHER}]"
    folder = write(tmp_path, "Where should the tablets be kept away from?", alt)
    loaded = load_golden(folder, "dev", DuplicateCorpus(), include_drafts=True)
    entry = loaded[0].evidence[0]
    assert entry.alt_document_ids == (DuplicateCorpus().document_id(OTHER),)


def test_ac_evl_01_an_alt_source_must_really_hold_the_quote(tmp_path: Path) -> None:
    alt = f"      alt_sources: [{THIRD}]"
    folder = write(tmp_path, "Who must the alphamab tablets be kept away from?", alt)
    with pytest.raises(GoldenValidationError, match="alt source"):
        load_golden(folder, "dev", DuplicateCorpus(), include_drafts=True)


def test_ac_evl_01_an_alt_source_cannot_be_the_main_source() -> None:
    with pytest.raises(ValueError, match="alt_sources"):
        Evidence(source=OWN, text="x", alt_sources=[OWN])


def test_ac_evl_01_the_report_lists_each_quote_with_its_other_documents(tmp_path: Path) -> None:
    from docdesk.evals.golden.report import duplicate_report

    folder = write(tmp_path, "Who must the alphamab tablets be kept away from?")
    loaded = load_golden(folder, "dev", DuplicateCorpus(), include_drafts=True)
    report = duplicate_report(loaded)
    assert "gi-001 quote 1: also in seed:openfda:other (named in the question)" in report
    assert duplicate_report([]) == "duplicate evidence check: no items"
