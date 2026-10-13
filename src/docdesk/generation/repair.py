"""Builds the single retry request: the original prompt plus the exact reason it was rejected."""

from __future__ import annotations

from docdesk.guardrails.errors import OutputError
from docdesk.prompts.loader import PromptFile
from docdesk.prompts.renderer import RenderedPrompt, render


def repair_prompt(
    prompt: PromptFile, variables: dict[str, str], previous_output: str, error: OutputError
) -> RenderedPrompt:
    """Retrying with the same prompt tends to repeat the mistake, so the error goes in the retry."""
    repair = {"previous_output": previous_output, "validation_error": str(error)}
    return render(prompt, variables, repair=repair)
