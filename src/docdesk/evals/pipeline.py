"""What the runner needs from a pipeline, as plain data, so a test can pass a fake one."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Protocol

from docdesk.evals.outcome import Outcome
from docdesk.generation.result import CallUsage


@dataclass
class PipelineOutput:
    """One question's journey, with chunk ids as strings to match the golden gold sets."""

    # None when generation was not run (retrieval only mode).
    outcome: Outcome | None
    retrieval_ran: bool = True
    packed: bool = False
    candidate_ids: list[str] = field(default_factory=list)
    retrieved_ids: list[str] = field(default_factory=list)
    used_ids: list[str] = field(default_factory=list)
    cited_ids: list[str] = field(default_factory=list)
    # The answer text without the disclaimer, and the evidence text the model was shown.
    answer: str = ""
    context: str = ""
    abstain_reason: str | None = None
    tokens_in: int = 0
    tokens_out: int = 0
    cost_usd: Decimal = Decimal("0")
    cache_hits: int = 0
    llm_calls: int = 0
    # Generator calls one by one, for the per run token accounting.
    calls: list[CallUsage] = field(default_factory=list)


class Pipeline(Protocol):
    """Anything that can answer one eval question; the real one wraps retrieval and generation."""

    def run(self, question: str, *, retrieval_only: bool) -> PipelineOutput:
        """Retrieve, and unless retrieval_only, generate. Must not call a judge."""
        ...
