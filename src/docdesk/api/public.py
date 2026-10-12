"""The allowlist of routes that need no login, and the walk that enforces it (AC-AUTH-05)."""

from __future__ import annotations

from fastapi import FastAPI

# (METHOD, path). Adding a line here is a deliberate decision to expose a route to everyone.
PUBLIC_ROUTES: frozenset[tuple[str, str]] = frozenset(
    {
        ("GET", "/health"),
        ("POST", "/auth/register"),
        ("POST", "/auth/login"),
    }
)

HTTP_METHODS = {"get", "post", "put", "patch", "delete"}


def all_operations(app: FastAPI) -> dict[tuple[str, str], dict]:
    """List every (METHOD, path) from the OpenAPI schema, which is FastAPI's stable public view."""
    operations = {}
    for path, item in app.openapi()["paths"].items():
        for method, operation in item.items():
            if method in HTTP_METHODS:
                operations[(method.upper(), path)] = operation
    return operations


def find_unprotected_routes(app: FastAPI) -> set[tuple[str, str]]:
    """Return routes with no bearer security requirement that are not in the allowlist.

    Only require_user uses the bearer scheme, so a security entry means a login is required.
    """
    return {
        key
        for key, operation in all_operations(app).items()
        if not operation.get("security") and key not in PUBLIC_ROUTES
    }
