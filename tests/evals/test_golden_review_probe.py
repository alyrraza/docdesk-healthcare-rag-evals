"""The review sheet of an unanswerable item shows what retrieval finds, so absence is visible."""

from __future__ import annotations

import uuid
from typing import Any

import numpy as np
import pytest

import docdesk.evals.golden.probe as probe_module
from docdesk.evals.golden.probe import Probe, ProbeChunk, probe_question
from docdesk.evals.golden.review import parse_sheet, render_sheet
from docdesk.evals.golden.schema import GoldenItem
from docdesk.retrieval.types import ScoredChunk


def unanswerable() -> GoldenItem:
    data: dict[str, Any] = {
        "id": "gi-055",
        "type": "unanswerable",
        "split": "dev",
        "question": "What is the usual adult dose of warfarin?",
        "answerable": False,
        "gold_route": "documents",
        "no_evidence_reason": "No document in the corpus is about warfarin.",
        "absent_terms": ["warfarin", "coumadin"],
        "absence_scope": "corpus",
    }
    return GoldenItem.model_validate(data)


PROBE = Probe(
    dense=[
        ProbeChunk("Aspirin drug label", 0.41, "Aspirin dense text one"),
        ProbeChunk("B", 0.3, "x"),
    ],
    keyword=[ProbeChunk("Heparin drug label", 0.9, "Heparin keyword text")],
)


def test_ac_evl_01_an_unanswerable_sheet_shows_the_reason_the_terms_and_the_scope() -> None:
    sheet = render_sheet([unanswerable()], {}, "b.yaml", {"gi-055": PROBE})
    for expected in (
        "No document in the corpus is about warfarin.",
        "warfarin, coumadin",
        "corpus",
        "## gi-055",
    ):
        assert expected in sheet


def test_ac_evl_01_the_sheet_lists_dense_and_keyword_chunks_with_title_and_score() -> None:
    sheet = render_sheet([unanswerable()], {}, "b.yaml", {"gi-055": PROBE})
    assert "dense top 3" in sheet and "keyword top 3" in sheet
    assert "Aspirin drug label" in sheet and "0.41" in sheet
    assert "Aspirin dense text one" in sheet and "Heparin keyword text" in sheet


def test_ac_evl_01_an_empty_leg_is_said_plainly() -> None:
    sheet = render_sheet([unanswerable()], {}, "b.yaml", {"gi-055": Probe(PROBE.dense, [])})
    assert "keyword top 3: no chunk matched" in sheet


def test_ac_evl_01_a_sheet_without_probes_has_no_retrieval_section() -> None:
    assert "dense top 3" not in render_sheet([unanswerable()], {}, "b.yaml")


def test_ac_evl_01_a_sheet_with_a_probe_still_parses_its_decisions() -> None:
    sheet = render_sheet([unanswerable()], {}, "b.yaml", {"gi-055": PROBE})
    filled = sheet.replace("Decision:\n", "Decision: OK\n")
    assert parse_sheet(filled).decisions["gi-055"].kind == "OK"


class FakeEncoder:
    def encode(self, texts: list[str]) -> np.ndarray:
        return np.zeros((len(texts), 384))


def scored(source: str, title: str, text: str, score: float) -> ScoredChunk:
    return ScoredChunk(uuid.uuid4(), uuid.uuid4(), title, text, score, source)


def test_ac_evl_01_probing_a_question_keeps_the_top_three_of_each_leg(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    asked: dict[str, int] = {}

    def dense(session: object, vector: object, user_id: object, top_n: int) -> list[ScoredChunk]:
        asked["dense"] = top_n
        return [scored("dense", f"D{n}", f"dense {n}", 1 - n / 10) for n in range(3)]

    def keyword(session: object, question: str, user_id: object, top_n: int) -> list[ScoredChunk]:
        asked["keyword"] = top_n
        return [scored("keyword", "K0", "keyword 0", 0.5)]

    monkeypatch.setattr(probe_module, "dense_search", dense)
    monkeypatch.setattr(probe_module, "keyword_search", keyword)
    probe = probe_question(object(), FakeEncoder(), "a question", uuid.uuid4())  # type: ignore[arg-type]
    assert asked == {"dense": 3, "keyword": 3}
    assert [chunk.title for chunk in probe.dense] == ["D0", "D1", "D2"]
    assert probe.keyword == [ProbeChunk("K0", 0.5, "keyword 0")]


def test_ac_evl_01_dashes_in_retrieved_text_are_shown_as_hyphens() -> None:
    probe = Probe([ProbeChunk("T", 0.5, "dose \u2014 twice daily, 5\u201310 mg")], [])
    sheet = render_sheet([unanswerable()], {}, "b.yaml", {"gi-055": probe})
    assert "\u2014" not in sheet and "\u2013" not in sheet
    assert "dose - twice daily, 5-10 mg" in sheet
