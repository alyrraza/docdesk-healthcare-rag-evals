"""Answering one question end to end: retrieve, generate, trace."""

from __future__ import annotations

import logging
import uuid

from sqlalchemy.orm import Session

from docdesk.context.budget import ContextBudget
from docdesk.generation.abstain import AbstainPolicy
from docdesk.generation.answer import generate_answer
from docdesk.generation.result import AnswerResult
from docdesk.ingestion.types import TokenCounting
from docdesk.llm.client import LLMClient
from docdesk.observability.trace import TraceBuilder, write_trace
from docdesk.prompts.bundle import BundleParts, bundle_id
from docdesk.prompts.loader import PromptFile
from docdesk.retrieval.retriever import QueryEncoder, retrieve
from docdesk.retrieval.types import RetrievalConfig

log = logging.getLogger(__name__)

# Phase 3 starting setup. The abstain threshold is a placeholder (0 means: only empty retrieval
# abstains) until the dev split is used to tune it per config id in phase 4.
RETRIEVAL_CONFIG = RetrievalConfig()
ABSTAIN_POLICY = AbstainPolicy({}, default=0.0)
BUDGET = ContextBudget()


def answer_question(
    session: Session,
    *,
    trace_id: str,
    user_id: uuid.UUID,
    question: str,
    encoder: QueryEncoder,
    counter: TokenCounting,
    llm: LLMClient,
    prompt: PromptFile,
    model: str,
) -> AnswerResult:
    """Answer from the user's own and shared documents, and always leave one trace row."""
    trace = TraceBuilder(trace_id, user_id, question)
    try:
        retrieval = retrieve(session, encoder, question, user_id, RETRIEVAL_CONFIG)
        trace.add_retrieval(retrieval)
        result = generate_answer(
            question,
            retrieval,
            llm=llm,
            prompt=prompt,
            counter=counter,
            budget=BUDGET,
            model=model,
            abstain_policy=ABSTAIN_POLICY,
        )
        parts = BundleParts(
            prompt.name,
            prompt.version,
            prompt.content_hash,
            model,
            prompt.params,
            prompt.schema,
            retrieval.config_id,
        )
        trace.add_answer(result, bundle_id(parts))
    except Exception:
        trace.set_error("internal_error")
        log.exception("query failed")
        raise
    finally:
        write_trace(session, trace.build())
    return result
