"""Guard that keeps integration tests on a throwaway database. Tests never read DATABASE_URL."""

from __future__ import annotations

from sqlalchemy.engine import make_url


def test_integration_tests_run_on_a_database_named_for_testing(test_database_url: str) -> None:
    assert (make_url(test_database_url).database or "").endswith("_test")
