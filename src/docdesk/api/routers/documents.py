"""Document routes: upload now, process later."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Query, Request, Response
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from docdesk.api.deps import Enqueue, get_enqueue, get_file_store
from docdesk.api.schemas.documents import DocumentOut, UploadOut
from docdesk.auth.deps import require_user
from docdesk.auth.jwt import TokenClaims
from docdesk.core.config import Settings, get_settings
from docdesk.core.errors import AppError
from docdesk.db.session import get_session
from docdesk.documents import service
from docdesk.ingestion.filestore import LocalFileStore

router = APIRouter(prefix="/documents")


async def read_limited_body(request: Request, max_bytes: int) -> bytes:
    """Read the upload but stop once it passes the limit, so a huge body cannot fill memory."""
    received = bytearray()
    async for part in request.stream():
        received.extend(part)
        if len(received) > max_bytes:
            raise AppError("file_too_large", f"The file is larger than {max_bytes} bytes", 413)
    return bytes(received)


@router.post("", status_code=202)
async def upload_document(
    request: Request,
    response: Response,
    title: str = Query(min_length=1, max_length=500),
    claims: TokenClaims = Depends(require_user),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
    store: LocalFileStore = Depends(get_file_store),
    enqueue: Enqueue = Depends(get_enqueue),
) -> dict[str, object]:
    """Accept the file as the raw request body and return 202 before any embedding (AC-ING-01)."""
    data = await read_limited_body(request, settings.max_upload_bytes)
    document, duplicate = await run_in_threadpool(
        service.submit_document, session, store, enqueue, claims.user_id, title, data
    )
    if duplicate:
        response.status_code = 200
    out = UploadOut(**DocumentOut.from_document(document).model_dump(), duplicate=duplicate)
    return {"data": out.model_dump(), "trace_id": request.state.trace_id}


@router.get("")
def list_documents(
    request: Request,
    claims: TokenClaims = Depends(require_user),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    """Show the caller's documents and the shared corpus, newest first."""
    documents = service.list_documents(session, claims.user_id)
    data = [DocumentOut.from_document(document).model_dump() for document in documents]
    return {"data": data, "trace_id": request.state.trace_id}


@router.get("/{document_id}")
def get_document(
    document_id: uuid.UUID,
    request: Request,
    claims: TokenClaims = Depends(require_user),
    session: Session = Depends(get_session),
) -> dict[str, object]:
    """Show one document's status, so the page can poll until it is ready or failed."""
    document = service.get_visible_document(session, claims.user_id, document_id)
    return {
        "data": DocumentOut.from_document(document).model_dump(),
        "trace_id": request.state.trace_id,
    }
