"""T096: the real pipeline adapter, with a fake encoder and a fake model (no network)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from sqlalchemy.orm import Session

from docdesk.evals.config import load_eval_config
from docdesk.evals.live_pipeline import LivePipeline
from docdesk.llm.errors import ProviderError
from docdesk.prompts.loader import load_prompt
from fakes.corpus import Corpus, FixedEncoder
from fakes.ingestion import WordCounter
from fakes.llm import FakeLLMClient

pytestmark = pytest.mark.integration

ROOT = Path(__file__).resolve().parents[2]
CONFIG = load_eval_config(ROOT / "evals" / "configs" / "b0.toml")
PROMPT = load_prompt(ROOT / "prompts" / "answer" / "answer.v1.md")
ANSWER = json.dumps({
    "evidence_used": ["c1"], "answer": "Take it with food.", "citations": ["c1"],
    "confidence": "high", "abstained": False, "abstain_reason": "none",
})


@pytest.fixture
def corpus(db_session: Session) -> Corpus:
    return Corpus(db_session)


def build(db_session: Session, corpus: Corpus, llm: FakeLLMClient | None):
    user = corpus.user()
    doc = corpus.document(user, shared=True)
    chunks = [corpus.chunk(doc, f"Chunk text number {n} about famotidine.", hot=n, position=n)
              for n in range(8)]
    pipeline = LivePipeline(
        session=db_session, encoder=FixedEncoder(0), counter=WordCounter(), llm=llm,
        prompt=PROMPT, config=CONFIG, user_id=user,
    )
    return pipeline, chunks


def test_ac_evl_02_live_01_retrieval_only_makes_no_model_call(
    db_session: Session, corpus: Corpus
) -> None:
    pipeline, chunks = build(db_session, corpus, llm=None)
    out = pipeline.run("What about famotidine?", retrieval_only=True)
    assert out.outcome is None and out.answer == ""
    assert out.retrieved_ids[0] == str(chunks[0].id)
    assert len(out.retrieved_ids) == 5 and len(out.candidate_ids) == 8  # top_k 5, top_n 20


def test_ac_evl_03_live_02_full_run_returns_answer_ids_context_and_tokens(
    db_session: Session, corpus: Corpus
) -> None:
    client = FakeLLMClient([ANSWER])
    pipeline, chunks = build(db_session, corpus, client)
    out = pipeline.run("What about famotidine?", retrieval_only=False)
    assert out.outcome == "answered" and out.answer == "Take it with food."
    assert out.cited_ids == [str(chunks[0].id)]
    assert out.packed and out.used_ids[0] == str(chunks[0].id)
    assert out.context.startswith("[c1] ") and "Chunk text number 0" in out.context
    assert out.tokens_in > 0 and out.llm_calls == 1
    assert client.requests[0].model == CONFIG.values["models"]["generator"]


def test_ac_evl_03_live_03_policy_refusal_skips_retrieval_and_the_model(
    db_session: Session, corpus: Corpus
) -> None:
    client = FakeLLMClient([])
    pipeline, _ = build(db_session, corpus, client)
    out = pipeline.run("How much famotidine should I take tonight?", retrieval_only=False)
    assert out.outcome == "refused" and out.retrieval_ran is False
    assert client.requests == []


def test_ac_evl_03_live_04_a_model_failure_is_an_error_outcome(
    db_session: Session, corpus: Corpus
) -> None:
    pipeline, _ = build(db_session, corpus, FakeLLMClient([ProviderError("boom")]))
    out = pipeline.run("What about famotidine?", retrieval_only=False)
    assert out.outcome == "error"
