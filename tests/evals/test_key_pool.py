"""AC-EVL-POOL: several provider keys behave as one client; slot numbers show, keys never do."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest

from docdesk.evals.budget import BudgetStop, TokenLedger
from docdesk.evals.cache import cache_key
from docdesk.evals.config import load_eval_config
from docdesk.evals.key_pool import KeyPoolClient, seed_pool_ledger, slot_key
from docdesk.llm.client import LLMRequest
from docdesk.llm.errors import ProviderError, RateLimitedError
from fakes.llm import FakeLLMClient

MODEL = "m"
REQ = LLMRequest(system="s", user="u", model=MODEL, max_output_tokens=100)
CONFIGS = Path(__file__).resolve().parents[2] / "evals" / "configs"


class Clock:
    now = 1_000_000.0

    def __call__(self) -> float:
        return self.now


def pool(
    tmp_path: Path, clients: list[FakeLLMClient], limit: int = 1000
) -> tuple[KeyPoolClient, TokenLedger]:
    limits = {slot_key(MODEL, n): limit for n in range(1, len(clients) + 1)}
    ledger = TokenLedger(tmp_path / "pool.json", limits, clock=Clock())
    return KeyPoolClient(clients, ledger), ledger


def daily() -> RateLimitedError:
    return RateLimitedError("Groq daily limit reached", None, daily=True)


def test_ac_evl_pool_02_the_first_slot_with_room_serves_the_call(tmp_path: Path) -> None:
    client, ledger = pool(tmp_path, [FakeLLMClient(["a"]), FakeLLMClient(["b"])])
    result = client.complete(REQ)
    assert result.slot == 1 and result.text == "a"
    assert ledger.used(slot_key(MODEL, 1)) > 0 and ledger.used(slot_key(MODEL, 2)) == 0


def test_ac_evl_pool_03_a_slot_at_its_limit_hands_over_to_the_next(tmp_path: Path) -> None:
    client, ledger = pool(tmp_path, [FakeLLMClient([]), FakeLLMClient(["b"])])
    ledger.record(slot_key(MODEL, 1), 850)
    result = client.complete(REQ)
    assert result.slot == 2 and result.text == "b"


def test_ac_evl_pool_04_a_daily_limit_error_rotates_and_the_slot_stays_skipped(
    tmp_path: Path,
) -> None:
    first, second = FakeLLMClient([daily()]), FakeLLMClient(["b", "c"])
    client, _ = pool(tmp_path, [first, second])
    assert client.complete(REQ).slot == 2
    assert client.complete(REQ).slot == 2
    assert len(first.requests) == 1


def test_ac_evl_pool_05_other_errors_are_not_swallowed(tmp_path: Path) -> None:
    client, _ = pool(tmp_path, [FakeLLMClient([ProviderError("boom")]), FakeLLMClient(["b"])])
    with pytest.raises(ProviderError):
        client.complete(REQ)


def test_ac_evl_pool_06_every_slot_exhausted_is_a_normal_budget_stop(tmp_path: Path) -> None:
    client, ledger = pool(tmp_path, [FakeLLMClient([]), FakeLLMClient([daily()])])
    ledger.record(slot_key(MODEL, 1), 850)
    with pytest.raises(BudgetStop):
        client.complete(REQ)


def test_ac_evl_pool_07_logs_show_the_slot_number(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    client, _ = pool(tmp_path, [FakeLLMClient([daily()]), FakeLLMClient(["b"])])
    with caplog.at_level(logging.INFO, logger="docdesk.evals.key_pool"):
        client.complete(REQ)
    text = " ".join(r.getMessage() for r in caplog.records)
    assert "slot 1" in text and "slot 2" in text


def test_ac_evl_pool_08_slot_one_is_seeded_from_the_old_ledger(tmp_path: Path) -> None:
    old = tmp_path / "ledger.json"
    old.write_text(json.dumps({MODEL: [[Clock.now - 10, 800]]}), encoding="utf-8")
    new = tmp_path / "pool.json"
    seed_pool_ledger(new, old)
    ledger = TokenLedger(new, {slot_key(MODEL, 1): 1000}, clock=Clock())
    assert ledger.used(slot_key(MODEL, 1)) == 800
    seed_pool_ledger(new, old)
    assert ledger.used(slot_key(MODEL, 1)) == 800


def test_ac_evl_pool_09_a_request_hashes_exactly_as_before() -> None:
    request = LLMRequest(system="sys prompt", user="the question", model="openai/gpt-oss-120b")
    assert cache_key(request) == "8059fc0fd282123fa968ff5a4b0dfe5f918e65fce26830544175fcd3d79b0dcb"


def test_ac_evl_pool_10_committed_config_hashes_are_unchanged() -> None:
    pinned = {
        "b0.toml": "ec66619a5a99a1adb5968b76526e76d0e12e967ebd4e1874b6c13a1a5b7c19a6",
        "final_simple.toml": "d33ca14b2046a3e2b0c1d79583d3c2e6012d7d5894ee141c4d5af479558fb69f",
        "calib_cap4.toml": "d584122c4b8a68979a20d95d95c64f59cc408f756f5afe2a45a1665c116a440c",
    }
    for name, expected in pinned.items():
        assert load_eval_config(CONFIGS / name).values["content_hash"] == expected
