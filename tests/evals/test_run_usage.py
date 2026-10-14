"""T098b (AC-EVL-04): tokens are stored per call for each run, so a report never mixes runs."""

from __future__ import annotations

import json
from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from docdesk.db.models.evals import EvalResultRow
from docdesk.db.repositories.fingerprint import FingerprintRepository
from docdesk.evals.config import load_eval_config
from docdesk.evals.judges.kit import load_judge_kit
from docdesk.evals.report import report_markdown
from docdesk.evals.report_data import ResultRecord, RunData, build_report, load_run_data
from docdesk.evals.report_usage import usage_from_records
from docdesk.evals.runner import RunOptions, run_eval
from docdesk.generation.answer import Attempt, account
from docdesk.generation.result import AnswerResult, CallUsage, abstain_output
from docdesk.llm.client import LLMResult
from docdesk.prompts.loader import load_prompt
from fakes.eval_run import FakeGoldenCorpus, FakePipeline, write_golden
from fakes.llm import FakeLLMClient

ROOT = Path(__file__).resolve().parents[2]
CONFIG = load_eval_config(ROOT / "evals" / "configs" / "b0.toml")
JUDGE_MODEL = CONFIG.values["models"]["judge"]
PROMPT = load_prompt(ROOT / "prompts" / "answer" / "answer.v1.md")
FAITH_OK = json.dumps({"claims": [{"claim": "c", "label": "supported", "evidence_id": "c1"}]})
CORRECT_OK = json.dumps({"key_points": [{"point": 1, "label": "covered"}]})


class HitClient(FakeLLMClient):
    """A fake whose every reply says it came from the cache."""

    def complete(self, request):
        return replace(super().complete(request), cache_hit=True)


def llm_result(tokens_in: int, tokens_out: int, cache_hit: bool) -> LLMResult:
    return LLMResult("x", tokens_in, tokens_out, 1.0, "stop", "gen-m", Decimal("0.01"),
                     cache_hit=cache_hit)


def test_ac_evl_04_usage_10_account_records_every_generator_call_with_its_cache_flag() -> None:
    result = AnswerResult("", abstain_output("no_evidence"))
    account(result, [Attempt(llm=llm_result(100, 20, True)), Attempt(llm=llm_result(50, 5, False))])
    assert result.calls == [
        CallUsage("gen-m", 100, 20, Decimal("0.01"), True),
        CallUsage("gen-m", 50, 5, Decimal("0.01"), False),
    ]


@pytest.mark.integration
def test_ac_evl_04_usage_11_runner_stores_one_usage_entry_per_call(
    db_session: Session, tmp_path: Path
) -> None:
    FingerprintRepository(db_session).write(CONFIG.corpus_fingerprint())
    pipeline = FakePipeline()
    call = CallUsage("gen-m", 100, 20, Decimal("0.5"), False)
    pipeline.outputs[good_answer_question()].calls = [call]
    kit = load_judge_kit(ROOT / "prompts", HitClient([FAITH_OK, CORRECT_OK]), JUDGE_MODEL)
    summary = run_eval(
        config=CONFIG, answer_prompt=PROMPT, session=db_session, corpus=FakeGoldenCorpus(),
        golden_dir=write_golden(tmp_path / "golden"), pipeline=pipeline, kit=kit,
        options=RunOptions(commit=False),
    )
    rows = db_session.execute(
        select(EvalResultRow).where(EvalResultRow.run_id == summary.run_id)
    ).scalars()
    by_item = {row.item_id: row for row in rows}
    calls = by_item["gi-001"].usage
    assert [(c["role"], c["model"], c["cache_hit"]) for c in calls] == [
        ("generator", "gen-m", False), ("faithfulness", JUDGE_MODEL, True),
        ("correctness", JUDGE_MODEL, True)]
    assert calls[0]["tokens_in"] == 100 and calls[0]["cost_usd"] == "0.5"
    assert by_item["gi-003"].usage == []  # a refusal made no model call
    assert by_item["gi-004"].usage is None  # not run: nothing was measured


def good_answer_question() -> str:
    return "How should famotidine be taken according to the label?"


def entry(role: str, model: str, tokens_in: int, tokens_out: int, hit: bool) -> dict:
    return {"role": role, "model": model, "tokens_in": tokens_in, "tokens_out": tokens_out,
            "cost_usd": "0.01", "cache_hit": hit}


