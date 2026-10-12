"""Register and login routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from docdesk.api.schemas.auth import RegisterRequest, UserOut
from docdesk.auth import service
from docdesk.db.session import get_session

router = APIRouter(prefix="/auth")


@router.post("/register", status_code=201)
def register(
    body: RegisterRequest, request: Request, session: Session = Depends(get_session)
) -> dict[str, object]:
    """Let a person create an account (AC-AUTH-01)."""
    user = service.register_user(session, body.email, body.password)
    out = UserOut(id=str(user.id), email=user.email, role=user.role)
    return {"data": out.model_dump(), "trace_id": request.state.trace_id}
