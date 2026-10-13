"""Builds the single retry request: the original prompt plus the exact reason it was rejected."""

from __future__ import annotations

from docdesk.guardrails.errors import OutputError
from docdesk.prompts.loader import PromptFile
from docdesk.prompts.renderer import RenderedPrompt, render

# The error text can echo ids the model wrote, so it is escaped by the renderer and also cut short.
MAX_ERROR_CHARS = 300


def repair_prompt(
    prompt: PromptFile, variables: dict[str, str], previous_output: str, error: OutputError
) -> RenderedPrompt:
    """Retrying with the same prompt tends to repeat the mistake, so the error goes in the retry."""
    repair = {"previous_output": previous_output, "validation_error": str(error)[:MAX_ERROR_CHARS]}
    return render(prompt, variables, repair=repair)
