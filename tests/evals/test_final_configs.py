"""AC-EVL-08: the FINAL candidates differ from B0 only in the keys the amended rule allows."""

from __future__ import annotations

from pathlib import Path

from docdesk.evals.config import load_eval_config

CONFIGS = Path(__file__).resolve().parents[2] / "evals" / "configs"


def changed_keys(name: str) -> dict[str, tuple[object, object]]:
    """Why: shows exactly which settings a candidate moved away from the B0 baseline."""
    base = load_eval_config(CONFIGS / "b0.toml").values
    other = load_eval_config(CONFIGS / name).values
    out: dict[str, tuple[object, object]] = {}
    for section, body in other.items():
        if section in ("id", "content_hash") or not isinstance(body, dict):
            continue
        for key, value in body.items():
            if base[section].get(key) != value:
                out[f"{section}.{key}"] = (base[section].get(key), value)
    return out


def test_ac_evl_08_final_simple_is_cap4_alone() -> None:
    assert changed_keys("final_simple.toml") == {"packer.max_per_document": (2, 4)}
    assert load_eval_config(CONFIGS / "final_simple.toml").id == "final_simple"


def test_ac_evl_08_final_equals_final_simple_but_id() -> None:
    simple = load_eval_config(CONFIGS / "final_simple.toml").values
    final = load_eval_config(CONFIGS / "final.toml").values
    assert final["id"] == "final"
    drop = ("id", "content_hash")
    assert {k: v for k, v in final.items() if k not in drop} == {
        k: v for k, v in simple.items() if k not in drop
    }
