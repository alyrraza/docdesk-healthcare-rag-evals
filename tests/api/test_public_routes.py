"""The route walk: every route needs auth unless it is in the public allowlist (AC-AUTH-05)."""

from __future__ import annotations

from fastapi import Depends

from docdesk.api.app import create_app
from docdesk.api.public import all_operations, find_unprotected_routes, public_routes
from docdesk.auth.deps import require_user
from docdesk.core.config import Settings

SETTINGS = Settings(
    database_url="postgresql://unused",
    redis_url="redis://unused",
    jwt_secret="t" * 40,
    _env_file=None,
)


def test_ac_auth_05_every_public_route_is_in_the_allowlist() -> None:
    assert find_unprotected_routes(create_app(SETTINGS), SETTINGS) == set()


def test_ac_auth_05_an_unprotected_route_outside_the_allowlist_is_found() -> None:
    app = create_app(SETTINGS)

    @app.get("/secret-data")
    def secret_data() -> dict[str, str]:
        return {"oops": "no auth"}

    assert ("GET", "/secret-data") in find_unprotected_routes(app, SETTINGS)


def test_ac_auth_05_a_route_with_require_user_is_not_flagged() -> None:
    app = create_app(SETTINGS)

    @app.get("/private", dependencies=[Depends(require_user)])
    def private() -> dict[str, str]:
        return {}

    assert ("GET", "/private") not in find_unprotected_routes(app, SETTINGS)


def test_ac_auth_05_allowlist_has_no_stale_entries() -> None:
    assert public_routes(SETTINGS) <= set(all_operations(create_app(SETTINGS)))


def test_ac_auth_05_the_walk_sees_the_real_routes() -> None:
    seen = set(all_operations(create_app(SETTINGS)))
    assert {("GET", "/health"), ("POST", "/auth/login")} <= seen
