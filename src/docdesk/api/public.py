"""The allowlist of routes that need no login, and the walk that enforces it (AC-AUTH-05)."""

from __future__ import annotations

from collections.abc import Iterator

from fastapi import FastAPI
from fastapi.dependencies.models import Dependant
from fastapi.security.base import SecurityBase
from starlette.routing import Mount

from docdesk.core.config import Settings

# (METHOD, path). Adding a line here is a deliberate decision to expose a route to everyone.
PUBLIC_ROUTES: frozenset[tuple[str, str]] = frozenset(
    {
        ("GET", "/health"),
        ("POST", "/auth/register"),
        ("POST", "/auth/login"),
    }
)

# Public only while Settings.public_docs_enabled is true (not in production).
DOCS_ROUTES: frozenset[tuple[str, str]] = frozenset(
    {
        ("GET", "/docs"),
        ("GET", "/redoc"),
        ("GET", "/openapi.json"),
        ("GET", "/docs/oauth2-redirect"),
    }
)

IGNORED_METHODS = {"HEAD", "OPTIONS"}


def public_routes(settings: Settings) -> frozenset[tuple[str, str]]:
    """Build the allowlist for this environment so production never lists the docs."""
    return PUBLIC_ROUTES | DOCS_ROUTES if settings.public_docs_enabled else PUBLIC_ROUTES


def uses_bearer_security(dependant: Dependant) -> bool:
    """Check a dependency tree for a security scheme, since only require_user adds one."""
    return isinstance(dependant.call, SecurityBase) or any(
        uses_bearer_security(child) for child in dependant.dependencies
    )


def walk_routes(routes: list, prefix: str = "") -> Iterator[tuple[str, str, bool]]:
    """Yield (method, path, requires_login) for the real routes, descending into routers and mounts.

    Real routes are used instead of the OpenAPI schema because the schema leaves out
    routes declared with include_in_schema=False. Newer FastAPI wraps each included router
    in an object with effective_candidates(), which already carries the prefix and the
    include-level dependencies; older FastAPI keeps a flat list, which the same loop handles.
    """
    for route in routes:
        if hasattr(route, "effective_candidates"):
            yield from walk_routes(route.effective_candidates(), prefix)
            continue
        real = getattr(route, "starlette_route", None) or route
        path = prefix + getattr(real, "path", "")
        if isinstance(real, Mount):
            if real.routes:
                yield from walk_routes(real.routes, path)
            else:
                yield "MOUNT", path, False  # an opaque app (static files) cannot be checked
            continue
        dependant = getattr(real, "dependant", None)
        protected = dependant is not None and uses_bearer_security(dependant)
        methods = getattr(real, "methods", None) or {"WEBSOCKET"}
        for method in sorted(methods - IGNORED_METHODS):
            yield method, path, protected


def all_operations(app: FastAPI) -> dict[tuple[str, str], bool]:
    """Map every (METHOD, path) to whether it requires a login."""
    return {(method, path): protected for method, path, protected in walk_routes(app.routes)}


def find_unprotected_routes(app: FastAPI, settings: Settings) -> set[tuple[str, str]]:
    """Return routes with no login requirement that are not in this environment's allowlist."""
    allowed = public_routes(settings)
    operations = all_operations(app)
    return {key for key, protected in operations.items() if not protected and key not in allowed}
