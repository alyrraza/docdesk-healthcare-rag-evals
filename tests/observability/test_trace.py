"""One trace row per request, written even when the request failed (AC-OBS-01)."""

from __future__ import annotations

import uuid
from decimal import Decimal

import pytest
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from docdesk.db.models.traces import QueryTraceRow
from docdesk.generation.result import AnswerResult, Citation, abstain_output
from docdesk.generation.schema import AnswerOutput
from docdesk.observability.trace import TraceBuilder, write_trace
from docdesk.retrieval.types import RetrievalResult, ScoredChunk

TRACE_ID = "a1" * 16
CHUNK = ScoredChunk(uuid.UUID(int=1), uuid.UUID(int=2), "Doc", "text", 0.8, "both")


def retrieval() -> RetrievalResult:
    return RetrievalResult(
        [CHUNK], "hybrid-n20-k5-rrf60", {"embed": 5.0, "dense": 2.0, "total": 9.0}
    )


def answer() -> AnswerResult:
    output = AnswerOutput(
        evidence_used=["c1"],
        answer="x",
        citations=["c1"],
        confidence="high",
        abstained=False,
        abstain_reason="none",
    )
    result = AnswerResult("x", output)
    result.citations = [Citation("c1", CHUNK.chunk_id, CHUNK.document_id, "Doc", "text", None)]
    result.used_ids, result.dropped_ids = [CHUNK.chunk_id], [uuid.UUID(int=9)]
    result.model, result.tokens_in, result.tokens_out = "openai/gpt-oss-120b", 900, 120
    result.cost_usd, result.llm_calls, result.finish_reason = Decimal("0.0002"), 1, "stop"
    result.flags = ["number 2 not in evidence"]
    result.stage_ms = {"pack": 1.0, "generate": 800.0}
    return result


def test_ac_obs_01_the_row_carries_the_fields_the_spec_lists() -> None:
    builder = TraceBuilder(TRACE_ID, uuid.UUID(int=5), "  What is Aspirin? ")
    builder.add_retrieval(retrieval())
    builder.add_answer(answer(), bundle_id="bundle-abc")
    row = builder.build()
    assert (row.trace_id, row.user_id, row.route) == (TRACE_ID, uuid.UUID(int=5), "documents")
    assert row.config_id == "hybrid-n20-k5-rrf60" and row.prompt_bundle_id == "bundle-abc"
    assert row.retrieved == [{"chunk_id": str(CHUNK.chunk_id), "score": 0.8, "source": "both"}]
    assert row.used_ids == [str(CHUNK.chunk_id)] and row.dropped_ids == [str(uuid.UUID(int=9))]
    assert row.tokens == {"in": 900, "out": 120, "calls": 1, "model": "openai/gpt-oss-120b"}
    assert row.cost_usd == Decimal("0.0002")
    assert row.finish_reason == "stop" and not row.abstained and not row.retry_used
    assert row.validation["flags"] == ["number 2 not in evidence"]


def test_ac_obs_01_stage_timings_from_retrieval_and_generation_are_merged_with_a_total() -> None:
    builder = TraceBuilder(TRACE_ID, None, "q")
    builder.add_retrieval(retrieval())
    builder.add_answer(answer(), bundle_id="b")
    row = builder.build()
    assert {"embed", "dense", "pack", "generate", "total"} <= set(row.stage_ms)
    assert row.total_ms == row.stage_ms["total"] >= 0


def test_ac_obs_01_the_question_is_stored_only_as_a_normalised_hash() -> None:
    first = TraceBuilder(TRACE_ID, None, "  What is Aspirin? ").build()
    second = TraceBuilder(TRACE_ID, None, "what is aspirin?").build()
    assert first.question_hash == second.question_hash and len(first.question_hash) == 64
    assert first.question_text is None


def test_ac_obs_01_an_abstained_answer_records_its_reason_and_error_code() -> None:
    result = AnswerResult("x", abstain_output("system_error"))
    result.error_code, result.retry_used = "output_invalid", True
    builder = TraceBuilder(TRACE_ID, None, "q")
    builder.add_answer(result, bundle_id="b")
    row = builder.build()
    assert row.abstained and row.abstain_reason == "system_error"
    assert row.error_code == "output_invalid" and row.retry_used


def test_ac_obs_01_a_request_that_failed_before_any_stage_still_builds_a_row() -> None:
    builder = TraceBuilder(TRACE_ID, None, "q")
    builder.set_error("internal_error")
    row = builder.build()
    assert row.error_code == "internal_error" and row.retrieved == []


def test_ac_obs_01_a_failing_write_is_swallowed_and_reported_as_false() -> None:
    class BrokenSession:
        def add(self, row: object) -> None:
            raise SQLAlchemyError("database is down")

        def rollback(self) -> None:
            pass

    assert write_trace(BrokenSession(), TraceBuilder(TRACE_ID, None, "q").build()) is False  # type: ignore[arg-type]


@pytest.mark.integration
def test_ac_obs_01_a_written_trace_can_be_read_back(db_session: Session) -> None:
    builder = TraceBuilder("b2" * 16, None, "q")
    builder.add_retrieval(retrieval())
    builder.add_answer(answer(), bundle_id="bundle-abc")
    assert write_trace(db_session, builder.build(), commit=False) is True
    stored = db_session.execute(
        select(QueryTraceRow).where(QueryTraceRow.trace_id == "b2" * 16)
    ).scalar_one()
    assert stored.prompt_bundle_id == "bundle-abc"
    assert stored.tokens["model"] == "openai/gpt-oss-120b"
