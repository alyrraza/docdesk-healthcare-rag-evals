"""Shared fixtures. Database tests use TEST_DATABASE_URL only and never DATABASE_URL."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from dotenv import dotenv_values
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def test_database_url() -> str:
    """Give integration tests the throwaway database, and refuse anything that is not one."""
    url = os.environ.get("TEST_DATABASE_URL") or dotenv_values(ROOT / ".env").get(
        "TEST_DATABASE_URL"
    )
    if not url:
        pytest.fail("TEST_DATABASE_URL is missing from the environment and .env")
    name = make_url(url).database or ""
    if not name.endswith("_test"):
        pytest.fail(f"TEST_DATABASE_URL must point at a database ending in _test, got {name!r}")
    return url


@pytest.fixture(scope="session")
def migrated_url(test_database_url: str) -> str:
    """Build the schema from scratch with the real migrations, so tests check them too."""
    config = Config(str(ROOT / "alembic.ini"))
    config.attributes["url"] = test_database_url
    config.attributes["readonly_password"] = readonly_password()
    command.downgrade(config, "base")
    command.upgrade(config, "head")
    return test_database_url


def readonly_url() -> str | None:
    """Read READONLY_DATABASE_URL from the environment or .env, or None if it is not set."""
    return os.environ.get("READONLY_DATABASE_URL") or dotenv_values(ROOT / ".env").get(
        "READONLY_DATABASE_URL"
    )


def readonly_password() -> str | None:
    """Password the migration gives the read-only role; None leaves the role unable to log in."""
    url = readonly_url()
    return make_url(url).password if url else None


@pytest.fixture(scope="session")
def readonly_test_url(migrated_url: str) -> str:
    """Connection url for the read-only role, pointed at the test database."""
    url = readonly_url()
    if not url:
        pytest.fail("READONLY_DATABASE_URL is missing from the environment and .env")
    test_name = make_url(migrated_url).database
    return make_url(url).set(database=test_name).render_as_string(hide_password=False)
