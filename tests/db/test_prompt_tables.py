"""Tests for the prompt_versions and active_prompts tables."""

from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from sqlalchemy.orm.exc import FlushError

from docdesk.core import clock
from docdesk.db.models.prompts import ActivePromptRow, PromptVersionRow

pytestmark = pytest.mark.integration


def make_version(name: str = "answer", version: str = "1.0.0", status: str = "draft"):
    return PromptVersionRow(
        name=name,
        version=version,
        content_hash="abc123",
        body="## system\nhello",
        params={"temperature": 0, "max_output_tokens": 600},
        schema_version="AnswerOutput@1",
        status=status,
        created_at=clock.utc_now(),
    )


def test_prompt_version_round_trips_with_json_params(db_session: Session) -> None:
    db_session.add(make_version())
    db_session.flush()
    stored = db_session.execute(select(PromptVersionRow)).scalar_one()
    assert stored.params == {"temperature": 0, "max_output_tokens": 600}
    assert stored.schema_version == "AnswerOutput@1"


def test_same_name_and_version_cannot_be_registered_twice(db_session: Session) -> None:
    db_session.add(make_version())
    db_session.flush()
    db_session.add(make_version())
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_same_version_under_another_name_is_allowed(db_session: Session) -> None:
    db_session.add(make_version(name="answer"))
    db_session.add(make_version(name="router"))
    db_session.flush()


def test_unknown_status_is_rejected(db_session: Session) -> None:
    db_session.add(make_version(status="published"))
    with pytest.raises(IntegrityError):
        db_session.flush()


def test_ac_prm_02_activating_only_moves_the_pointer(db_session: Session) -> None:
    v1, v2 = make_version(version="1.0.0"), make_version(version="2.0.0")
    db_session.add_all([v1, v2])
    db_session.flush()
    db_session.add(
        ActivePromptRow(name="answer", prompt_version_id=v1.id, activated_at=clock.utc_now())
    )
    db_session.flush()
    pointer = db_session.get(ActivePromptRow, "answer")
    pointer.prompt_version_id = v2.id
    db_session.flush()
    assert db_session.get(ActivePromptRow, "answer").prompt_version_id == v2.id
    assert len(db_session.execute(select(PromptVersionRow)).scalars().all()) == 2


def test_only_one_active_pointer_per_prompt_name(db_session: Session) -> None:
    version = make_version()
    db_session.add(version)
    db_session.flush()
    db_session.add(
        ActivePromptRow(name="answer", prompt_version_id=version.id, activated_at=clock.utc_now())
    )
    db_session.flush()
    db_session.add(
        ActivePromptRow(name="answer", prompt_version_id=version.id, activated_at=clock.utc_now())
    )
    with pytest.raises((IntegrityError, FlushError)):
        db_session.flush()
