"""FastAPI application factory."""

from __future__ import annotations

from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response

from docdesk.api.routers import auth, documents, health, query, retrieve
from docdesk.core.config import Settings, get_settings
from docdesk.core.errors import register_error_handlers
from docdesk.core.ids import new_trace_id
from docdesk.core.logging import bind_trace_id
from docdesk.web import routes as web
from docdesk.worker.celery_app import make_celery


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


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the app in a function so tests get a fresh instance each time."""
    settings = settings or get_settings()
    # Binds the ingestion task to the real broker. set_default makes it visible to the threads
    # that run the routes; the plain current app is per thread.
    make_celery(settings.redis_url).set_default()
    docs = settings.public_docs_enabled
    app = FastAPI(
        title="DocDesk v2",
        docs_url="/docs" if docs else None,
        redoc_url="/redoc" if docs else None,
        openapi_url="/openapi.json" if docs else None,
    )
    app.middleware("http")(add_trace_id)
    register_error_handlers(app)
    app.include_router(health.router)
    app.include_router(auth.router)
    app.include_router(documents.router)
    app.include_router(query.router)
    app.include_router(retrieve.router)
    app.include_router(web.router)
    return app
