"""Citation membership: a model may only cite evidence it was actually shown (AC-GEN-02)."""

from __future__ import annotations

from collections.abc import Collection

from docdesk.generation.schema import AnswerOutput
from docdesk.guardrails.errors import OutputError


def check_citations(output: AnswerOutput, allowed_labels: Collection[str]) -> None:
    """Reject the answer if it cites or relies on an id outside the evidence in the prompt."""
    unknown = sorted(set(output.citations + output.evidence_used) - set(allowed_labels))
    if unknown:
        raise OutputError("citations", f"unknown evidence ids: {', '.join(unknown)}")
