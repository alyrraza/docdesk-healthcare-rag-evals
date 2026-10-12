"""Typed application error and the handlers that render the standard error envelope."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger(__name__)

UNKNOWN_TRACE_ID = "unknown"


class AppError(Exception):
    """A failure we chose to raise, so callers get a stable code instead of raw text."""

    def __init__(self, code: str, message: str, status: int) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


def error_response(request: Request, code: str, message: str, status: int) -> JSONResponse:
    """Build the one error shape every client can rely on, with the trace id."""
    trace_id = getattr(request.state, "trace_id", UNKNOWN_TRACE_ID)
    body = {"error": {"code": code, "message": message, "trace_id": trace_id}}
    return JSONResponse(status_code=status, content=body)


async def handle_app_error(request: Request, exc: AppError) -> JSONResponse:
    """Render our own typed errors as they are."""
    return error_response(request, exc.code, exc.message, exc.status)


async def handle_http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    """Wrap framework errors such as 404 so they match the envelope too."""
    code = "not_found" if exc.status_code == 404 else "http_error"
    return error_response(request, code, str(exc.detail), exc.status_code)


async def handle_validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Report bad input as 422 without echoing the submitted values back."""
    fields = ", ".join(".".join(str(p) for p in e["loc"]) for e in exc.errors())
    return error_response(request, "invalid_request", f"Invalid fields: {fields}", 422)


async def handle_unexpected_error(request: Request, exc: Exception) -> JSONResponse:
    """Log the real cause with the trace id and return a generic 500."""
    trace_id = getattr(request.state, "trace_id", UNKNOWN_TRACE_ID)
    logger.error("unhandled error", exc_info=exc, extra={"trace_id": trace_id})
    return error_response(request, "internal_error", "Something went wrong", 500)


def register_error_handlers(app: FastAPI) -> None:
    """Attach every handler in one call so create_app cannot forget one."""
    app.add_exception_handler(AppError, handle_app_error)
    app.add_exception_handler(StarletteHTTPException, handle_http_error)
    app.add_exception_handler(RequestValidationError, handle_validation_error)
    app.add_exception_handler(Exception, handle_unexpected_error)
