"""F6 extra: a comparison warns when the two runs differ in split, judge or corpus."""

from __future__ import annotations

from typing import Any

from docdesk.evals.identity import legacy_identity
from docdesk.evals.report import compare_markdown
from docdesk.evals.report_compare import compare_runs
from docdesk.evals.report_data import ResultRecord, RunData


def ok(item_id: str) -> ResultRecord:
    metrics = {"status": "ok", "type": "single_fact", "behavior": "answer", "outcome": "answered",
               "group": item_id, "recall": 1.0, "mrr": 1.0, "faithfulness": 1.0,
               "correctness": 1.0, "passed": True}
    return ResultRecord(item_id, metrics, None)


def run(run_id: str, identity: dict[str, Any] | None, split: str = "dev") -> RunData:
    records = [ok(f"gi-{n:03d}") for n in range(1, 4)]
    return RunData(run_id, "b0", split, "full", records, identity=identity)


JUDGE = {"judge_model": "j1", "judge_prompts": {"p@1": "aaa"},
         "fingerprint": {"chunker": "recursive", "chunk_size": 200}}


def test_ac_evl_08_cmp_01_identical_judge_and_corpus_give_no_warning() -> None:
    result = compare_runs(run("a", dict(JUDGE)), run("b", dict(JUDGE)))
    assert result.warnings == []
    assert "WARNING" not in compare_markdown(result)


def test_ac_evl_08_cmp_02_judge_model_prompt_corpus_and_split_differences_warn_on_top() -> None:
    other = {"judge_model": "j2", "judge_prompts": {"p@1": "bbb"},
             "fingerprint": {"chunker": "fixed", "chunk_size": 200}}
    result = compare_runs(run("a", dict(JUDGE)), run("b", other, split="test"))
    text = compare_markdown(result)
    assert text.index("WARNING") < text.index("Paired on")
    for word in ("split", "judge model", "judge prompt", "corpus"):
        assert any(word in w for w in result.warnings), word


def test_ac_evl_08_cmp_03_a_run_without_identity_is_said_to_be_unchecked() -> None:
    result = compare_runs(run("a", None), run("b", dict(JUDGE)))
    assert any("no stored identity" in w for w in result.warnings)


def test_ac_evl_08_cmp_04_legacy_identity_is_read_from_the_row_traces() -> None:
    trace = {"config_hash": "h", "judge_model": "j1", "judge_prompts": {"p@1": "aaa"}}
    rows = [ResultRecord("gi-002", {"status": "ok"}, None, trace),
            ResultRecord("gi-001", {"status": "not_run"}, None, trace)]
    identity = legacy_identity(rows)
    assert identity["judge_model"] == "j1" and identity["judge_prompts"] == {"p@1": "aaa"}
    assert identity["items"] == ["gi-001", "gi-002"] and identity["legacy"] is True
    assert "fingerprint" not in identity
