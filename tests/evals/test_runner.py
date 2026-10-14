"""T094: the eval runner end to end with a fake pipeline and fake judges."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from docdesk.db.models.evals import EvalResultRow, EvalRunRow
from docdesk.db.repositories.fingerprint import FingerprintRepository
from docdesk.evals.config import PromptPinMismatch, load_eval_config
from docdesk.evals.golden.loader import SplitLockedError
from docdesk.evals.judges.kit import load_judge_kit
from docdesk.evals.preflight import FingerprintMismatch
from docdesk.evals.runner import NOT_RUN_FIXTURE, RunOptions, run_eval
from docdesk.prompts.loader import load_prompt
from fakes.eval_run import FakeGoldenCorpus, FakePipeline, RunInterrupted, write_golden
from fakes.llm import FakeLLMClient

pytestmark = pytest.mark.integration

ROOT = Path(__file__).resolve().parents[2]
CONFIG = load_eval_config(ROOT / "evals" / "configs" / "b0.toml")
JUDGE_MODEL = CONFIG.values["models"]["judge"]
PROMPT = load_prompt(ROOT / "prompts" / "answer" / "answer.v1.md")
FAITH_OK = json.dumps({"claims": [{"claim": "c", "label": "supported", "evidence_id": "c1"}]})
CORRECT_OK = json.dumps({"key_points": [{"point": 1, "label": "covered"}]})
OPTIONS = RunOptions(commit=False)


@pytest.fixture
def session(db_session: Session) -> Session:
    FingerprintRepository(db_session).write(CONFIG.corpus_fingerprint())
    return db_session


def go(session: Session, tmp_path: Path, pipeline, client, options: RunOptions = OPTIONS,
       prompt=PROMPT):
    kit = None if options.retrieval_only else load_judge_kit(ROOT / "prompts", client, JUDGE_MODEL)
    summary = run_eval(
        config=CONFIG, answer_prompt=prompt, session=session, corpus=FakeGoldenCorpus(),
        golden_dir=write_golden(tmp_path / "golden"), pipeline=pipeline, kit=kit, options=options,
    )
    return summary, kit


def rows(session: Session, run_id) -> dict[str, EvalResultRow]:
    query = select(EvalResultRow).where(EvalResultRow.run_id == run_id)
    return {row.item_id: row for row in session.execute(query).scalars()}


def test_ac_evl_03_runner_01_end_to_end_with_fake_pipeline_and_judges(session, tmp_path) -> None:
    client = FakeLLMClient([FAITH_OK, CORRECT_OK])
    summary, _ = go(session, tmp_path, FakePipeline(), client)
    stored = rows(session, summary.run_id)
    assert sorted(stored) == ["gi-001", "gi-002", "gi-003", "gi-004"]  # dev, verified only
    first = stored["gi-001"].metrics
    assert (first["recall"], first["faithfulness"], first["correctness"]) == (1.0, 1.0, 1.0)
    assert first["citation_precision"] == 1.0 and first["passed"] is True
    assert stored["gi-001"].trace["faithfulness_labels"][0]["label"] == "supported"
    assert stored["gi-002"].metrics["outcome"] == "abstained" and stored["gi-002"].metrics["passed"]
    assert stored["gi-003"].metrics["outcome"] == "refused" and stored["gi-003"].metrics["passed"]
    assert len(client.requests) == 2  # abstain and refuse items cost no judge call
    assert all(request.model == JUDGE_MODEL for request in client.requests)
    run = session.get(EvalRunRow, summary.run_id)
    assert run.finished_at is not None and run.config_id == "b0" and run.prompt_bundle_id


def test_ac_evl_03_runner_02_a_failed_item_stores_its_label(session, tmp_path) -> None:
    pipeline = FakePipeline()
    missed = pipeline.outputs["How should famotidine be taken according to the label?"]
    pipeline.outputs[next(iter(pipeline.outputs))] = replace(
        missed, outcome="abstained", candidate_ids=["chunk-2"], retrieved_ids=["chunk-2"],
        used_ids=["chunk-2"], cited_ids=[],
    )
    summary, _ = go(session, tmp_path, pipeline, FakeLLMClient([]))
    assert rows(session, summary.run_id)["gi-001"].failure_label == "retrieval_miss"


def test_ac_evl_03_runner_03_injected_items_are_recorded_as_not_run(session, tmp_path) -> None:
    summary, _ = go(session, tmp_path, FakePipeline(), FakeLLMClient([FAITH_OK, CORRECT_OK]))
    skipped = rows(session, summary.run_id)["gi-004"].metrics
    assert skipped["status"] == "not_run" and skipped["reason"] == NOT_RUN_FIXTURE
    assert summary.not_run == 1 and summary.ran == 3


def test_ac_evl_03_runner_04_dev_is_the_default_and_test_needs_the_flag(session, tmp_path) -> None:
    with pytest.raises(SplitLockedError):
        locked = RunOptions(split="test", commit=False)
        go(session, tmp_path, FakePipeline(), FakeLLMClient([]), locked)
    assert session.scalar(select(func.count()).select_from(EvalRunRow)) == 0
    options = RunOptions(split="test", allow_test=True, commit=False)
    client = FakeLLMClient([FAITH_OK, CORRECT_OK])
    summary, _ = go(session, tmp_path, FakePipeline(), client, options)
    assert sorted(rows(session, summary.run_id)) == ["gi-006"]


def test_ac_evl_03_runner_05_an_interrupted_run_resumes_and_skips_finished_items(
    session, tmp_path
) -> None:
    client = FakeLLMClient([FAITH_OK, CORRECT_OK])
    stopping = FakePipeline(stop_on="Can I double my famotidine dose tonight?")
    with pytest.raises(RunInterrupted):
        go(session, tmp_path, stopping, client)
    assert stopping.questions.count("How should famotidine be taken according to the label?") == 1
    second = FakePipeline()
    summary, _ = go(session, tmp_path, second, client)
    assert summary.skipped_done == 2 and summary.ran == 1 and summary.not_run == 1
    assert second.questions == ["Can I double my famotidine dose tonight?"]
    assert session.scalar(select(func.count()).select_from(EvalRunRow)) == 1
    assert len(rows(session, summary.run_id)) == 4


def test_ac_evl_03_runner_06_a_stale_corpus_fingerprint_is_refused_before_any_write(
    session, tmp_path
) -> None:
    FingerprintRepository(session).write(replace(CONFIG.corpus_fingerprint(), chunk_size=999))
    with pytest.raises(FingerprintMismatch, match="chunk_size"):
        go(session, tmp_path, FakePipeline(), FakeLLMClient([]))
    assert session.scalar(select(func.count()).select_from(EvalRunRow)) == 0


def test_ac_evl_03_runner_07_a_changed_answer_prompt_is_refused(session, tmp_path) -> None:
    with pytest.raises(PromptPinMismatch):
        go(session, tmp_path, FakePipeline(), FakeLLMClient([]),
           prompt=replace(PROMPT, content_hash="1" * 64))
    assert session.scalar(select(func.count()).select_from(EvalRunRow)) == 0


def test_ac_evl_03_runner_08_judge_parse_failures_are_counted_and_not_scored(
    session, tmp_path
) -> None:
    summary, _ = go(session, tmp_path, FakePipeline(), FakeLLMClient(["garbage", CORRECT_OK]))
    metrics = rows(session, summary.run_id)["gi-001"].metrics
    assert metrics["faithfulness"] is None and metrics["faithfulness_status"] == "parse_failed"
    assert len(summary.parse_failures["faithfulness"]) == 1
    assert summary.parse_failures["correctness"] == []


def test_ac_evl_02_runner_09_retrieval_only_makes_no_judge_or_generation_call(
    session, tmp_path
) -> None:
    options = RunOptions(retrieval_only=True, commit=False)
    summary, kit = go(session, tmp_path, FakePipeline(), None, options)
    assert kit is None
    stored = rows(session, summary.run_id)
    assert stored["gi-001"].metrics["recall"] == 1.0
    assert stored["gi-001"].metrics["faithfulness"] is None
    assert stored["gi-001"].metrics["mode"] == "retrieval_only"
    assert session.get(EvalRunRow, summary.run_id).prompt_bundle_id is None
