"""The read-only role used by the SQL branch reads only what it is granted and writes nothing."""

from __future__ import annotations

import psycopg
import pytest
from sqlalchemy.engine import make_url

pytestmark = pytest.mark.integration


def connect(url: str) -> psycopg.Connection:
    dsn = make_url(url).set(drivername="postgresql").render_as_string(hide_password=False)
    return psycopg.connect(dsn, autocommit=True)


def test_readonly_role_can_log_in_and_run_a_select(readonly_test_url: str) -> None:
    with connect(readonly_test_url) as conn:
        assert conn.execute("SELECT 1").fetchone()[0] == 1


def test_readonly_role_cannot_read_application_tables(readonly_test_url: str) -> None:
    with connect(readonly_test_url) as conn, pytest.raises(psycopg.errors.InsufficientPrivilege):
        conn.execute("SELECT * FROM users")


def test_readonly_role_cannot_create_tables_even_if_it_lifts_read_only_mode(
    readonly_test_url: str,
) -> None:
    """Privileges must stop writes on their own, not only the read-only default."""
    with connect(readonly_test_url) as conn:
        conn.execute("SET default_transaction_read_only = off")
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("CREATE TABLE should_fail (id int)")


def test_readonly_role_cannot_write_even_to_a_temp_table(readonly_test_url: str) -> None:
    with connect(readonly_test_url) as conn:
        assert conn.execute("SHOW default_transaction_read_only").fetchone()[0] == "on"
        with pytest.raises(psycopg.errors.ReadOnlySqlTransaction):
            conn.execute("CREATE TEMP TABLE t (id int)")


def test_readonly_role_holds_no_table_privileges_on_public_tables(readonly_test_url: str) -> None:
    sql = (
        "SELECT count(*) FROM information_schema.table_privileges "
        "WHERE grantee = 'docdesk_readonly' AND table_schema = 'public'"
    )
    with connect(readonly_test_url) as conn:
        assert conn.execute(sql).fetchone()[0] == 0
