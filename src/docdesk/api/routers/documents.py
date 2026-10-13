"""Document routes: upload now, process later."""

from __future__ import annotations

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
