"""What a run is tied to: config, judge model, judge prompts. A resume must match all of it."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import asdict
from typing import Any, Protocol

from docdesk.evals.config import EvalConfig
from docdesk.evals.judges.kit import JudgeKit


class JudgePinMismatch(ValueError):
    """The judge prompts or judge model in use are not the ones the config pins."""


class RunIdentityMismatch(ValueError):
    """An unfinished run was started under other pins, so it must not be continued."""


def check_judge_pins(config: EvalConfig, kit: JudgeKit) -> None:
    """Refuse a judge prompt edit or a judge model swap, so a judge change is never silent."""
    pinned_model = config.values["models"]["judge"]
    if kit.model != pinned_model:
        raise JudgePinMismatch(f"{config.id} pins judge model {pinned_model}, got {kit.model}")
    pins = config.judge_pins()
    actual = kit.prompt_hashes()
    for name, expected in pins.items():
        if actual.get(name) != expected:
            raise JudgePinMismatch(
                f"{name} no longer matches the hash pinned for {config.id}. "
                "Do not edit a judge prompt: make a new version and new pins."
            )
    if set(actual) != set(pins):
        raise JudgePinMismatch(f"judge prompts {sorted(actual)} differ from pins {sorted(pins)}")


def build_identity(
    config: EvalConfig, kit: JudgeKit | None, item_ids: list[str]
) -> dict[str, Any]:
    """The facts stored on a run at creation; a retrieval only run has no judge facts."""
    return {
        "items": sorted(item_ids),
        "config_hash": config.content_hash,
        "generation": config.generation_params(),
        "judge_model": kit.model if kit else None,
        "judge_prompts": kit.prompt_hashes() if kit else {},
        "fingerprint": asdict(config.corpus_fingerprint()),
    }


def differing_keys(stored: dict[str, Any], wanted: dict[str, Any]) -> list[str]:
    """The identity keys on which a stored run and the run being started disagree."""
    keys = sorted(set(stored) | set(wanted))
    return [key for key in keys if stored.get(key) != wanted.get(key)]


class StoredRow(Protocol):
    """What legacy_identity needs from a stored result row."""

    item_id: str
    trace: dict[str, Any]


def legacy_identity(rows: Sequence[StoredRow]) -> dict[str, Any]:
    """Identity of a run stored before eval_runs.identity existed, read from its row traces.

    Each row stored the config hash, judge model and judge prompt hashes it was made with. The
    corpus fingerprint was not stored, so it is absent and a comparison cannot check it.
    """
    meta = next((r.trace for r in rows if "judge_model" in r.trace), {})
    return {
        "legacy": True,
        "items": sorted(r.item_id for r in rows),
        "config_hash": meta.get("config_hash"),
        "judge_model": meta.get("judge_model"),
        "judge_prompts": meta.get("judge_prompts", {}),
    }


def identity_warnings(base: dict[str, Any] | None, cand: dict[str, Any] | None) -> list[str]:
    """Differences that make two runs not comparable on judged metrics, as plain sentences."""
    if base is None or cand is None:
        return ["a run has no stored identity, so its judge and corpus cannot be checked"]
    found = []
    if base.get("judge_model") != cand.get("judge_model"):
        found.append(
            f"judge model differs: {base.get('judge_model')} against {cand.get('judge_model')}"
        )
    if base.get("judge_prompts") != cand.get("judge_prompts"):
        found.append("judge prompt hashes differ, so judged scores are not comparable")
    if "fingerprint" in base and "fingerprint" in cand and base["fingerprint"] != cand[
        "fingerprint"
    ]:
        found.append("corpus fingerprint differs (chunking or embedding), chunk ids are not shared")
    return found
