"""F14: ledger and cache paths do not depend on the working directory; limits are per model."""

from __future__ import annotations

import ast
import importlib
from pathlib import Path

import pytest

from docdesk.evals.config import EvalConfig, load_eval_config
from docdesk.llm.pacer import GROQ_FREE_LIMITS, ModelLimits

ROOT = Path(__file__).resolve().parents[2]
B0 = load_eval_config(ROOT / "evals" / "configs" / "b0.toml")


def test_ac_evl_04_paths_01_ledger_and_cache_paths_do_not_depend_on_the_cwd(
    monkeypatch, tmp_path
) -> None:
    monkeypatch.chdir(tmp_path)
    import docdesk.evals.cache as cache
    import docdesk.evals.cli_runtime as runtime
    import docdesk.evals.paths as paths

    for module in (paths, cache, runtime):
        importlib.reload(module)
    assert runtime.LEDGER_PATH == ROOT / ".cache" / "ledger.json"
    assert cache.DEFAULT_CACHE_DIR == ROOT / ".cache" / "llm"
    assert paths.PROJECT_ROOT == ROOT


def test_ac_evl_04_paths_02_smoke_test_goes_through_the_budget_guarded_stack() -> None:
    tree = ast.parse((ROOT / "scripts" / "smoke_llm.py").read_text(encoding="utf-8"))
    called = {n.func.id for n in ast.walk(tree) if isinstance(n, ast.Call)
              and isinstance(n.func, ast.Name)}
    assert "build_llm" not in called, "smoke_llm must use the stack, not the raw client"
    assert "llm_stack_for" in called


def test_ac_evl_04_limits_01_b0_keeps_the_groq_defaults() -> None:
    daily, per_minute = B0.model_limits("openai/gpt-oss-120b")
    assert daily == 200_000 and per_minute == GROQ_FREE_LIMITS


def test_ac_evl_04_limits_02_a_config_can_set_limits_per_model() -> None:
    values = {
        **B0.values,
        "limits": {"other/model": {"daily_tokens": 1000, "tokens_per_minute": 50,
                                   "requests_per_minute": 3}},
    }
    config = EvalConfig("x", "h", values)
    assert config.model_limits("other/model") == (1000, ModelLimits(50, 3))
    assert config.model_limits("openai/gpt-oss-120b")[0] == 200_000


@pytest.mark.parametrize("missing", ["daily_tokens", "tokens_per_minute", "requests_per_minute"])
def test_ac_evl_04_limits_03_a_partial_limits_table_is_refused(missing) -> None:
    entry = {"daily_tokens": 1, "tokens_per_minute": 2, "requests_per_minute": 3}
    del entry[missing]
    config = EvalConfig("x", "h", {**B0.values, "limits": {"m": entry}})
    with pytest.raises(ValueError, match=missing):
        config.model_limits("m")