def record(item_id: str, usage: list[dict] | None) -> ResultRecord:
    metrics = {"status": "ok", "type": "single_fact", "behavior": "answer",
               "outcome": "answered", "group": item_id}
    return ResultRecord(item_id, metrics, None, usage=usage)


def test_ac_evl_04_usage_12_billed_and_saved_tokens_are_split_per_model() -> None:
    records = [
        record("a", [entry("generator", "gen", 100, 20, False),
                      entry("faithfulness", "j", 30, 5, True)]),
        record("b", [entry("generator", "gen", 50, 10, True)]),
    ]
    gen, judge = usage_from_records(records)
    assert (gen.model, gen.calls, gen.cached_calls) == ("gen", 2, 1)
    assert (gen.tokens_billed, gen.tokens_saved) == (120, 60)
    assert gen.cost_usd == Decimal("0.02") and gen.cost_billed == Decimal("0.01")
    assert (judge.model, judge.tokens_billed, judge.tokens_saved) == ("j", 0, 35)


def test_ac_evl_04_usage_13_a_run_without_stored_usage_is_not_guessed() -> None:
    assert usage_from_records([record("a", None), record("b", None)]) is None
    run = RunData("r", "b0", "dev", "full", [record("a", None)])
    text = report_markdown(build_report(run))
    assert "per run token numbers are not available for this run" in text


def test_ac_evl_04_usage_14_the_report_table_shows_billed_and_cached() -> None:
    run = RunData("r", "b0", "dev", "full", [
        record("a", [entry("generator", "gen", 100, 20, False),
                      entry("generator", "gen", 5, 5, True)])
    ])
    text = report_markdown(build_report(run))
    assert "| gen | 2 | 1 | 120 | 10 | 0.010000 |" in text
    header = "| model | calls | cached calls | tokens billed | tokens saved | cost billed USD |"
    assert header in text


@pytest.mark.integration
def test_ac_evl_04_usage_15_stored_usage_is_loaded_back_into_the_run_data(
    db_session: Session, tmp_path: Path
) -> None:
    FingerprintRepository(db_session).write(CONFIG.corpus_fingerprint())
    kit = load_judge_kit(ROOT / "prompts", FakeLLMClient([FAITH_OK, CORRECT_OK]), JUDGE_MODEL)
    summary = run_eval(
        config=CONFIG, answer_prompt=PROMPT, session=db_session, corpus=FakeGoldenCorpus(),
        golden_dir=write_golden(tmp_path / "golden"), pipeline=FakePipeline(), kit=kit,
        options=RunOptions(commit=False),
    )
    data = load_run_data(db_session, summary.run_id)
    first = next(r for r in data.records if r.item_id == "gi-001")
    assert [c["role"] for c in first.usage][-2:] == ["faithfulness", "correctness"]


def test_ac_evl_pool_11_usage_names_the_key_slot_that_served_each_call() -> None:
    result = AnswerResult("", abstain_output("no_evidence"))
    served = replace(llm_result(100, 20, False), slot=2)
    account(result, [Attempt(llm=served)])
    assert result.calls[0].slot == 2


def test_ac_evl_pool_12_billed_tokens_are_split_per_slot_in_the_report() -> None:
    slotted = {"slot": 1}, {"slot": 2}, {"slot": 2}
    calls = [{**entry("generator", "gen", 100, 20, False), **slotted[0]},
             {**entry("generator", "gen", 10, 5, False), **slotted[1]},
             {**entry("generator", "gen", 1, 1, False), **slotted[2]},
             {**entry("generator", "gen", 7, 7, True)}]
    (gen,) = usage_from_records([record("a", calls)])
    assert gen.billed_by_slot == {1: 120, 2: 17}
    text = report_markdown(build_report(RunData("r", "b0", "dev", "full", [record("a", calls)])))
    assert "| gen | 2 | 17 |" in text and "| gen | 1 | 120 |" in text


def test_ac_evl_pool_13_a_run_without_slots_has_no_slot_table() -> None:
    records = [record("a", [entry("generator", "gen", 100, 20, False)])]
    assert usage_from_records(records)[0].billed_by_slot == {}
    assert "per key slot" not in report_markdown(build_report(
        RunData("r", "b0", "dev", "full", records)))
