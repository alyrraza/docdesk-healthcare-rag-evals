"""Copies prompt files into the database and keeps the pointer to the live version."""

from __future__ import annotations

import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from docdesk.core import clock
from docdesk.db.models.prompts import ActivePromptRow, PromptVersionRow
from docdesk.prompts.loader import PromptFile, load_all, parse_prompt


class ImmutablePromptError(Exception):
    """A released version was edited; the fix is a new version, never an edit (AC-PRM-01)."""


class NoActivePromptError(LookupError):
    """No version of this prompt has been activated yet."""


def find_row(session: Session, name: str, version: str) -> PromptVersionRow | None:
    """Fetch one stored version, or None."""
    query = select(PromptVersionRow).where(
        PromptVersionRow.name == name, PromptVersionRow.version == version
    )
    return session.execute(query).scalar_one_or_none()


def fill_row(row: PromptVersionRow, prompt: PromptFile) -> None:
    """Copy a parsed file onto a row."""
    row.content_hash = prompt.content_hash
    row.body = prompt.text
    row.params = prompt.params
    row.schema_version = prompt.schema
    row.status = prompt.status


def sync_prompts(session: Session, directory: Path) -> list[str]:
    """Store every file as a version row; return the versions that were added or updated."""
    changed: list[str] = []
    for prompt in load_all(directory):
        label = f"{prompt.name}@{prompt.version}"
        row = find_row(session, prompt.name, prompt.version)
        if row is None:
            row = PromptVersionRow(
                name=prompt.name, version=prompt.version, created_at=clock.utc_now()
            )
            fill_row(row, prompt)
            session.add(row)
        elif row.content_hash == prompt.content_hash:
            continue
        elif row.status == "released":
            raise ImmutablePromptError(f"{label} is released, change it by adding a new version")
        else:
            fill_row(row, prompt)
        changed.append(label)
    session.flush()
    return changed


def activate(session: Session, name: str, version: str, user_id: uuid.UUID | None) -> None:
    """Point a prompt name at a version; nothing else changes, so rollback is the same call."""
    row = find_row(session, name, version)
    if row is None:
        raise LookupError(f"prompt {name}@{version} is not in the database, sync first")
    if row.status == "retired":
        raise ValueError(f"prompt {name}@{version} is retired and cannot be activated")
    pointer = session.get(ActivePromptRow, name)
    if pointer is None:
        pointer = ActivePromptRow(name=name)
        session.add(pointer)
    pointer.prompt_version_id = row.id
    pointer.activated_by = user_id
    pointer.activated_at = clock.utc_now()
    session.flush()


def get_active(session: Session, name: str) -> PromptFile:
    """Return the live version of a prompt, rebuilt from the stored text."""
    pointer = session.get(ActivePromptRow, name)
    if pointer is None:
        raise NoActivePromptError(f"no active version for prompt '{name}'")
    row = session.get(PromptVersionRow, pointer.prompt_version_id)
    assert row is not None  # the foreign key guarantees it
    return parse_prompt(row.body)
