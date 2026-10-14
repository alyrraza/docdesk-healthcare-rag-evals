"""F3: every config key is read or refused. A silent no-op config cannot exist."""

from __future__ import annotations

import tomllib
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest

from docdesk.evals.config import (
    KNOWN_KEYS,
    ConfigKeyError,
    EvalConfig,
    UnsupportedConfig,
    content_hash,
    load_eval_config,
)
from docdesk.evals.identity import build_identity
from docdesk.evals.judges.kit import load_judge_kit
from docdesk.evals.runner import run_bundle_id
from docdesk.generation.answer import to_request
from docdesk.llm.client import LLMRequest  # noqa: F401  (documents the type to_request returns)
from docdesk.prompts.loader import load_prompt
from docdesk.prompts.renderer import RenderedPrompt
from fakes.llm import FakeLLMClient

ROOT = Path(__file__).resolve().parents[2]
B0_PATH = ROOT / "evals" / "configs" / "b0.toml"
B0 = load_eval_config(B0_PATH)
PROMPT = load_prompt(ROOT / "prompts" / "answer" / "answer.v1.md")


def written(tmp_path: Path, change: dict[str, Any]) -> Path:
    """A copy of B0 with changes merged in, written with a correct hash."""
    values = tomllib.loads(B0_PATH.read_text(encoding="utf-8"))
    for section, body in change.items():
        if isinstance(body, dict):
            values.setdefault(section, {}).update(body)
        else:
            values[section] = body
    values["content_hash"] = content_hash(values)
    lines = []
    for key, value in values.items():
        if not isinstance(value, dict):
            lines.append(f"{key} = {_toml(value)}")
    for key, value in values.items():
        if isinstance(value, dict):
            lines.append(f"\n[{key}]")
            lines += [f"{k} = {_toml(v)}" for k, v in value.items()]
    path = tmp_path / "t.toml"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def _toml(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return f'"{value}"' if isinstance(value, str) else str(value)


def flat_keys(values: dict[str, Any]) -> set[str]:
    found = set()
    for key, value in values.items():
        if isinstance(value, dict):
            found |= {f"{key}.{inner}" for inner in value}
        else:
            found.add(key)
    return found


def test_ac_evl_08_keys_01_every_key_of_b0_is_a_known_key() -> None:
    known = {f"{s}.{k}" if keys else s for s, keys in KNOWN_KEYS.items() for k in (keys or [""])}
    assert flat_keys(B0.values) <= known


def test_ac_evl_08_keys_02_an_unknown_key_is_refused(tmp_path: Path) -> None:
    with pytest.raises(ConfigKeyError, match="retreival_depth"):
        load_eval_config(written(tmp_path, {"retrieval": {"retreival_depth": 3}}))
    with pytest.raises(ConfigKeyError, match="extra"):
        load_eval_config(written(tmp_path, {"extra": {"x": 1}}))


def test_ac_evl_08_keys_03_rerank_enabled_is_refused_until_a_reranker_exists(tmp_path) -> None:
    with pytest.raises(UnsupportedConfig, match="rerank"):
        load_eval_config(written(tmp_path, {"rerank": {"enabled": True}}))
    load_eval_config(written(tmp_path, {"rerank": {"enabled": False}}))


def test_ac_evl_08_keys_04_temperature_and_max_tokens_reach_the_request() -> None:
    rendered = RenderedPrompt(system="s", user="u")
    default = to_request(rendered, PROMPT, "m")
    assert (default.temperature, default.max_output_tokens) == (0.0, 600)
    changed = to_request(rendered, PROMPT, "m", temperature=0.7, max_output_tokens=300)
    assert (changed.temperature, changed.max_output_tokens) == (0.7, 300)


def test_ac_evl_08_keys_05_temperature_and_max_tokens_change_the_run_identity() -> None:
    def with_models(**change: Any) -> EvalConfig:
        return replace(B0, values={**B0.values, "models": {**B0.values["models"], **change}})

    kit = load_judge_kit(ROOT / "prompts", FakeLLMClient([]), B0.values["models"]["judge"])
    base = build_identity(B0, kit, ["gi-001"])
    assert base["generation"] == {"temperature": 0, "max_output_tokens": 600}
    hot = build_identity(with_models(temperature=0.7), kit, ["gi-001"])
    short = build_identity(with_models(max_output_tokens=300), kit, ["gi-001"])
    assert hot != base and short != base and hot != short
    assert run_bundle_id(with_models(temperature=0.7), PROMPT) != run_bundle_id(B0, PROMPT)
    assert run_bundle_id(with_models(max_output_tokens=300), PROMPT) != run_bundle_id(B0, PROMPT)
