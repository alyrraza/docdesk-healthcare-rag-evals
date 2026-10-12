"""The route walk: every route needs auth unless it is in the public allowlist (AC-AUTH-05)."""

from __future__ import annotations

from docdesk.api.public import PUBLIC_ROUTES, find_unprotected_routes
from fastapi import Depends, FastAPI

from docdesk.api.app import create_app
from docdesk.auth.deps import require_user


def test_ac_auth_05_every_public_route_is_in_the_allowlist() -> None:
    assert find_unprotected_routes(create_app()) == set()


def test_ac_auth_05_an_unprotected_route_outside_the_allowlist_is_found() -> None:
    app = create_app()

    @app.get("/secret-data")
    def secret_data() -> dict[str, str]:
        return {"oops": "no auth"}

    assert ("GET", "/secret-data") in find_unprotected_routes(app)


def test_ac_auth_05_a_route_with_require_user_is_not_flagged() -> None:
    app = create_app()

    @app.get("/private", dependencies=[Depends(require_user)])
    def private() -> dict[str, str]:
        return {}

    assert ("GET", "/private") not in find_unprotected_routes(app)


def test_ac_auth_05_allowlist_has_no_stale_entries() -> None:
    app = create_app()
    existing = {
        (method, route.path)
        for route in app.routes
        for method in (getattr(route, "methods", None) or [])
    }
    assert {entry for entry in PUBLIC_ROUTES if entry[0] != "ANY"} <= existing


def test_a_bare_fastapi_app_has_only_its_docs_routes_unprotected() -> None:
    assert all(path in {"/docs", "/redoc", "/openapi.json", "/docs/oauth2-redirect"}
               for _, path in find_unprotected_routes(FastAPI()))
