"""Tests that Alembic runs against the real test database, up and back down."""

from __future__ import annotations

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text

from docdesk.db.session import make_engine

pytestmark = pytest.mark.integration


@pytest.fixture(autouse=True)
def restore_schema_afterwards(test_database_url: str):
    """These tests walk the schema down to base, so rebuild it for tests that run later."""
    yield
    command.upgrade(alembic_config(test_database_url), "head")


ROOT = Path(__file__).resolve().parents[2]


def alembic_config(url: str) -> Config:
    """Point Alembic at the test database without touching DATABASE_URL."""
    config = Config(str(ROOT / "alembic.ini"))
    config.attributes["url"] = url
    return config


def current_versions(url: str) -> list[str]:
    with make_engine(url).connect() as connection:
        rows = connection.execute(text("SELECT version_num FROM alembic_version"))
        return [row[0] for row in rows]


def test_first_migration_upgrades_and_downgrades(test_database_url: str) -> None:
    config = alembic_config(test_database_url)
    command.downgrade(config, "base")
    command.upgrade(config, "0001")
    assert current_versions(test_database_url) == ["0001"]
    command.downgrade(config, "base")
    assert current_versions(test_database_url) == []


def extension_version(url: str) -> str | None:
    with make_engine(url).connect() as connection:
        query = text("SELECT extversion FROM pg_extension WHERE extname = 'vector'")
        return connection.execute(query).scalar_one_or_none()


def test_second_migration_enables_and_removes_pgvector(test_database_url: str) -> None:
    config = alembic_config(test_database_url)
    command.downgrade(config, "base")
    command.upgrade(config, "0002")
    assert extension_version(test_database_url) is not None
    command.downgrade(config, "0001")
    assert extension_version(test_database_url) is None
    command.downgrade(config, "base")


def test_ac_ing_05_migration_0012_adds_and_removes_the_chunks_page_column(
    test_database_url: str,
) -> None:
    config = alembic_config(test_database_url)
    sql = (
        "SELECT is_nullable, data_type FROM information_schema.columns "
        "WHERE table_name = 'chunks' AND column_name = 'page'"
    )
    command.downgrade(config, "0011")
    with make_engine(test_database_url).connect() as connection:
        assert connection.execute(text(sql)).fetchall() == []
    command.upgrade(config, "0012")
    with make_engine(test_database_url).connect() as connection:
        assert connection.execute(text(sql)).fetchall() == [("YES", "integer")]
