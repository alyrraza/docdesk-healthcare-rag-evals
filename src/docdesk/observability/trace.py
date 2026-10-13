"""Collects what happened during one request and writes it as one trace row (AC-OBS-01)."""

from __future__ import annotations

import hashlib
import logging
import time
import uuid

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from docdesk.core import clock
from docdesk.db.models.traces import QueryTraceRow
from docdesk.generation.result import AnswerResult
from docdesk.retrieval.types import RetrievalResult

log = logging.getLogger(__name__)


def output_outcome(answer: AnswerResult) -> str | None:
    """Say how the output checks ended, or None when there was no model reply to check."""
    if answer.llm_calls == 0:
        return None
    if answer.error_code == "output_invalid" or (answer.error_code and answer.retry_used):
        return "failed"
    if answer.error_code:
        return None  # the provider failed on the first call, so no output was ever checked
    return "retried" if answer.retry_used else "passed"


def question_hash(question: str) -> str:
    """Hash the normalised question, so repeats can be counted without storing the text."""
    return hashlib.sha256(" ".join(question.casefold().split()).encode("utf-8")).hexdigest()


class TraceBuilder:
    """Created when a request starts, filled as stages finish, built once at the end."""

    def __init__(self, trace_id: str, user_id: uuid.UUID | None, question: str) -> None:
        self._started = time.perf_counter()
        self._row = QueryTraceRow(
            trace_id=trace_id,
            user_id=user_id,
            created_at=clock.utc_now(),
            route="documents",
            question_hash=question_hash(question),
            retrieved=[],
            used_ids=[],
            dropped_ids=[],
            stage_ms={},
            tokens={},
            guardrails={},
            validation={},
            # Always False: the semantic cache is built in Phase 6, nothing can hit it before.
            cache_hit=False,
            abstained=False,
            retry_used=False,
        )

    def add_retrieval(self, result: RetrievalResult) -> None:
        """Record the config, every retrieved chunk with its score and the retrieval timings."""
        self._row.config_id = result.config_id
        self._row.retrieved = [
            {"chunk_id": str(c.chunk_id), "score": c.score, "source": c.source}
            for c in result.chunks
        ]
        self._row.stage_ms = {**self._row.stage_ms, **result.timings_ms}

    def add_answer(self, answer: AnswerResult, bundle_id: str | None) -> None:
        """Record what the answer flow decided and what it cost."""
        row = self._row
        row.prompt_bundle_id = bundle_id
        row.used_ids = [str(i) for i in answer.used_ids]
        row.dropped_ids = [str(i) for i in answer.dropped_ids]
        row.tokens = {
            "in": answer.tokens_in,
            "out": answer.tokens_out,
            "calls": answer.llm_calls,
            "model": answer.model,
        }
        row.cost_usd = answer.cost_usd
        row.abstained = answer.abstained
        row.abstain_reason = answer.output.abstain_reason if answer.abstained else None
        row.retry_used = answer.retry_used
        row.finish_reason = answer.finish_reason
        row.error_code = answer.error_code or row.error_code
        outcome = output_outcome(answer)
        if outcome:
            self.add_guardrail("output", outcome)
        row.validation = {"flags": answer.flags, "raw_output_kept": answer.raw_output is not None}
        row.stage_ms = {**row.stage_ms, **answer.stage_ms}

    def add_guardrail(self, name: str, outcome: str) -> None:
        """Record what an input or output guardrail decided, for review of refusals."""
        self._row.guardrails = {**self._row.guardrails, name: outcome}

    def set_error(self, code: str) -> None:
        """Mark the request as failed, so a crash still leaves a trace."""
        self._row.error_code = code

    def build(self) -> QueryTraceRow:
        """Finish the row with the total time; call it once, in a finally block."""
        total = (time.perf_counter() - self._started) * 1000.0
        self._row.stage_ms = {**self._row.stage_ms, "total": total}
        self._row.total_ms = total
        return self._row


def write_trace(session: Session, row: QueryTraceRow, *, commit: bool = True) -> bool:
    """Save the row; a failed write is logged and never fails the user's request."""
    try:
        session.add(row)
        if commit:
            session.commit()
        else:
            session.flush()
    except SQLAlchemyError as error:
        log.error("could not write trace %s: %s", row.trace_id, type(error).__name__)
        session.rollback()
        return False
    return True
