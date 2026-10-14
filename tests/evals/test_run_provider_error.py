"""F13: a generator provider error is not scored, left out of every n, and retried on resume."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from docdesk.db.models.evals import EvalResultRow, EvalRunRow
from docdesk.db.repositories.fingerprint import FingerprintRepository
from docdesk.evals.config import load_eval_config
from docdesk.evals.judges.kit import load_judge_kit
from docdesk.evals.pipeline import PipelineOutput
from docdesk.evals.report import report_markdown
from docdesk.evals.report_data import ResultRecord, RunData, build_report, load_run_data
from docdesk.evals.runner import RunOptions, run_eval
from docdesk.prompts.loader import load_prompt
from fakes.eval_run import FakeGoldenCorpus, FakePipeline, write_golden
from fakes.llm import FakeLLMClient

ROOT = Path(__file__).resolve().parents[2]
CONFIG = load_eval_config(ROOT / "evals" / "configs" / "b0.toml")
PROMPT = load_prompt(ROOT / "prompts" / "answer" / "answer.v1.md")
JUDGE_MODEL = CONFIG.values["models"]["judge"]
FAITH_OK = json.dumps({"claims": [{"claim": "c", "label": "supported", "evidence_id": "c1"}]})
CORRECT_OK = json.dumps({"key_points": [{"point": 1, "label": "covered"}]})
QUESTION = "How should famotidine be taken according to the label?"


def broken_pipeline() -> FakePipeline:
    pipeline = FakePipeline()
    pipeline.outputs[QUESTION] = PipelineOutput(
        outcome="error", abstain_reason="system_error", error_code="llm_timeout", answer="x")
    return pipeline


def go(session: Session, tmp_path: Path, pipeline: FakePipeline):
    client = FakeLLMClient([FAITH_OK, CORRECT_OK] * 4)
    kit = load_judge_kit(ROOT / "prompts", client, JUDGE_MODEL)
    return run_eval(
        config=CONFIG, answer_prompt=PROMPT, session=session, corpus=FakeGoldenCorpus(),
        golden_dir=write_golden(tmp_path / "golden"), pipeline=pipeline, kit=kit,
        options=RunOptions(commit=False),
    )


@pytest.mark.integration
def test_ac_evl_08_provider_01_an_error_item_is_not_scored_and_retried_on_resume(
    db_session: Session, tmp_path: Path
) -> None:
    FingerprintRepository(db_session).write(CONFIG.corpus_fingerprint())
    first = go(db_session, tmp_path, broken_pipeline())
    row = db_session.get(EvalResultRow, (first.run_id, "gi-001"))
    assert row.metrics["status"] == "not_scored" and row.metrics["reason"] == "llm_timeout"
    assert row.failure_label is None
    assert not first.finished
    assert db_session.get(EvalRunRow, first.run_id).finished_at is None
    healthy = FakePipeline()
    second = go(db_session, tmp_path, healthy)
    assert second.run_id == first.run_id and second.finished
    assert healthy.questions == [QUESTION]  # only the failed item was retried
    row = db_session.get(EvalResultRow, (first.run_id, "gi-001"))
    assert row.metrics["status"] == "ok"
    count = db_session.scalar(
        select(func.count()).select_from(EvalResultRow).where(EvalResultRow.run_id == first.run_id)
    )
    assert count == 4
    assert load_run_data(db_session, first.run_id).records  # loads back


def test_ac_evl_08_provider_02_the_report_leaves_it_out_of_n_and_counts_it_apart() -> None:
    ok = ResultRecord("gi-002", {"status": "ok", "type": "single_fact", "behavior": "answer",
                                 "outcome": "answered", "group": "g", "passed": True,
                                 "recall": 1.0}, None)
    bad = ResultRecord("gi-001", {"status": "not_scored", "type": "single_fact",
                                  "reason": "llm_timeout"}, None)
    report = build_report(RunData("r", "c", "dev", "full", [ok, bad]))
    assert report.total_ok == 1
    assert report.not_scored == [("gi-001", "llm_timeout")]
    assert "Not scored (provider error)" in report_markdown(report)
    assert replace(ok).item_id == "gi-002"
