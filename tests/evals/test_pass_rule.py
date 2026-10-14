"""F1: one pass rule. A judge that failed or gave no score never counts as a pass."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from docdesk.evals.golden.loader import gold_sets, load_golden
from docdesk.evals.judges.kit import load_judge_kit
from docdesk.evals.labeler import LabelInput, label_failure
from docdesk.evals.passing import scores_pass
from docdesk.evals.report_data import ResultRecord, RunData, build_report
from docdesk.evals.report_sections import is_strict_pass, stage_split, strict_pass_rate
from docdesk.evals.scoring import score_item
from fakes.eval_run import FakeGoldenCorpus, FakePipeline, write_golden
from fakes.llm import FakeLLMClient

ROOT = Path(__file__).resolve().parents[2]
CORRECT_OK = json.dumps({"key_points": [{"point": 1, "label": "covered"}]})
GOOD = LabelInput(
    behavior="answer", outcome="answered", retrieval_ran=True, packed=True,
    gold_sets=[frozenset({"g1"})], candidate_ids=["g1"], retrieved_ids=["g1"], used_ids=["g1"],
    faithfulness=1.0, correctness=1.0,
)


def test_ac_evl_08_pass_01_both_scores_at_one_and_nothing_contradicted_is_a_pass() -> None:
    assert scores_pass(1.0, 1.0, 0)
    assert not scores_pass(1.0, 0.5, 0)
    assert not scores_pass(0.9, 1.0, 0)
    assert not scores_pass(1.0, 1.0, 1)


def test_ac_evl_08_pass_02_a_missing_score_is_not_a_pass() -> None:
    assert not scores_pass(None, 1.0, 0)
    assert not scores_pass(1.0, None, 0)
    assert not scores_pass(None, None, 0)


def test_ac_evl_08_pass_03_the_labeler_fails_an_answer_whose_judge_failed() -> None:
    assert label_failure(replace(GOOD, faithfulness=None, judge_failed=True)) == "judge_failure"
    assert label_failure(replace(GOOD, correctness=None, judge_failed=True)) == "judge_failure"
    assert label_failure(replace(GOOD, faithfulness=None)) == "other"


def test_ac_evl_08_pass_04_a_parse_failure_is_not_passed_anywhere(tmp_path) -> None:
    corpus = FakeGoldenCorpus()
    items = load_golden(write_golden(tmp_path / "golden"), "dev", corpus)
    resolved = next(r for r in items if r.item.id == "gi-001")
    client = FakeLLMClient(["garbage", CORRECT_OK])
    kit = load_judge_kit(ROOT / "prompts", client, "m")
    output = FakePipeline().outputs[resolved.item.question]
    score = score_item(resolved, gold_sets(resolved, corpus), output, kit, 5)
    assert score.metrics["faithfulness"] is None
    assert score.metrics["passed"] is False
    assert score.failure_label == "judge_failure"
    record = ResultRecord("gi-001", score.metrics, score.failure_label)
    assert not is_strict_pass(record)
    assert strict_pass_rate([record]).passed == 0
    split = stage_split([record])
    assert split.counts["pass"] == 0 and split.counts["generation"] == 1
    overall = build_report(RunData("r", "c", "dev", "full", [record])).overall
    assert overall.metrics["pass_rate"].interval.estimate == 0.0
    assert build_report(RunData("r", "c", "dev", "full", [record])).judge_failures[
        "faithfulness"] == {"parse_failed": 1}
