"""T094: the order of the call layers, and the checks that stop a run before it starts."""

from __future__ import annotations

from dataclasses import replace
from decimal import Decimal
from pathlib import Path

import pytest

from docdesk.db.repositories.fingerprint import CorpusFingerprint
from docdesk.evals.budget import BudgetStop, TokenLedger
from docdesk.evals.config import PromptPinMismatch, load_eval_config
from docdesk.evals.preflight import FingerprintMismatch, check_run_allowed
from docdesk.evals.stack import build_llm_stack
from docdesk.llm.client import LLMRequest, LLMResult
from docdesk.llm.pacer import Pacer
from docdesk.prompts.loader import load_prompt

ROOT = Path(__file__).resolve().parents[2]
REQUEST = LLMRequest(system="sys", user="question one", model="m")


class SpyClient:
    """The real client stand in; it logs when the model would have been called."""

    def __init__(self, events: list[str]) -> None:
        self.events = events

    def complete(self, request: LLMRequest) -> LLMResult:
        self.events.append("client")
        return LLMResult("{}", 10, 5, 1.0, "stop", request.model, Decimal("0"))


class SpyLedger(TokenLedger):
    def __init__(self, events: list[str], path: Path, limits: dict[str, int]) -> None:
        super().__init__(path, limits)
        self.events = events

    def check(self, model: str, estimated_tokens: int) -> None:
        self.events.append("budget")
        super().check(model, estimated_tokens)


class SpyPacer(Pacer):
    def __init__(self, events: list[str]) -> None:
        super().__init__({})
        self.events = events

    def acquire(self, model: str, estimated_tokens: int):
        self.events.append("pacer")
        return super().acquire(model, estimated_tokens)


def make_stack(tmp_path: Path, limits: dict[str, int] | None = None):
    events: list[str] = []
    ledger = SpyLedger(events, tmp_path / "ledger.json", limits or {})
    stack = build_llm_stack(
        SpyClient(events), cache_dir=tmp_path / "cache", ledger=ledger, pacer=SpyPacer(events)
    )
    return stack, events, ledger


def test_ac_evl_04_stack_01_a_miss_goes_budget_then_pacer_then_client(tmp_path: Path) -> None:
    stack, events, _ = make_stack(tmp_path)
    stack.complete(REQUEST)
    assert events == ["budget", "pacer", "client"]


def test_ac_evl_04_stack_02_a_cache_hit_touches_no_layer_below_the_cache(tmp_path: Path) -> None:
    stack, events, ledger = make_stack(tmp_path)
    first = stack.complete(REQUEST)
    events.clear()
    second = stack.complete(REQUEST)
    assert events == []
    assert second.cache_hit is True and first.cache_hit is False
    assert ledger.used("m") == 15


def test_ac_evl_04_stack_03_the_budget_guard_stops_before_the_pacer_and_client(tmp_path) -> None:
    stack, events, _ = make_stack(tmp_path, limits={"m": 10})
    with pytest.raises(BudgetStop):
        stack.complete(REQUEST)
    assert events == ["budget"]


def test_ac_evl_04_stack_04_bypass_skips_the_cache_for_latency_runs(tmp_path: Path) -> None:
    events: list[str] = []
    ledger = SpyLedger(events, tmp_path / "l.json", {})
    stack = build_llm_stack(
        SpyClient(events), cache_dir=tmp_path / "c", ledger=ledger, pacer=SpyPacer(events),
        bypass_cache=True,
    )
    stack.complete(REQUEST)
    stack.complete(REQUEST)
    assert events.count("client") == 2


CONFIG = load_eval_config(ROOT / "evals" / "configs" / "b0.toml")
PROMPT = load_prompt(ROOT / "prompts" / "answer" / "answer.v1.md")


def test_ac_evl_04_preflight_01_a_matching_corpus_and_prompt_may_run() -> None:
    check_run_allowed(CONFIG, PROMPT, CONFIG.corpus_fingerprint())


def test_ac_evl_04_preflight_02_a_different_corpus_fingerprint_is_refused() -> None:
    for field, value in (("chunk_size", 400), ("overlap", 0), ("chunker", "fixed"),
                         ("embedding_model", "other@1")):
        stored: CorpusFingerprint = replace(CONFIG.corpus_fingerprint(), **{field: value})
        with pytest.raises(FingerprintMismatch, match=field):
            check_run_allowed(CONFIG, PROMPT, stored)


def test_ac_evl_04_preflight_03_a_missing_fingerprint_is_refused() -> None:
    with pytest.raises(FingerprintMismatch, match="no corpus fingerprint"):
        check_run_allowed(CONFIG, PROMPT, None)


def test_ac_evl_04_preflight_04_a_different_answer_prompt_hash_is_refused() -> None:
    edited = replace(PROMPT, content_hash="0" * 64)
    with pytest.raises(PromptPinMismatch):
        check_run_allowed(CONFIG, edited, CONFIG.corpus_fingerprint())
