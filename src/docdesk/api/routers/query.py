"""POST /query: parse the question, call the service, shape the response."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from docdesk.api.query_deps import get_answer_prompt, get_encoder, get_llm, get_token_counter
from docdesk.api.schemas.query import QueryOut, QueryRequest
from docdesk.auth.deps import require_user
from docdesk.auth.jwt import TokenClaims
from docdesk.core.config import Settings, get_settings
from docdesk.db.session import get_session
from docdesk.ingestion.types import TokenCounting
from docdesk.llm.client import LLMClient
from docdesk.prompts.loader import PromptFile
from docdesk.query.service import answer_question
from docdesk.retrieval.retriever import QueryEncoder

router = APIRouter()


@router.post("/query")
def query(
    body: QueryRequest,
    request: Request,
    claims: TokenClaims = Depends(require_user),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
    encoder: QueryEncoder = Depends(get_encoder),
    counter: TokenCounting = Depends(get_token_counter),
    llm: LLMClient = Depends(get_llm),
    prompt: PromptFile = Depends(get_answer_prompt),
) -> dict[str, object]:
    """Answer one question from the documents the user may see (AC-OBS-01 trace included)."""
    result = answer_question(
        session,
        trace_id=request.state.trace_id,
        user_id=claims.user_id,
        question=body.question,
        encoder=encoder,
        counter=counter,
        llm=llm,
        prompt=prompt,
        model=settings.generator_model,
    )
    return {"data": QueryOut.from_result(result).model_dump(), "trace_id": request.state.trace_id}
