"""T096: the eval CLI (run, report, compare, check) with fakes and the test database."""

from __future__ import annotations

import json
from contextlib import nullcontext
from dataclasses import replace
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from docdesk.db.models.evals import EvalResultRow, EvalRunRow
from docdesk.db.repositories.fingerprint import FingerprintRepository
from docdesk.evals.budget import BudgetStop
from docdesk.evals.cli import Runtime, main
from docdesk.evals.config import load_eval_config
from docdesk.evals.judges.kit import load_judge_kit
from fakes.eval_run import FakeGoldenCorpus, FakePipeline, write_golden
from fakes.llm import FakeLLMClient

pytestmark = pytest.mark.integration

ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "evals" / "configs" / "b0.toml"
CONFIG = load_eval_config(CONFIG_PATH)
FAITH_OK = json.dumps({"claims": [{"claim": "c", "label": "supported"}]})
CORRECT_OK = json.dumps({"key_points": [{"point": 1, "label": "covered"}]})


class Calls:
    """Counts what the CLI built, to prove a mode did not touch the model side."""

    def __init__(self) -> None:
        self.judge_kits = 0
        self.pipelines: list[bool] = []
        self.pipeline = FakePipeline()
        self.client = FakeLLMClient([FAITH_OK, CORRECT_OK] * 3)


def make_runtime(session: Session, tmp_path: Path, calls: Calls) -> Runtime:
    def kit_for(config):
        calls.judge_kits += 1
        return load_judge_kit(ROOT / "prompts", calls.client, config.values["models"]["judge"])

    def pipeline_for(session, config, prompt, retrieval_only):
        calls.pipelines.append(retrieval_only)
        return calls.pipeline

    return Runtime(
        open_session=lambda: nullcontext(session), corpus_for=lambda s: FakeGoldenCorpus(),
        pipeline_for=pipeline_for, judge_kit_for=kit_for, golden_dir=write_golden(tmp_path / "g"),
        prompts_dir=ROOT / "prompts", git_sha="abc123", commit=False,
    )


@pytest.fixture
def setup(db_session: Session, tmp_path: Path):
    FingerprintRepository(db_session).write(CONFIG.corpus_fingerprint())
    calls = Calls()
    return db_session, make_runtime(db_session, tmp_path, calls), calls


def cli(runtime: Runtime, *args: str) -> int:
    return main(["--config", str(CONFIG_PATH), *args], runtime)


def test_ac_evl_06_cli_01_check_passes_without_running_anything(setup, capsys) -> None:
    _, runtime, calls = setup
    assert cli(runtime, "check") == 0
    out = capsys.readouterr().out
    for word in ("config", "fingerprint", "answer prompt", "judge prompts", "golden"):
        assert f"OK   {word}" in out
    assert calls.judge_kits == 0 and calls.pipelines == [] and calls.pipeline.questions == []


def test_ac_evl_06_cli_02_check_reports_a_stale_fingerprint(setup, capsys) -> None:
    session, runtime, _ = setup
    FingerprintRepository(session).write(replace(CONFIG.corpus_fingerprint(), overlap=0))
    assert cli(runtime, "check") == 1
    assert "FAIL fingerprint" in capsys.readouterr().out


def test_ac_evl_06_cli_03_check_reports_an_edited_config(setup, tmp_path, capsys) -> None:
    _, runtime, _ = setup
    edited = tmp_path / "b0.toml"
    edited.write_text(CONFIG_PATH.read_text(encoding="utf-8").replace("size = 200", "size = 201"),
                      encoding="utf-8")
    assert main(["--config", str(edited), "check"], runtime) == 1
    assert "FAIL config" in capsys.readouterr().out


def test_ac_evl_06_cli_04_retrieval_only_never_builds_a_judge_or_calls_a_model(
    setup, capsys
) -> None:
    _, runtime, calls = setup
    assert cli(runtime, "run", "--retrieval-only") == 0
    assert calls.judge_kits == 0 and calls.pipelines == [True]
    assert calls.client.requests == []
    assert "ran 3" in capsys.readouterr().out


