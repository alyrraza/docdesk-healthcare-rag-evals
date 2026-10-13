"""The retry request carries the exact validation error (AC-GEN-04)."""

from __future__ import annotations

from pathlib import Path

from docdesk.generation.repair import repair_prompt
from docdesk.guardrails.output import OutputError
from docdesk.prompts.loader import load_prompt

ROOT = Path(__file__).resolve().parents[2]


def test_ac_gen_04_the_retry_prompt_names_the_layer_and_the_message_of_the_failure() -> None:
    prompt = load_prompt(ROOT / "prompts" / "answer" / "answer.v1.md")
    error = OutputError("citations", "cited id c9 was not retrieved")
    rendered = repair_prompt(
        prompt, {"evidence": "[c1] text", "question": "q"}, '{"citations": ["c9"]}', error
    )
    assert "citations: cited id c9 was not retrieved" in rendered.user
    assert '{"citations": ["c9"]}' in rendered.user
    assert "[c1] text" in rendered.user
