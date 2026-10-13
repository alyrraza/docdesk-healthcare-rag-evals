"""Helpers shared by the POST /query API tests."""

from __future__ import annotations

import json

from fastapi.testclient import TestClient
from sqlalchemy import select

from docdesk.db.models.traces import QueryTraceRow
from docdesk.db.session import make_engine, make_session_factory

PASSWORD = "a-long-enough-password"
REPLY = json.dumps(
    {
        "evidence_used": ["c1"],
        "answer": "Aspirin may cause stomach bleeding.",
        "citations": ["c1"],
        "confidence": "high",
        "abstained": False,
        "abstain_reason": "none",
    }
)


def register_user(client: TestClient, email: str) -> dict[str, str]:
    """Create a user and log in; return the auth header and the user id."""
    creds = {"email": email, "password": PASSWORD}
    user_id = client.post("/auth/register", json=creds).json()["data"]["id"]
    token = client.post("/auth/login", json=creds).json()["data"]["access_token"]
    return {"authorization": f"Bearer {token}", "user_id": user_id}


def trace_for(migrated_url: str, trace_id: str) -> QueryTraceRow:
    """Read back the one trace row a request left."""
    engine = make_engine(migrated_url)
    with make_session_factory(engine)() as session:
        row = session.execute(
            select(QueryTraceRow).where(QueryTraceRow.trace_id == trace_id)
        ).scalar_one()
    engine.dispose()
    return row


def ask(client: TestClient, me: dict[str, str], question: str = "What are aspirin risks?"):
    """Send one question as the given user."""
    return client.post(
        "/query", json={"question": question}, headers={"authorization": me["authorization"]}
    )