def test_ac_evl_06_cli_05_a_full_run_then_report_and_compare(setup, capsys, tmp_path) -> None:
    session, runtime, calls = setup
    assert cli(runtime, "run") == 0
    assert calls.judge_kits == 1 and len(calls.client.requests) == 2
    capsys.readouterr()
    assert cli(runtime, "report") == 0
    report = capsys.readouterr().out
    assert "# Eval report" in report and "not run, needs T122" in report
    assert cli(runtime, "run") == 0  # the first run finished, so this is a second run
    runs = sorted(session.execute(select(EvalRunRow.id)).scalars())
    capsys.readouterr()
    assert cli(runtime, "compare", str(runs[0]), str(runs[1])) == 0
    assert "# Comparison" in capsys.readouterr().out
    target = tmp_path / "report.md"
    assert cli(runtime, "report", "--out", str(target)) == 0
    text = target.read_text(encoding="utf-8")
    assert "—" not in text and "–" not in text


def test_ac_evl_06_cli_06_the_test_split_needs_the_allow_flag(setup, capsys) -> None:
    _, runtime, _ = setup
    assert cli(runtime, "run", "--retrieval-only", "--split", "test") == 1
    assert "allow-test" in capsys.readouterr().out
    assert cli(runtime, "run", "--retrieval-only", "--split", "test", "--allow-test") == 0


def test_ac_evl_06_cli_07_a_budget_stop_exits_cleanly_with_the_resume_message(
    setup, capsys
) -> None:
    _, runtime, calls = setup

    def stop(question, *, retrieval_only):
        raise BudgetStop("Daily token guard for m: progress is saved.")

    calls.pipeline.run = stop
    assert cli(runtime, "run") == 2
    assert "progress is saved" in capsys.readouterr().out


def test_ac_evl_04_cli_report_reads_tokens_per_model_from_the_runtime_cache_folder(
    setup, capsys, tmp_path
) -> None:
    _, runtime, _ = setup
    cache = tmp_path / "cache"
    cache.mkdir()
    entry = {"text": "x", "tokens_in": 10, "tokens_out": 2, "latency_ms": 1.0,
             "finish_reason": "stop", "model": "cache-model", "cost_usd": "0.5"}
    (cache / "one.json").write_text(json.dumps(entry), encoding="utf-8")
    runtime.cache_dir = cache
    assert cli(runtime, "run") == 0
    capsys.readouterr()
    assert cli(runtime, "report") == 0
    assert "| cache-model | 1 | 10 | 2 | 0.500000 |" in capsys.readouterr().out


def test_ac_evl_06_cli_08_items_flag_runs_only_the_named_verified_items(setup, capsys) -> None:
    session, runtime, calls = setup
    assert cli(runtime, "run", "--items", "gi-002,gi-001") == 0
    assert "ran 2" in capsys.readouterr().out
    assert sorted(calls.pipeline.questions) == sorted([
        "How should famotidine be taken according to the label?",
        "What is the half-life of famotidine?",
    ])
    stored = session.execute(select(EvalResultRow.item_id)).scalars()
    assert sorted(stored) == ["gi-001", "gi-002"]


def test_ac_evl_06_cli_09_items_flag_refuses_ids_outside_the_chosen_split(setup, capsys) -> None:
    _, runtime, calls = setup
    # gi-005 is an unverified draft, gi-006 is a test item, gi-404 does not exist.
    assert cli(runtime, "run", "--items", "gi-001,gi-005,gi-006,gi-404") == 1
    out = capsys.readouterr().out
    assert "refused" in out and "gi-005" in out and "gi-006" in out and "gi-404" in out
    assert calls.pipeline.questions == []


def test_ac_evl_06_cli_10_items_flag_does_not_unlock_the_test_split(setup, capsys) -> None:
    _, runtime, calls = setup
    assert cli(runtime, "run", "--split", "test", "--items", "gi-006") == 1
    assert "allow-test" in capsys.readouterr().out and calls.pipeline.questions == []
    assert cli(runtime, "run", "--split", "test", "--allow-test", "--items", "gi-006") == 0
    assert len(calls.pipeline.questions) == 1


def test_ac_evl_06_cli_11_label_is_stored_on_the_run(setup) -> None:
    session, runtime, _ = setup
    assert cli(runtime, "run", "--retrieval-only", "--label", "smoke 3 items") == 0
    assert session.execute(select(EvalRunRow.label)).scalar_one() == "smoke 3 items"
    assert cli(runtime, "run", "--retrieval-only") == 0
    labels = sorted(str(x) for x in session.execute(select(EvalRunRow.label)).scalars())
    assert labels == ["None", "smoke 3 items"]
