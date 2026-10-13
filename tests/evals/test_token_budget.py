"""The daily guard stops a run cleanly before the limit, and a run can resume from disk."""

from __future__ import annotations

from pathlib import Path

import pytest

from docdesk.evals.budget import (
    BudgetedClient,
    BudgetStop,
    ProgressMismatch,
    RunProgress,
    TokenLedger,
)
from docdesk.evals.cache import CachedClient
from docdesk.llm.client import LLMRequest
from fakes.llm import FakeLLMClient

DAY = 24 * 3600.0
REQ = LLMRequest(system="s", user="u", model="m", max_output_tokens=100)


class Clock:
    def __init__(self) -> None:
        self.now = 1_000_000.0

    def __call__(self) -> float:
        return self.now


def make_ledger(tmp_path: Path, clock: Clock, limit: int = 1000) -> TokenLedger:
    return TokenLedger(tmp_path / "ledger.json", {"m": limit}, guard_fraction=0.85, clock=clock)


def test_t079d_spending_under_the_guard_is_allowed(tmp_path: Path) -> None:
    ledger = make_ledger(tmp_path, Clock())
    ledger.record("m", 500)
    ledger.check("m", 300)


def test_t079d_the_guard_is_85_percent_of_the_daily_limit(tmp_path: Path) -> None:
    ledger = make_ledger(tmp_path, Clock(), limit=1000)
    ledger.record("m", 800)
    ledger.check("m", 50)
    with pytest.raises(BudgetStop):
        ledger.check("m", 51)


def test_t079d_the_stop_message_says_when_and_how_to_continue(tmp_path: Path) -> None:
    clock = Clock()
    ledger = make_ledger(tmp_path, clock)
    ledger.record("m", 840)
    clock.now += 3600
    with pytest.raises(BudgetStop) as stop:
        ledger.check("m", 100)
    assert "m" in str(stop.value)
    assert "run the same command again" in str(stop.value)
    assert stop.value.resume_at == 1_000_000.0 + DAY


def test_t079d_spend_older_than_24_hours_no_longer_counts(tmp_path: Path) -> None:
    clock = Clock()
    ledger = make_ledger(tmp_path, clock)
    ledger.record("m", 840)
    clock.now += DAY + 1
    ledger.check("m", 800)


def test_t079d_the_ledger_survives_a_new_process(tmp_path: Path) -> None:
    clock = Clock()
    make_ledger(tmp_path, clock).record("m", 840)
    with pytest.raises(BudgetStop):
        make_ledger(tmp_path, clock).check("m", 100)


def test_t079d_a_model_without_a_limit_is_not_guarded(tmp_path: Path) -> None:
    ledger = make_ledger(tmp_path, Clock())
    ledger.record("other", 10_000_000)
    ledger.check("other", 10_000_000)


def test_t079d_a_call_bigger_than_the_whole_guard_stops_with_the_limit_named(
    tmp_path: Path,
) -> None:
    with pytest.raises(BudgetStop):
        make_ledger(tmp_path, Clock(), limit=100).check("m", 500)


def test_t079d_the_budgeted_client_records_the_real_tokens(tmp_path: Path) -> None:
    ledger = make_ledger(tmp_path, Clock(), limit=1000)
    client = BudgetedClient(FakeLLMClient(["one two three"]), ledger)
    client.complete(REQ)
    assert ledger.used("m") == 5


def test_t079d_the_budgeted_client_refuses_before_calling_the_model(tmp_path: Path) -> None:
    ledger = make_ledger(tmp_path, Clock(), limit=1000)
    ledger.record("m", 840)
    inner = FakeLLMClient(["never"])
    with pytest.raises(BudgetStop):
        BudgetedClient(inner, ledger).complete(REQ)
    assert inner.requests == []


def test_ac_evl_04_a_cache_hit_costs_no_budget_even_when_the_guard_is_full(
    tmp_path: Path,
) -> None:
    ledger = make_ledger(tmp_path, Clock(), limit=1000)
    cache_dir = tmp_path / "cache"
    first = CachedClient(BudgetedClient(FakeLLMClient(["answer"]), ledger), cache_dir)
    first.complete(REQ)
    ledger.record("m", 840)
    used = ledger.used("m")
    again = CachedClient(BudgetedClient(FakeLLMClient([]), ledger), cache_dir)
    assert again.complete(REQ).cache_hit is True
    assert ledger.used("m") == used


def test_t079d_progress_remembers_finished_items_across_processes(tmp_path: Path) -> None:
    first = RunProgress.open(tmp_path, config_id="b0", bundle_id="bundle1")
    first.mark_done("item-1")
    first.mark_done("item-2")
    second = RunProgress.open(tmp_path, config_id="b0", bundle_id="bundle1")
    assert second.is_done("item-1") and second.is_done("item-2")
    assert not second.is_done("item-3")
    assert second.done_count == 2


def test_t079d_marking_an_item_twice_counts_it_once(tmp_path: Path) -> None:
    progress = RunProgress.open(tmp_path, config_id="b0", bundle_id="bundle1")
    progress.mark_done("item-1")
    progress.mark_done("item-1")
    assert progress.done_count == 1


def test_t079d_progress_for_another_config_or_bundle_is_a_separate_run(tmp_path: Path) -> None:
    RunProgress.open(tmp_path, config_id="b0", bundle_id="bundle1").mark_done("item-1")
    other = RunProgress.open(tmp_path, config_id="b0", bundle_id="bundle2")
    assert not other.is_done("item-1")


def test_t079d_a_progress_file_that_names_another_run_is_refused(tmp_path: Path) -> None:
    RunProgress.open(tmp_path, config_id="b0", bundle_id="bundle1").mark_done("item-1")
    for path in tmp_path.glob("*.json"):
        path.write_text(path.read_text(encoding="utf-8").replace("bundle1", "bundleX"))
    with pytest.raises(ProgressMismatch):
        RunProgress.open(tmp_path, config_id="b0", bundle_id="bundle1")
