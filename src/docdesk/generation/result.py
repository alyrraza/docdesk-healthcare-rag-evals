"""What the answer flow returns: the answer, its citations and everything the trace records."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from decimal import Decimal

from docdesk.generation.schema import ABSTAIN_SENTENCE, AnswerOutput
from docdesk.guardrails.policy import REFUSAL_MESSAGE, with_disclaimer


@dataclass(frozen=True)
class Citation:
    """An evidence item the answer cites, with the text a reader needs to check it."""

    label: str
    chunk_id: uuid.UUID
    document_id: uuid.UUID
    document_title: str
    text: str
    page: int | None


@dataclass(frozen=True)
class CallUsage:
    """One model call: what it used and whether the eval cache answered it (T098b)."""

    model: str
    tokens_in: int
    tokens_out: int
    cost_usd: Decimal
    cache_hit: bool


@dataclass
class AnswerResult:
    """The final answer (disclaimer included) plus the facts the trace needs (AC-OBS-01)."""

    answer: str
    output: AnswerOutput
    citations: list[Citation] = field(default_factory=list)
    used_ids: list[uuid.UUID] = field(default_factory=list)
    dropped_ids: list[uuid.UUID] = field(default_factory=list)
    model: str | None = None
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: Decimal = Decimal("0")
    llm_calls: int = 0
    # One entry per answered model call, so an eval run can split billed from cached tokens.
    calls: list[CallUsage] = field(default_factory=list)
    retry_used: bool = False
    finish_reason: str | None = None
    flags: list[str] = field(default_factory=list)
    # Set when the typed fallback was returned; the raw reply is kept for review, not shown.
    error_code: str | None = None
    raw_output: str | None = None
    stage_ms: dict[str, float] = field(default_factory=dict)

    @property
    def abstained(self) -> bool:
        """Whether the system declined to answer, for any reason."""
        return self.output.abstained


def abstain_output(reason: str) -> AnswerOutput:
    """The typed output for an answer the system gave up on, never written by a model."""
    return AnswerOutput(
        evidence_used=[],
        answer=ABSTAIN_SENTENCE,
        citations=[],
        confidence="low",
        abstained=True,
        abstain_reason=reason,  # type: ignore[arg-type]
    )


def refusal_result() -> AnswerResult:
    """The fixed answer for a personal dose or diagnosis request; no model is called."""
    output = AnswerOutput(
        evidence_used=[],
        answer=REFUSAL_MESSAGE,
        citations=[],
        confidence="high",
        abstained=True,
        abstain_reason="unsafe_request",
    )
    return AnswerResult(with_disclaimer(REFUSAL_MESSAGE), output)
