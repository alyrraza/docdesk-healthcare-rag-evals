"""Cost is computed in code from a versioned price table (AC-OBS-03)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from docdesk.llm.cost import PRICE_TABLE_VERSION, UnknownModelError, compute_cost


def test_ac_obs_03_generator_cost_is_tokens_times_the_listed_price() -> None:
    # 1000 in at $0.15 per 1M plus 500 out at $0.60 per 1M.
    assert compute_cost("openai/gpt-oss-120b", 1000, 500) == Decimal("0.00045")


def test_ac_obs_03_judge_cost_uses_its_own_prices() -> None:
    assert compute_cost("qwen/qwen3.8-27b", 1000, 500) == Decimal("0.0028")


def test_ac_obs_03_free_openrouter_models_cost_nothing() -> None:
    assert compute_cost("google/gemma-4-31b-it:free", 5000, 5000) == Decimal("0")


def test_ac_obs_03_an_unknown_model_is_an_error_not_a_free_call() -> None:
    with pytest.raises(UnknownModelError, match="some/new-model"):
        compute_cost("some/new-model", 1, 1)


def test_ac_obs_03_the_price_table_has_a_version_with_a_date() -> None:
    assert PRICE_TABLE_VERSION.startswith("2026-")
