"""FastAPI application factory."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response

from docdesk.api.routers import auth, health
from docdesk.core.errors import register_error_handlers
from docdesk.core.ids import new_trace_id
from docdesk.core.logging import bind_trace_id


async def add_trace_id(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Give every request one trace id for logs, error bodies and the response header."""
    trace_id = new_trace_id()
    request.state.trace_id = trace_id
    bind_trace_id(trace_id)
    response = await call_next(request)
    response.headers["x-trace-id"] = trace_id
    return response


def create_app() -> FastAPI:
    """Build the app in a function so tests get a fresh instance each time."""
    app = FastAPI(title="DocDesk v2")
    app.middleware("http")(add_trace_id)
    register_error_handlers(app)
    app.include_router(health.router)
    app.include_router(auth.router)
    return app
