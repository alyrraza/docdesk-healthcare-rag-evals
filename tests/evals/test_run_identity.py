"""F6: a run is tied to its judge prompts and judge model, and a resume must match them."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from docdesk.db.models.evals import EvalRunRow
from docdesk.db.repositories.fingerprint import FingerprintRepository
from docdesk.evals.config import load_eval_config
from docdesk.evals.identity import JudgePinMismatch, RunIdentityMismatch
from docdesk.evals.judges.kit import JudgeKit, load_judge_kit
from docdesk.evals.runner import RunOptions, run_eval
from docdesk.prompts.loader import load_prompt
from fakes.eval_run import FakeGoldenCorpus, FakePipeline, RunInterrupted, write_golden
from fakes.llm import FakeLLMClient

pytestmark = pytest.mark.integration

ROOT = Path(__file__).resolve().parents[2]
CONFIG = load_eval_config(ROOT / "evals" / "configs" / "b0.toml")
PROMPT = load_prompt(ROOT / "prompts" / "answer" / "answer.v1.md")
JUDGE_MODEL = CONFIG.values["models"]["judge"]
STOP_QUESTION = "Can I double my famotidine dose tonight?"
FAITH_OK = json.dumps({"claims": [{"claim": "c", "label": "supported", "evidence_id": "c1"}]})
CORRECT_OK = json.dumps({"key_points": [{"point": 1, "label": "covered"}]})


@pytest.fixture
def session(db_session: Session) -> Session:
    FingerprintRepository(db_session).write(CONFIG.corpus_fingerprint())
    return db_session


def kit_for(model: str = JUDGE_MODEL) -> JudgeKit:
    return load_judge_kit(ROOT / "prompts", FakeLLMClient([FAITH_OK, CORRECT_OK] * 3), model)


def go(session: Session, tmp_path: Path, kit: JudgeKit, pipeline=None):
    return run_eval(
        config=CONFIG, answer_prompt=PROMPT, session=session, corpus=FakeGoldenCorpus(),
        golden_dir=write_golden(tmp_path / "golden"), pipeline=pipeline or FakePipeline(),
        kit=kit, options=RunOptions(commit=False),
    )


def run_count(session: Session) -> int:
    return session.scalar(select(func.count()).select_from(EvalRunRow))


def test_ac_evl_08_identity_01_a_changed_judge_prompt_hash_is_refused(session, tmp_path) -> None:
    kit = kit_for()
    kit.faithfulness_prompt = replace(kit.faithfulness_prompt, content_hash="1" * 64)
    with pytest.raises(JudgePinMismatch, match="judge_faithfulness"):
        go(session, tmp_path, kit)
    assert run_count(session) == 0


def test_ac_evl_08_identity_02_a_judge_model_other_than_the_config_is_refused(
    session, tmp_path
) -> None:
    with pytest.raises(JudgePinMismatch, match="judge model"):
        go(session, tmp_path, kit_for("some/other-model"))
    assert run_count(session) == 0


def test_ac_evl_08_identity_03_the_run_stores_judge_pins_and_model(session, tmp_path) -> None:
    summary = go(session, tmp_path, kit_for())
    identity = session.get(EvalRunRow, summary.run_id).identity
    assert identity["judge_model"] == JUDGE_MODEL
    assert set(identity["judge_prompts"]) == {
        "judge_faithfulness@2.0.0", "judge_correctness@2.0.0"}
    assert identity["config_hash"] == CONFIG.content_hash


def test_ac_evl_08_identity_04_a_resume_under_other_judge_pins_is_refused(
    session, tmp_path
) -> None:
    with pytest.raises(RunInterrupted):
        go(session, tmp_path, kit_for(), FakePipeline(stop_on=STOP_QUESTION))
    run = session.scalars(select(EvalRunRow)).one()
    run.identity = {**run.identity, "judge_prompts": {"judge_faithfulness@2.0.0": "0" * 64}}
    session.flush()
    with pytest.raises(RunIdentityMismatch, match="judge_prompts"):
        go(session, tmp_path, kit_for())
    assert run_count(session) == 1


def test_ac_evl_08_identity_05_a_legacy_run_without_identity_is_never_continued(
    session, tmp_path
) -> None:
    with pytest.raises(RunInterrupted):
        go(session, tmp_path, kit_for(), FakePipeline(stop_on=STOP_QUESTION))
    session.scalars(select(EvalRunRow)).one().identity = None
    session.flush()
    summary = go(session, tmp_path, kit_for())
    assert run_count(session) == 2
    assert summary.skipped_done == 0
