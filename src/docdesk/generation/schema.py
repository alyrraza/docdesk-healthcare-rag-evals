"""The structured answer the model must return, exactly as designed in OUTPUTS.md."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

# The one sentence an abstaining answer must contain; fixed so no model can word it differently.
ABSTAIN_SENTENCE = "The provided documents do not contain enough information to answer this."


class AnswerOutput(BaseModel):
    """Evidence fields come first so the model lists what it relies on before it answers."""

    model_config = ConfigDict(extra="forbid")

    evidence_used: list[str]
    answer: str
    citations: list[str]
    confidence: Literal["high", "medium", "low"]
    abstained: bool
    abstain_reason: Literal[
        "none", "no_evidence", "weak_evidence", "out_of_scope", "unsafe_request", "system_error"
    ]
