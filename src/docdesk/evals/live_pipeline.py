"""The real pipeline for eval runs: policy check, retrieval, answer flow. No trace is written."""

from __future__ import annotations

import uuid
from dataclasses import replace

from sqlalchemy.orm import Session

from docdesk.context.packer import format_item
from docdesk.evals.config import EvalConfig
from docdesk.evals.outcome import Outcome
from docdesk.evals.pipeline import PipelineOutput
from docdesk.generation.abstain import AbstainPolicy
from docdesk.generation.answer import generate_answer
from docdesk.generation.result import AnswerResult
from docdesk.guardrails.input import check_policy
from docdesk.guardrails.policy import REFUSAL_MESSAGE
from docdesk.ingestion.types import TokenCounting
from docdesk.llm.client import LLMClient
from docdesk.prompts.loader import PromptFile
from docdesk.retrieval.retriever import QueryEncoder, retrieve
from docdesk.retrieval.types import RetrievalResult


def outcome_of(result: AnswerResult) -> Outcome:
    """Map the answer flow's result to the four outcomes the metrics know."""
    reason = result.output.abstain_reason
    if reason == "system_error":
        return "error"
    if reason == "unsafe_request":
        return "refused"
    return "abstained" if result.abstained else "answered"


class LivePipeline:
    """Runs one question the way POST /query does, with the settings of the pinned config."""

    def __init__(
        self,
        *,
        session: Session,
        encoder: QueryEncoder,
        counter: TokenCounting,
        llm: LLMClient | None,
        prompt: PromptFile,
        config: EvalConfig,
        user_id: uuid.UUID,
    ) -> None:
        """llm may be None for retrieval only runs, which must never reach a model."""
        self._session, self._encoder, self._counter = session, encoder, counter
        self._llm, self._prompt, self._config, self._user = llm, prompt, config, user_id

    def run(self, question: str, *, retrieval_only: bool) -> PipelineOutput:
        """Refuse by policy, else retrieve, and unless retrieval_only, generate."""
        if not retrieval_only and check_policy(question).refused:
            return PipelineOutput(outcome="refused", retrieval_ran=False, answer=REFUSAL_MESSAGE)
        settings = self._config.retrieval_config()
        # Retrieve all top_n candidates so the labeler can tell a ranking miss from a retrieval
        # miss, then cut to top_k. For a dense config this gives the same top_k as asking for k.
        every = replace(settings, top_k=settings.top_n)
        wide = retrieve(self._session, self._encoder, question, self._user, every)
        top = RetrievalResult(wide.chunks[: settings.top_k], settings.config_id, wide.timings_ms)
        output = PipelineOutput(
            outcome=None,
            candidate_ids=[str(c.chunk_id) for c in wide.chunks],
            retrieved_ids=[str(c.chunk_id) for c in top.chunks],
        )
        if retrieval_only:
            return output
        return self.generate(question, top, output)

    def generate(
        self, question: str, top: RetrievalResult, output: PipelineOutput
    ) -> PipelineOutput:
        """Run the answer flow on the retrieved chunks and copy the facts the metrics need."""
        assert self._llm is not None, "a full run needs a model client"
        values = self._config.values
        result = generate_answer(
            question,
            top,
            llm=self._llm,
            prompt=self._prompt,
            counter=self._counter,
            budget=self._config.context_budget(),
            model=values["models"]["generator"],
            abstain_policy=AbstainPolicy({}, default=values["abstain"]["threshold"]),
            max_per_document=values["packer"]["max_per_document"],
        )
        used = {chunk_id: n for n, chunk_id in enumerate(result.used_ids, start=1)}
        packed_chunks = sorted(
            (c for c in top.chunks if c.chunk_id in used), key=lambda c: used[c.chunk_id]
        )
        output.outcome = outcome_of(result)
        output.packed = bool(result.used_ids or result.dropped_ids)
        output.used_ids = [str(i) for i in result.used_ids]
        output.cited_ids = [str(c.chunk_id) for c in result.citations]
        output.answer = result.output.answer
        output.context = "\n\n".join(
            format_item(f"c{n}", chunk) for n, chunk in enumerate(packed_chunks, start=1)
        )
        output.abstain_reason = result.output.abstain_reason
        output.tokens_in, output.tokens_out = result.tokens_in, result.tokens_out
        output.cost_usd, output.llm_calls = result.cost_usd, result.llm_calls
        return output
