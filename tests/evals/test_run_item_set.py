"""F2: a run declares its item set; a different item set never joins or finishes it."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from docdesk.db.models.evals import EvalRunRow
from docdesk.db.repositories.fingerprint import FingerprintRepository
from docdesk.evals.config import load_eval_config
from docdesk.evals.judges.kit import load_judge_kit
from docdesk.evals.runner import RunOptions, run_eval
from docdesk.prompts.loader import load_prompt
from fakes.eval_run import FakeGoldenCorpus, FakePipeline, RunInterrupted, write_golden
from fakes.llm import FakeLLMClient

pytestmark = pytest.mark.integration

ROOT = Path(__file__).resolve().parents[2]
CONFIG = load_eval_config(ROOT / "evals" / "configs" / "b0.toml")
PROMPT = load_prompt(ROOT / "prompts" / "answer" / "answer.v1.md")
JUDGE_MODEL = CONFIG.values["models"]["judge"]
FAITH_OK = json.dumps({"claims": [{"claim": "c", "label": "supported", "evidence_id": "c1"}]})
CORRECT_OK = json.dumps({"key_points": [{"point": 1, "label": "covered"}]})
STOP_QUESTION = "Can I double my famotidine dose tonight?"


@pytest.fixture
def session(db_session: Session) -> Session:
    FingerprintRepository(db_session).write(CONFIG.corpus_fingerprint())
    return db_session


def go(session: Session, tmp_path: Path, pipeline=None, items=None):
    client = FakeLLMClient([FAITH_OK, CORRECT_OK] * 4)
    kit = load_judge_kit(ROOT / "prompts", client, JUDGE_MODEL)
    return run_eval(
        config=CONFIG, answer_prompt=PROMPT, session=session, corpus=FakeGoldenCorpus(),
        golden_dir=write_golden(tmp_path / "golden"), pipeline=pipeline or FakePipeline(), kit=kit,
        options=RunOptions(commit=False, items=items),
    )


def runs(session: Session) -> list[EvalRunRow]:
    return list(session.scalars(select(EvalRunRow).order_by(EvalRunRow.started_at)))


def test_ac_evl_08_items_01_the_run_declares_its_item_set(session, tmp_path) -> None:
    summary = go(session, tmp_path, items=("gi-001", "gi-002"))
    identity = session.get(EvalRunRow, summary.run_id).identity
    assert identity["items"] == ["gi-001", "gi-002"]


def test_ac_evl_08_items_02_an_items_run_never_joins_or_finishes_a_full_run(
    session, tmp_path
) -> None:
    with pytest.raises(RunInterrupted):
        go(session, tmp_path, FakePipeline(stop_on=STOP_QUESTION))
    full = runs(session)[0]
    assert full.finished_at is None
    small = go(session, tmp_path, items=("gi-001",))
    assert small.run_id != full.id and small.finished
    assert session.get(EvalRunRow, full.id).finished_at is None
    resumed = go(session, tmp_path)
    assert resumed.run_id == full.id and resumed.finished
    assert session.get(EvalRunRow, full.id).finished_at is not None


def test_ac_evl_08_items_03_a_run_with_missing_items_is_not_finished(session, tmp_path) -> None:
    pipeline = FakePipeline(stop_on=STOP_QUESTION)
    with pytest.raises(RunInterrupted):
        go(session, tmp_path, pipeline)
    assert runs(session)[0].finished_at is None
