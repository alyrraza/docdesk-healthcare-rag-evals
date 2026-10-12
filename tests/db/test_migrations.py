"""Tests that Alembic runs against the real test database, up and back down."""

from __future__ import annotations

from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text

from docdesk.db.session import make_engine

pytestmark = pytest.mark.integration

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
    command.upgrade(config, "head")
    assert current_versions(test_database_url) == ["0001"]
    command.downgrade(config, "base")
    assert current_versions(test_database_url) == []
