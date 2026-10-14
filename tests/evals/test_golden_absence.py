"""AC-EVL-01: absence is proven by code, a term found in the scope fails the item."""

from __future__ import annotations

import uuid
from typing import Any

import pytest

from docdesk.evals.golden.absence import absence_problems
from docdesk.evals.golden.duplicates import CorpusScan
from docdesk.evals.golden.loader import ResolvedItem, resolve_item
from docdesk.evals.golden.report import absence_report
from docdesk.evals.golden.schema import GoldenItem

ALPHA, BETA = "seed:openfda:alpha", "seed:medlineplus:beta"


class TwoDocuments:
    """A corpus of two documents; the second one mentions Warfarin in a wrapped line."""

    texts = {
        ALPHA: "Alpha tablets are used for pain.\nStore at room temperature.",
        BETA: "Blood thinners such as\nWarfarin need regular blood tests.",
    }

    def document_id(self, source: str) -> uuid.UUID | None:
        return uuid.uuid5(uuid.NAMESPACE_URL, source) if source in self.texts else None

    def cleaned_text(self, document_id: uuid.UUID) -> str:
        return next(t for s, t in self.texts.items() if self.document_id(s) == document_id)

    def chunks(self, document_id: uuid.UUID) -> list[tuple[str, str]]:
        return [("c", self.cleaned_text(document_id))]

    def source_titles(self) -> dict[str, str]:
        return {ALPHA: "Alpha drug label", BETA: "Blood thinners"}


def item(terms: list[str], scope: str) -> GoldenItem:
    data: dict[str, Any] = {
        "id": "gi-055",
        "type": "unanswerable",
        "split": "dev",
        "question": "What is the usual adult dose of the drug in this topic?",
        "answerable": False,
        "gold_route": "documents",
        "no_evidence_reason": "The corpus does not say.",
        "absent_terms": terms,
        "absence_scope": scope,
    }
    return GoldenItem.model_validate(data)


def problems(terms: list[str], scope: str) -> list[str]:
    corpus = TwoDocuments()
    return absence_problems(item(terms, scope), corpus, CorpusScan(corpus))


def test_ac_evl_01_a_term_missing_from_the_whole_corpus_passes() -> None:
    assert problems(["apixaban", "eliquis"], "corpus") == []


def test_ac_evl_01_a_term_found_anywhere_in_the_corpus_fails_naming_the_document() -> None:
    found = problems(["apixaban", "warfarin"], "corpus")
    assert len(found) == 1
    assert "warfarin" in found[0] and BETA in found[0]


def test_ac_evl_01_the_check_ignores_case_and_folds_whitespace() -> None:
    assert problems(["WARFARIN NEED"], "corpus") != []
    assert problems(["such   as warfarin"], "corpus") != []


def test_ac_evl_01_a_document_scope_only_looks_at_that_document() -> None:
    assert problems(["warfarin"], ALPHA) == []
    assert problems(["warfarin"], BETA) != []


def test_ac_evl_01_a_scope_key_that_matches_no_document_is_a_problem() -> None:
    found = problems(["warfarin"], "seed:openfda:missing")
    assert found and "matches no document" in found[0]


def test_ac_evl_01_resolving_an_item_runs_the_absence_check() -> None:
    corpus = TwoDocuments()
    with pytest.raises(ValueError, match="warfarin"):
        resolve_item(item(["warfarin"], "corpus"), corpus, {}, CorpusScan(corpus))
    assert resolve_item(item(["apixaban"], "corpus"), corpus, {}, CorpusScan(corpus)).evidence == ()


def test_ac_evl_01_the_absence_report_lists_each_item_with_its_scope_and_term_count() -> None:
    items = [
        ResolvedItem(item(["apixaban", "eliquis"], "corpus"), ()),
        ResolvedItem(item(["incubation"], ALPHA), ()),
    ]
    lines = absence_report(items).splitlines()
    assert lines[0] == "absence check: 2 items"
    assert "gi-055: 2 terms absent from the whole corpus" in lines[1]
    assert f"gi-055: 1 term absent from {ALPHA}" in lines[2]


def test_ac_evl_01_the_absence_report_ignores_answerable_items() -> None:
    assert absence_report([]) == "absence check: no unanswerable items"
