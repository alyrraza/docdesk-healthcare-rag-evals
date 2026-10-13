"""Syncing prompt files into the database and moving the active pointer (AC-PRM-01)."""

from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from docdesk.db.models.prompts import PromptVersionRow
from docdesk.prompts.registry import (
    ImmutablePromptError,
    NoActivePromptError,
    activate,
    get_active,
    sync_prompts,
)

pytestmark = pytest.mark.integration

FILE = """---
name: {name}
version: {version}
schema: AnswerOutput@1
params:
  temperature: 0
untrusted: []
status: {status}
changelog: test
---
## system
{body}

## user
{{{{question}}}}
"""


def write(folder: Path, name: str, version: str, status: str, body: str = "rules") -> None:
    target = folder / name
    target.mkdir(parents=True, exist_ok=True)
    text = FILE.format(name=name, version=version, status=status, body=body)
    (target / f"{name}.v{version[0]}.md").write_text(text, encoding="utf-8")


def unique(prefix: str = "p") -> str:
    return f"{prefix}{uuid.uuid4().hex[:8]}"


def test_ac_prm_01_a_new_file_is_stored_as_a_version_row(
    db_session: Session, tmp_path: Path
) -> None:
    name = unique()
    write(tmp_path, name, "1.0.0", "released")
    assert sync_prompts(db_session, tmp_path) == [f"{name}@1.0.0"]
    row = db_session.execute(
        select(PromptVersionRow).where(PromptVersionRow.name == name)
    ).scalar_one()
    assert (row.version, row.status, row.schema_version) == ("1.0.0", "released", "AnswerOutput@1")
    assert len(row.content_hash) == 64


def test_ac_prm_01_syncing_the_same_files_again_changes_nothing(
    db_session: Session, tmp_path: Path
) -> None:
    write(tmp_path, unique(), "1.0.0", "released")
    sync_prompts(db_session, tmp_path)
    assert sync_prompts(db_session, tmp_path) == []


def test_ac_prm_01_editing_a_released_version_is_refused(
    db_session: Session, tmp_path: Path
) -> None:
    name = unique()
    write(tmp_path, name, "1.0.0", "released", body="original")
    sync_prompts(db_session, tmp_path)
    write(tmp_path, name, "1.0.0", "released", body="a typo fix")
    with pytest.raises(ImmutablePromptError, match=name):
        sync_prompts(db_session, tmp_path)


def test_ac_prm_01_a_draft_may_still_change(db_session: Session, tmp_path: Path) -> None:
    name = unique()
    write(tmp_path, name, "1.0.0", "draft", body="first")
    sync_prompts(db_session, tmp_path)
    write(tmp_path, name, "1.0.0", "draft", body="second")
    assert sync_prompts(db_session, tmp_path) == [f"{name}@1.0.0"]
    assert "second" in get_stored_body(db_session, name)


def get_stored_body(session: Session, name: str) -> str:
    return session.execute(
        select(PromptVersionRow.body).where(PromptVersionRow.name == name)
    ).scalar_one()


def test_ac_prm_01_a_new_version_is_a_new_row_next_to_the_old_one(
    db_session: Session, tmp_path: Path
) -> None:
    name = unique()
    write(tmp_path, name, "1.0.0", "released")
    sync_prompts(db_session, tmp_path)
    write(tmp_path, name, "2.0.0", "released")
    sync_prompts(db_session, tmp_path)
    count = (
        db_session.execute(select(PromptVersionRow).where(PromptVersionRow.name == name))
        .scalars()
        .all()
    )
    assert sorted(r.version for r in count) == ["1.0.0", "2.0.0"]


def test_ac_prm_02_activating_moves_only_the_pointer(db_session: Session, tmp_path: Path) -> None:
    name = unique()
    write(tmp_path, name, "1.0.0", "released")
    sync_prompts(db_session, tmp_path)
    with pytest.raises(NoActivePromptError):
        get_active(db_session, name)
    activate(db_session, name, "1.0.0", None)
    assert get_active(db_session, name).version == "1.0.0"
    assert db_session.execute(select(PromptVersionRow)).scalars().all()


def test_ac_prm_02_activating_an_unknown_version_is_an_error(db_session: Session) -> None:
    with pytest.raises(LookupError):
        activate(db_session, "nothing", "9.9.9", None)
