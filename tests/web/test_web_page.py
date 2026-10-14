"""The single page at / and its static files (no database, no model)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from docdesk.api.app import create_app
from docdesk.api.public import find_unprotected_routes
from docdesk.core.config import Settings

SETTINGS = Settings(
    database_url="postgresql://unused",
    redis_url="redis://unused",
    jwt_secret="t" * 40,
    _env_file=None,
)
ROOT = Path(__file__).resolve().parents[2]
STATIC = ROOT / "src" / "docdesk" / "web" / "static"
ALLOWED_URLS = ("localhost", "127.0.0.1", "github.com/alyrraza/docdesk-healthcare-rag-evals")
URL = re.compile(r"https?://[^\s\"'`)<>]+")


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    """An app built from test settings; the page routes touch no database."""
    monkeypatch.setattr("docdesk.api.app.get_settings", lambda: SETTINGS)
    return TestClient(create_app())


def test_ac_web_04_get_root_returns_the_html_page(client: TestClient) -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "not medical advice" in response.text.lower()


def test_ac_web_05_static_files_are_served_with_the_right_type(client: TestClient) -> None:
    css = client.get("/static/style.css")
    js = client.get("/static/main.js")
    assert css.status_code == 200 and css.headers["content-type"].startswith("text/css")
    assert js.status_code == 200 and "javascript" in js.headers["content-type"]


def test_ac_web_06_static_route_does_not_serve_other_files_or_paths(client: TestClient) -> None:
    assert client.get("/static/nope.js").status_code == 404
    assert client.get("/static/..%2Fpage.py").status_code == 404
    assert client.get("/static/%2e%2e/web/__init__.py").status_code == 404


def test_ac_web_07_page_sets_a_content_security_policy_with_no_outside_sources(
    client: TestClient,
) -> None:
    policy = client.get("/").headers["content-security-policy"]
    assert "default-src 'self'" in policy and "http" not in policy


def test_ac_web_08_the_page_routes_are_the_only_new_public_routes(client: TestClient) -> None:
    app = client.app
    assert find_unprotected_routes(app, SETTINGS) == set()  # type: ignore[arg-type]


def test_ac_web_09_static_files_make_no_outside_request() -> None:
    offenders = []
    for path in sorted(STATIC.iterdir()):
        for url in URL.findall(path.read_text(encoding="utf-8")):
            if not any(ok in url for ok in ALLOWED_URLS):
                offenders.append(f"{path.name}: {url}")
    assert offenders == []


def test_ac_web_10_no_inner_html_or_other_html_sinks_in_the_scripts() -> None:
    sinks = re.compile(
        r"innerHTML|outerHTML|insertAdjacentHTML|document\.write|eval\(|new Function"
    )
    hits = [p.name for p in STATIC.glob("*.js") if sinks.search(p.read_text(encoding="utf-8"))]
    assert hits == []


def test_ac_web_11_static_files_have_no_dashes_and_stay_short() -> None:
    for path in STATIC.iterdir():
        text = path.read_text(encoding="utf-8")
        assert "\u2014" not in text and "\u2013" not in text, path.name
        assert len(text.splitlines()) < 200, path.name


def test_ac_web_12_the_docker_image_copies_src_so_it_holds_the_static_files() -> None:
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert "COPY src ./src" in dockerfile
    assert "src" not in (ROOT / ".dockerignore").read_text(encoding="utf-8").split()
    assert (STATIC / "index.html").exists()
