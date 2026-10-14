"""POST /retrieve: show what retrieval finds for a question, with no model call."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from docdesk.api.query_deps import get_encoder
from docdesk.api.schemas.query import QueryRequest
from docdesk.api.schemas.retrieve import RetrieveOut
from docdesk.auth.deps import require_user
from docdesk.auth.jwt import TokenClaims
from docdesk.db.session import get_session
from docdesk.query.service import RETRIEVAL_CONFIG
from docdesk.retrieval.retriever import QueryEncoder, retrieve

router = APIRouter()


@router.post("/retrieve")
def retrieve_chunks(
    body: QueryRequest,
    request: Request,
    claims: TokenClaims = Depends(require_user),
    session: Session = Depends(get_session),
    encoder: QueryEncoder = Depends(get_encoder),
) -> dict[str, object]:
    """Let the web page show the evidence even when the model is not configured."""
    result = retrieve(session, encoder, body.question, claims.user_id, RETRIEVAL_CONFIG)
    data = RetrieveOut.from_result(result).model_dump()
    return {"data": data, "trace_id": request.state.trace_id}
