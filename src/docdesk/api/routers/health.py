"""Liveness route."""

from __future__ import annotations

from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/health")
def health(request: Request) -> dict[str, object]:
    """Let a load balancer or CI check that the process is up, without touching the database."""
    return {"data": {"status": "ok"}, "trace_id": request.state.trace_id}
