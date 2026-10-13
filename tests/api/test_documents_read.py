"""Tests for GET /documents and GET /documents/{id}: own and shared documents only."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient

from docdesk.db.models.documents import DocumentStatus
from docdesk.db.repositories.documents import DocumentRepository
from docdesk.db.repositories.users import UserRepository
from docdesk.db.session import make_engine, make_session_factory

pytestmark = pytest.mark.integration

CREDS = {"email": "reader@example.com", "password": "a-long-enough-password"}


@pytest.fixture
def me(client: TestClient) -> dict[str, str]:
    """Sign in and return the auth header plus the user id."""
    user_id = client.post("/auth/register", json=CREDS).json()["data"]["id"]
    token = client.post("/auth/login", json=CREDS).json()["data"]["access_token"]
    return {"authorization": f"Bearer {token}", "user_id": user_id}


@pytest.fixture
def make_doc(migrated_url: str):
    """Insert documents straight into the database for a given owner."""
    engine = make_engine(migrated_url)

    def make(owner_id: str, title: str, *, shared: bool = False, status=DocumentStatus.READY):
        with make_session_factory(engine)() as session:
            repo = DocumentRepository(session)
            doc = repo.add(uuid.UUID(owner_id), title, "test", f"hash-{title}", is_shared=shared)
            repo.set_status(doc.id, status, chunk_count=3)
            session.commit()
            return doc

    yield make
    engine.dispose()


@pytest.fixture
def stranger(migrated_url: str) -> str:
    """A second user whose private documents I must never see."""
    engine = make_engine(migrated_url)
    with make_session_factory(engine)() as session:
        user = UserRepository(session).add("stranger@example.com", "hash", "user")
        session.commit()
    engine.dispose()
    return str(user.id)


def headers(me: dict[str, str]) -> dict[str, str]:
    return {"authorization": me["authorization"]}


def test_ac_ing_02_list_shows_my_documents_with_status_and_chunk_count(
    client: TestClient, me, make_doc
) -> None:
    make_doc(me["user_id"], "mine")
    items = client.get("/documents", headers=headers(me)).json()["data"]
    assert [(i["title"], i["status"], i["chunk_count"]) for i in items] == [("mine", "ready", 3)]


def test_ac_ret_05_list_includes_shared_documents_but_not_other_peoples_private_ones(
    client: TestClient, me, make_doc, stranger
) -> None:
    make_doc(me["user_id"], "mine")
    make_doc(stranger, "shared corpus", shared=True)
    make_doc(stranger, "their private file")
    titles = {i["title"] for i in client.get("/documents", headers=headers(me)).json()["data"]}
    assert titles == {"mine", "shared corpus"}


def test_ac_ing_02_get_one_returns_its_status_and_failure_reason(
    client: TestClient, me, make_doc
) -> None:
    doc = make_doc(me["user_id"], "broken", status=DocumentStatus.FAILED)
    response = client.get(f"/documents/{doc.id}", headers=headers(me))
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "failed"
    assert "content_hash" not in response.json()["data"]


def test_ac_ret_05_someone_elses_private_document_looks_like_it_does_not_exist(
    client: TestClient, me, make_doc, stranger
) -> None:
    doc = make_doc(stranger, "their private file")
    response = client.get(f"/documents/{doc.id}", headers=headers(me))
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "not_found"


def test_ac_ret_05_a_shared_document_can_be_read_by_anyone_signed_in(
    client: TestClient, me, make_doc, stranger
) -> None:
    doc = make_doc(stranger, "shared corpus", shared=True)
    assert client.get(f"/documents/{doc.id}", headers=headers(me)).status_code == 200


def test_ac_ing_02_an_unknown_id_is_404_and_a_malformed_id_is_422(client: TestClient, me) -> None:
    assert client.get(f"/documents/{uuid.uuid4()}", headers=headers(me)).status_code == 404
    assert client.get("/documents/not-a-uuid", headers=headers(me)).status_code == 422


def test_ac_auth_03_both_routes_need_a_token(client: TestClient) -> None:
    assert client.get("/documents").status_code == 401
    assert client.get(f"/documents/{uuid.uuid4()}").status_code == 401
