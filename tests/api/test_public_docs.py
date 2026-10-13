"""The interactive docs are public only where the setting allows it (AC-AUTH-05)."""

from __future__ import annotations

import pytest
from fastapi import APIRouter, Depends, FastAPI
from fastapi.testclient import TestClient

from docdesk.api.app import create_app
from docdesk.api.public import DOCS_ROUTES, all_operations, find_unprotected_routes, public_routes
from docdesk.auth.deps import require_user
from docdesk.core.config import Settings


def make_settings(environment: str) -> Settings:
    """Settings for one environment, ignoring .env so the test owns every value."""
    return Settings(
        database_url="postgresql://unused",
        redis_url="redis://unused",
        jwt_secret="t" * 40,
        environment=environment,
        _env_file=None,
    )


@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json"])
def test_ac_auth_05_docs_are_served_without_login_locally(path: str) -> None:
    client = TestClient(create_app(make_settings("local")))
    assert client.get(path).status_code == 200


@pytest.mark.parametrize("path", ["/docs", "/redoc", "/openapi.json"])
def test_ac_auth_05_docs_are_gone_in_production(path: str) -> None:
    client = TestClient(create_app(make_settings("production")))
    assert client.get(path).status_code == 404


def test_ac_auth_05_docs_routes_are_explicit_allowlist_entries_locally() -> None:
    settings = make_settings("local")
    app = create_app(settings)
    assert DOCS_ROUTES <= set(all_operations(app))
    assert DOCS_ROUTES <= public_routes(settings)
    assert find_unprotected_routes(app, settings) == set()


def test_ac_auth_05_docs_are_not_allowlisted_in_production() -> None:
    settings = make_settings("production")
    app = create_app(settings)
    assert DOCS_ROUTES.isdisjoint(public_routes(settings))
    assert DOCS_ROUTES.isdisjoint(set(all_operations(app)))
    assert find_unprotected_routes(app, settings) == set()


def test_ac_auth_05_docs_left_on_in_production_are_flagged() -> None:
    """If someone builds the app with docs on but runs the check as production, it must fail."""
    app = create_app(make_settings("local"))
    assert DOCS_ROUTES <= find_unprotected_routes(app, make_settings("production"))


def test_ac_auth_05_a_route_hidden_from_the_schema_is_still_checked() -> None:
    settings = make_settings("local")
    app = create_app(settings)

    @app.get("/hidden", include_in_schema=False)
    def hidden() -> dict[str, str]:
        return {}

    assert ("GET", "/hidden") in find_unprotected_routes(app, settings)


def test_ac_auth_05_a_route_inside_a_mounted_app_is_checked() -> None:
    settings = make_settings("local")
    app = create_app(settings)
    sub_app = FastAPI()

    @sub_app.get("/inner")
    def inner() -> dict[str, str]:
        return {}

    app.mount("/sub", sub_app)

    assert ("GET", "/sub/inner") in find_unprotected_routes(app, settings)


def test_ac_auth_05_a_nested_router_with_a_login_dependency_is_not_flagged() -> None:
    settings = make_settings("local")
    app = create_app(settings)
    router = APIRouter()

    @router.get("/item")
    def item() -> dict[str, str]:
        return {}

    app.include_router(router, prefix="/guarded", dependencies=[Depends(require_user)])
    app.include_router(router, prefix="/open")

    unprotected = find_unprotected_routes(app, settings)
    assert ("GET", "/guarded/item") not in unprotected
    assert ("GET", "/open/item") in unprotected
