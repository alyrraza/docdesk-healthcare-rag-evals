"""T099 (AC-EVL-07): the calibration pool and the seeded, stratified sample."""

from __future__ import annotations

from collections import Counter

from docdesk.evals.calib_sample import SEED, Output, pool_from_runs, sample_outputs
from docdesk.evals.report_data import ResultRecord


def record(item_id: str, category: str, answer: str, outcome: str = "answered",
           status: str = "ok") -> ResultRecord:
    metrics = {"status": status, "type": category, "outcome": outcome}
    return ResultRecord(item_id, metrics, None, {"answer": answer, "used_ids": ["c-1", "c-2"]})


def outputs(count: int, category: str, run: str = "run-a", start: int = 0) -> list[Output]:
    return [Output(run, f"{category}-{start + i}", category, f"answer {category} {start + i}", ())
            for i in range(count)]


def test_ac_evl_07_calib_01_only_answered_outputs_enter_the_pool() -> None:
    rows = [
        record("gi-1", "single_fact", "Take it with food."),
        record("gi-2", "single_fact", "Not enough information.", outcome="abstained"),
        record("gi-3", "adversarial", "I can't give a dose.", outcome="refused"),
        record("gi-4", "single_fact", "System error.", outcome="error"),
        record("gi-5", "single_fact", "", status="not_run"),
    ]
    pool = pool_from_runs([("run-a", rows)])
    assert [o.item_id for o in pool] == ["gi-1"]
    assert pool[0].used_ids == ("c-1", "c-2")


def test_ac_evl_07_calib_02_same_item_and_same_answer_text_counts_once() -> None:
    first = [record("gi-1", "single_fact", "Take it with food."),
             record("gi-2", "multi_chunk", "Answer one.")]
    second = [record("gi-1", "single_fact", "Take it with food."),
              record("gi-2", "multi_chunk", "A different answer.")]
    pool = pool_from_runs([("run-b0", first), ("run-cap4", second)])
    assert [(o.run_id, o.item_id) for o in pool] == [
        ("run-b0", "gi-1"), ("run-b0", "gi-2"), ("run-cap4", "gi-2")]


def test_ac_evl_07_calib_03_a_fixed_seed_gives_the_same_sample() -> None:
    pool = outputs(60, "single_fact") + outputs(30, "multi_chunk")
    one = sample_outputs(pool, size=40, seed=SEED).outputs
    two = sample_outputs(list(reversed(pool)), size=40, seed=SEED).outputs
    assert one == two
    assert one != sample_outputs(pool, size=40, seed=SEED + 1).outputs


def test_ac_evl_07_calib_04_stratified_and_every_must_have_output_is_in() -> None:
    pool = (outputs(30, "single_fact") + outputs(10, "multi_chunk")
            + outputs(2, "unanswerable") + outputs(1, "adversarial"))
    result = sample_outputs(pool, size=40, seed=SEED)
    counts = Counter(o.category for o in result.outputs)
    assert counts == {"single_fact": 28, "multi_chunk": 9, "unanswerable": 2, "adversarial": 1}
    assert result.shortfall == 0


def test_ac_evl_07_calib_05_a_small_stratum_keeps_its_proportional_share_and_a_whole_pool() -> None:
    pool = outputs(50, "single_fact") + outputs(3, "multi_chunk")
    counts = Counter(o.category for o in sample_outputs(pool, size=40, seed=SEED).outputs)
    assert counts == {"single_fact": 38, "multi_chunk": 2}
    tiny = outputs(36, "single_fact") + outputs(1, "multi_chunk")
    assert Counter(o.category for o in sample_outputs(tiny, size=40, seed=SEED).outputs) == {
        "single_fact": 36, "multi_chunk": 1}


def test_ac_evl_07_calib_06_a_pool_smaller_than_the_size_is_taken_whole_and_reported() -> None:
    pool = outputs(20, "single_fact") + outputs(5, "multi_chunk")
    result = sample_outputs(pool, size=40, seed=SEED)
    assert len(result.outputs) == 25 and result.shortfall == 15


def test_ac_evl_07_calib_07_the_sample_is_numbered_from_one_and_has_no_repeats() -> None:
    result = sample_outputs(outputs(50, "single_fact"), size=40, seed=SEED)
    keys = [(o.run_id, o.item_id, o.answer_hash) for o in result.outputs]
    assert len(set(keys)) == 40
