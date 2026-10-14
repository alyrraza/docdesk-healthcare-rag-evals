"""F9: a retrieval only run has no citations, so citation scores are None, never 0.0."""

from __future__ import annotations

from dataclasses import replace

from docdesk.evals.golden.loader import gold_sets, load_golden
from docdesk.evals.scoring import score_item
from fakes.eval_run import FakeGoldenCorpus, FakePipeline, write_golden


def test_ac_evl_02_retrieval_only_01_citation_scores_are_none_without_an_answer(tmp_path) -> None:
    corpus = FakeGoldenCorpus()
    items = load_golden(write_golden(tmp_path / "golden"), "dev", corpus)
    resolved = next(r for r in items if r.item.id == "gi-001")
    output = replace(FakePipeline().outputs[resolved.item.question], outcome=None, cited_ids=[])
    score = score_item(resolved, gold_sets(resolved, corpus), output, None, 5)
    assert score.metrics["recall"] == 1.0
    assert score.metrics["citation_recall"] is None
    assert score.metrics["citation_precision"] is None
