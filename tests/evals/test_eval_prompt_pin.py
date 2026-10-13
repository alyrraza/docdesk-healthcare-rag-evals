"""B0 pins the exact answer.v1 text, so editing that prompt cannot move the baseline."""

from __future__ import annotations

from pathlib import Path

import pytest

from docdesk.evals.config import PromptPinMismatch, load_eval_config
from docdesk.prompts.loader import PromptFile, load_prompt, parse_prompt

ROOT = Path(__file__).resolve().parents[2]
B0_PATH = ROOT / "evals" / "configs" / "b0.toml"
ANSWER_V1 = ROOT / "prompts" / "answer" / "answer.v1.md"


def edited(prompt: PromptFile, old: str, new: str) -> PromptFile:
    """The same prompt file with one phrase changed, parsed again like a real edit would be."""
    assert old in prompt.text
    return parse_prompt(prompt.text.replace(old, new, 1))


def test_ac_prm_01_b0_pins_the_hash_of_the_shipped_answer_v1() -> None:
    config = load_eval_config(B0_PATH)
    assert len(config.values["prompt"]["content_hash"]) == 64
    config.check_prompt(load_prompt(ANSWER_V1))


def test_ac_prm_01_an_edited_answer_v1_is_refused_and_told_to_become_a_new_version() -> None:
    config = load_eval_config(B0_PATH)
    changed = edited(load_prompt(ANSWER_V1), "ONLY the evidence", "the evidence")
    with pytest.raises(PromptPinMismatch, match="new version"):
        config.check_prompt(changed)


def test_ac_prm_01_another_version_of_the_same_prompt_is_refused() -> None:
    config = load_eval_config(B0_PATH)
    other = edited(load_prompt(ANSWER_V1), "version: 1.0.0", "version: 1.1.0")
    with pytest.raises(PromptPinMismatch, match="1.1.0"):
        config.check_prompt(other)


def test_ac_prm_01_another_prompt_name_is_refused() -> None:
    config = load_eval_config(B0_PATH)
    router = load_prompt(ROOT / "prompts" / "router" / "router.v1.md")
    with pytest.raises(PromptPinMismatch, match="router"):
        config.check_prompt(router)
