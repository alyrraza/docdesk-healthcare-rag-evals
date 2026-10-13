"""The whole answer flow with a fake model (AC-GEN-01 to AC-GEN-04, AC-GEN-06)."""

from __future__ import annotations

import json
import uuid
from pathlib import Path

from docdesk.context.budget import ContextBudget
from docdesk.generation.abstain import AbstainPolicy
from docdesk.generation.answer import generate_answer
from docdesk.generation.schema import ABSTAIN_SENTENCE
from docdesk.guardrails.policy import DISCLAIMER
from docdesk.llm.errors import LLMTimeoutError
from docdesk.prompts.loader import load_prompt
from docdesk.retrieval.types import RetrievalResult, ScoredChunk
from fakes.ingestion import WordCounter
from fakes.llm import FakeLLMClient

ROOT = Path(__file__).resolve().parents[2]
PROMPT = load_prompt(ROOT / "prompts" / "answer" / "answer.v1.md")
CONFIG = "hybrid-n20-k5-rrf60"


def chunk(n: int, text: str, score: float = 0.9) -> ScoredChunk:
    return ScoredChunk(
        uuid.UUID(int=n), uuid.UUID(int=100 + n), f"Label {n}", text, score, "dense", 3
    )


def retrieval(*chunks: ScoredChunk) -> RetrievalResult:
    return RetrievalResult(list(chunks), CONFIG)


def good(citations: list[str], answer: str = "Aspirin can cause stomach bleeding.") -> str:
    return json.dumps(
        {
            "evidence_used": citations,
            "answer": answer,
            "citations": citations,
            "confidence": "high",
            "abstained": False,
            "abstain_reason": "none",
        }
    )


def run(client: FakeLLMClient, result: RetrievalResult | None = None, policy=None):
    chunks = result or retrieval(
        chunk(1, "Aspirin can cause stomach bleeding."), chunk(2, "Other.")
    )
    return generate_answer(
        "What are the risks of aspirin?",
        chunks,
        llm=client,
        prompt=PROMPT,
        counter=WordCounter(),
        budget=ContextBudget(),
        model="fake-model",
        abstain_policy=policy or AbstainPolicy({}, default=0.0),
    )


def test_ac_gen_01_a_valid_reply_becomes_an_answer_with_citations_and_the_disclaimer() -> None:
    client = FakeLLMClient([good(["c1"])])
    result = run(client)
    assert not result.abstained and not result.retry_used
    assert result.answer.endswith(DISCLAIMER)
    assert result.answer.startswith("Aspirin can cause stomach bleeding.")
    citation = result.citations[0]
    assert (citation.label, citation.chunk_id, citation.document_title, citation.page) == (
        "c1",
        uuid.UUID(int=1),
        "Label 1",
        3,
    )
    assert citation.text == "Aspirin can cause stomach bleeding."
    assert len(client.requests) == 1


def test_ac_ctx_03_the_request_carries_the_question_and_the_evidence_inside_delimiters() -> None:
    client = FakeLLMClient([good(["c1"])])
    run(client)
    request = client.requests[0]
    assert "<evidence>\n[c1] Label 1\nAspirin can cause stomach bleeding." in request.user
    assert "What are the risks of aspirin?" in request.user
    assert "stomach bleeding" not in request.system
    assert (request.model, request.temperature, request.max_output_tokens) == (
        "fake-model",
        0,
        600,
    )


def test_ac_gen_03_empty_retrieval_abstains_without_calling_the_model() -> None:
    client = FakeLLMClient([])
    result = run(client, retrieval())
    assert result.abstained and result.output.abstain_reason == "no_evidence"
    assert ABSTAIN_SENTENCE in result.answer and result.answer.endswith(DISCLAIMER)
    assert client.requests == [] and result.llm_calls == 0


def test_ac_gen_03_a_weak_best_score_abstains_without_calling_the_model() -> None:
    client = FakeLLMClient([])
    policy = AbstainPolicy({CONFIG: 0.5})
    result = run(client, retrieval(chunk(1, "text", score=0.1)), policy)
    assert result.output.abstain_reason == "weak_evidence"
    assert client.requests == []


def test_ac_gen_04_invalid_json_is_retried_once_with_the_exact_error_in_the_prompt() -> None:
    client = FakeLLMClient(["not json at all", good(["c1"])])
    result = run(client)
    assert result.retry_used and result.llm_calls == 2
    assert not result.abstained
    retry = client.requests[1]
    assert "Problem found: schema:" in retry.user
    assert "not json at all" in retry.user
    assert retry.system == client.requests[0].system


def test_ac_gen_02_a_citation_of_an_unretrieved_id_triggers_the_retry() -> None:
    client = FakeLLMClient([good(["c9"]), good(["c1"])])
    result = run(client)
    assert result.retry_used and not result.abstained
    assert "unknown evidence ids: c9" in client.requests[1].user


def test_ac_gen_04_a_reply_cut_off_by_the_length_limit_counts_as_invalid() -> None:
    client = FakeLLMClient([good(["c1"]), good(["c1"])], finish_reasons=["length"])
    result = run(client)
    assert result.retry_used


def test_ac_gen_04_two_invalid_replies_give_the_typed_fallback_and_never_a_third_call() -> None:
    client = FakeLLMClient(["bad one", "bad two"])
    result = run(client)
    assert len(client.requests) == 2
    assert result.abstained and result.output.abstain_reason == "system_error"
    assert result.citations == [] and result.answer.endswith(DISCLAIMER)
    assert result.raw_output == "bad two"
    assert result.error_code == "output_invalid"


def test_ac_gen_04_a_provider_failure_gives_the_fallback_instead_of_raising() -> None:
    client = FakeLLMClient([LLMTimeoutError("slow")])
    result = run(client)
    assert result.abstained and result.output.abstain_reason == "system_error"
    assert result.error_code == "llm_timeout"
    assert len(client.requests) == 1


def test_ac_gen_01_a_model_that_abstains_correctly_passes_through() -> None:
    reply = json.dumps(
        {
            "evidence_used": [],
            "answer": ABSTAIN_SENTENCE,
            "citations": [],
            "confidence": "low",
            "abstained": True,
            "abstain_reason": "no_evidence",
        }
    )
    result = run(FakeLLMClient([reply]))
    assert result.abstained and result.output.abstain_reason == "no_evidence"
    assert result.llm_calls == 1 and result.error_code is None


def test_ac_gen_01_a_number_missing_from_the_cited_evidence_is_flagged_not_changed() -> None:
    reply = good(["c1"], "Aspirin raises bleeding risk by 40 percent.")
    result = run(FakeLLMClient([reply]))
    assert "40 percent" in result.answer
    assert result.flags and "40" in result.flags[0]


def test_ac_obs_03_tokens_and_calls_are_added_up_over_the_retry() -> None:
    client = FakeLLMClient(["bad", good(["c1"])])
    result = run(client)
    assert result.tokens_in > 0 and result.tokens_out > 0
    assert result.model == "fake-model" and result.llm_calls == 2


def test_ac_ctx_02_used_and_dropped_ids_are_returned_for_the_trace() -> None:
    chunks = retrieval(chunk(1, "one two three"), chunk(2, "word " * 5000))
    result = run(FakeLLMClient([good(["c1"])]), chunks)
    assert result.used_ids == [uuid.UUID(int=1)]
    assert result.dropped_ids == [uuid.UUID(int=2)]
