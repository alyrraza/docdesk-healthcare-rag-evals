"""The JSON shapes the judges must return: labels only, never a score."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel

ClaimVerdict = Literal["supported", "unsupported", "contradicted"]


class ClaimLabel(BaseModel):
    """One claim from the answer and what the evidence says about it."""

    claim: str
    label: ClaimVerdict
    evidence_id: str | None = None


class FaithfulnessJudgement(BaseModel):
    """The whole reply of the faithfulness judge."""

    claims: list[ClaimLabel]
