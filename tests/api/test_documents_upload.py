"""Tests for POST /documents: accepted now, embedded later by the worker (AC-ING-01)."""

from __future__ import annotations

import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from docdesk.api.deps import get_enqueue, get_file_store
from docdesk.core.config import Settings, get_settings
from docdesk.db.session import make_engine, make_session_factory
from fakes.ingestion import FakeStore

pytestmark = pytest.mark.integration

BODY = b"Aspirin may cause stomach bleeding. Take it with food."


class Queue:
    """Records the document ids that would be sent to the worker."""

    def __init__(self) -> None:
        self.ids: list[uuid.UUID] = []
        self.fail = False

    def __call__(self, document_id: uuid.UUID) -> None:
        if self.fail:
            raise ConnectionError("broker is down")
        self.ids.append(document_id)


@pytest.fixture
def store(client: TestClient) -> FakeStore:
    fake = FakeStore()
    client.app.dependency_overrides[get_file_store] = lambda: fake
    return fake


@pytest.fixture
def queue(client: TestClient) -> Queue:
    recorder = Queue()
    client.app.dependency_overrides[get_enqueue] = lambda: recorder
    return recorder


def sign_in(client: TestClient, email: str = "uploader@example.com") -> dict[str, str]:
    creds = {"email": email, "password": "a-long-enough-password"}
    client.post("/auth/register", json=creds)
    token = client.post("/auth/login", json=creds).json()["data"]["access_token"]
    return {"authorization": f"Bearer {token}"}


def upload(client: TestClient, headers: dict[str, str], body: bytes = BODY, title: str = "Label"):
    return client.post("/documents", params={"title": title}, content=body, headers=headers)


def test_ac_ing_01_upload_returns_202_with_an_id_and_queued_status(
    client: TestClient, store: FakeStore, queue: Queue
) -> None:
    response = upload(client, sign_in(client))
    assert response.status_code == 202
    data = response.json()["data"]
    assert data["status"] == "queued"
    assert data["title"] == "Label"
    assert data["duplicate"] is False
    assert queue.ids == [uuid.UUID(data["id"])]
    assert store.files[uuid.UUID(data["id"])] == BODY


def test_ac_ing_01_upload_without_a_token_is_401(client: TestClient, queue: Queue) -> None:
    response = client.post("/documents", params={"title": "x"}, content=BODY)
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"
    assert queue.ids == []


def test_ac_ing_01_an_empty_upload_is_rejected(client: TestClient, queue: Queue) -> None:
    response = upload(client, sign_in(client), body=b"")
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "empty_file"
    assert queue.ids == []


def test_ac_ing_01_a_missing_title_is_rejected(client: TestClient, queue: Queue) -> None:
    response = client.post("/documents", content=BODY, headers=sign_in(client))
    assert response.status_code == 422
    assert "title" in response.json()["error"]["message"]


def test_ac_ing_01_a_file_over_the_size_limit_is_413(
    client: TestClient, store: FakeStore, queue: Queue, api_settings: Settings
) -> None:
    headers = sign_in(client)
    small = api_settings.model_copy(update={"max_upload_bytes": 10})
    client.app.dependency_overrides[get_settings] = lambda: small
    response = upload(client, headers)
    assert response.status_code == 413
    assert response.json()["error"]["code"] == "file_too_large"
    assert queue.ids == [] and store.files == {}


def test_ac_ing_04_the_same_content_twice_returns_the_first_document(
    client: TestClient, store: FakeStore, queue: Queue
) -> None:
    headers = sign_in(client)
    first = upload(client, headers).json()["data"]
    second = upload(client, headers, title="Same file again")
    assert second.status_code == 200
    assert second.json()["data"]["id"] == first["id"]
    assert second.json()["data"]["duplicate"] is True
    assert queue.ids == [uuid.UUID(first["id"])]


def test_ac_ing_04_another_user_uploading_the_same_content_gets_their_own_document(
    client: TestClient, store: FakeStore, queue: Queue
) -> None:
    first = upload(client, sign_in(client, "one@example.com")).json()["data"]
    second = upload(client, sign_in(client, "two@example.com")).json()["data"]
    assert first["id"] != second["id"]
    assert len(queue.ids) == 2


def test_ac_ing_03_if_the_queue_is_down_the_document_is_failed_and_the_user_told(
    client: TestClient, store: FakeStore, queue: Queue, migrated_url: str
) -> None:
    queue.fail = True
    response = upload(client, sign_in(client))
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "queue_unavailable"
    engine = make_engine(migrated_url)
    with make_session_factory(engine)() as session:
        row = session.execute(text("SELECT status, fail_reason FROM documents")).one()
    engine.dispose()
    assert row.status == "failed"
    assert "queue" in row.fail_reason


def test_ac_ing_01_the_uploaded_route_needs_login_in_the_openapi_schema(
    client: TestClient,
) -> None:
    operation = client.app.openapi()["paths"]["/documents"]["post"]
    assert operation["security"]


def test_ac_ing_03_uploading_again_after_a_failure_queues_the_same_document_again(
    client: TestClient, store: FakeStore, queue: Queue
) -> None:
    headers = sign_in(client)
    queue.fail = True
    assert upload(client, headers).status_code == 503
    queue.fail = False
    response = upload(client, headers)
    assert response.status_code == 202
    data = response.json()["data"]
    assert data["status"] == "queued" and data["duplicate"] is False
    assert queue.ids == [uuid.UUID(data["id"])]
