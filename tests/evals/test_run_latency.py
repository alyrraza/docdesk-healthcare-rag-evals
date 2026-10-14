"""F4: per item latency is stored, and the report shows p50 and p95 from non cached calls."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from docdesk.db.models.evals import EvalResultRow
from docdesk.db.repositories.fingerprint import FingerprintRepository
from docdesk.evals.config import load_eval_config
from docdesk.evals.judges.kit import load_judge_kit
from docdesk.evals.report import report_markdown
from docdesk.evals.report_data import ResultRecord, RunData, build_report, load_run_data
from docdesk.evals.report_latency import latency_stats
from docdesk.evals.runner import RunOptions, run_eval
from docdesk.prompts.loader import load_prompt
from fakes.eval_run import FakeGoldenCorpus, FakePipeline, write_golden
from fakes.llm import FakeLLMClient

ROOT = Path(__file__).resolve().parents[2]
CONFIG = load_eval_config(ROOT / "evals" / "configs" / "b0.toml")
PROMPT = load_prompt(ROOT / "prompts" / "answer" / "answer.v1.md")
FAITH_OK = json.dumps({"claims": [{"claim": "c", "label": "supported", "evidence_id": "c1"}]})
CORRECT_OK = json.dumps({"key_points": [{"point": 1, "label": "covered"}]})


def timed(item_id: str, total: float, cache_hit: bool = False, retrieval: float = 10.0):
    latency = {"retrieval_ms": retrieval, "generation_ms": total / 2, "judge_ms": total / 4,
               "total_ms": total, "cache_hit": cache_hit}
    metrics = {"status": "ok", "type": "single_fact", "behavior": "answer",
               "outcome": "answered", "group": item_id, "passed": True}
    return ResultRecord(item_id, metrics, None, latency=latency)


def test_ac_obs_03_latency_01_percentiles_use_only_non_cached_items() -> None:
    records = [timed(f"gi-{n:03d}", float(n * 100)) for n in range(1, 11)]
    records.append(timed("gi-999", 99999.0, cache_hit=True))
    stats = latency_stats(records)
    assert stats["total_ms"].n == 10
    assert stats["total_ms"].p50 == pytest.approx(550.0)
    assert stats["total_ms"].p95 == pytest.approx(955.0)
    assert stats["retrieval_ms"].n == 11  # retrieval is never cached, so every item counts


def test_ac_obs_03_latency_02_an_old_run_says_not_recorded_and_never_zero() -> None:
    old = ResultRecord("gi-001", {"status": "ok", "type": "single_fact", "behavior": "answer",
                                  "outcome": "answered", "group": "g", "passed": True}, None)
    assert latency_stats([old]) == {}
    text = report_markdown(build_report(RunData("r", "b0", "dev", "full", [old])))
    assert "Latency: not recorded" in text


def test_ac_obs_03_latency_03_the_report_labels_the_numbers_as_non_cached() -> None:
    records = [timed(f"gi-{n:03d}", float(n * 100)) for n in range(1, 6)]
    text = report_markdown(build_report(RunData("r", "b0", "dev", "full", records)))
    assert "non cached" in text and "p95" in text


@pytest.mark.integration
def test_ac_obs_03_latency_04_run_eval_stores_timings_and_a_cache_flag(
    db_session: Session, tmp_path: Path
) -> None:
    FingerprintRepository(db_session).write(CONFIG.corpus_fingerprint())
    client = FakeLLMClient([FAITH_OK, CORRECT_OK])
    kit = load_judge_kit(ROOT / "prompts", client, CONFIG.values["models"]["judge"])
    summary = run_eval(
        config=CONFIG, answer_prompt=PROMPT, session=db_session, corpus=FakeGoldenCorpus(),
        golden_dir=write_golden(tmp_path / "golden"), pipeline=FakePipeline(), kit=kit,
        options=RunOptions(commit=False),
    )
    row = db_session.get(EvalResultRow, (summary.run_id, "gi-001"))
    assert set(row.latency) == {
        "retrieval_ms", "generation_ms", "judge_ms", "total_ms", "cache_hit"}
    assert row.latency["total_ms"] >= row.latency["judge_ms"] >= 0
    assert row.latency["cache_hit"] is False
    loaded = next(r for r in load_run_data(db_session, summary.run_id).records
                  if r.item_id == "gi-001")
    assert loaded.latency == row.latency
