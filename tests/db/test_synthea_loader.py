"""Tests for the Synthea tables and the loader that fills them."""

from __future__ import annotations

import csv
from pathlib import Path

import psycopg
import pytest
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from docdesk.db.session import make_engine
from docdesk.db.synthea import load_synthea

pytestmark = pytest.mark.integration

PATIENT = "11111111-1111-1111-1111-111111111111"
OTHER = "22222222-2222-2222-2222-222222222222"
ENCOUNTER = "33333333-3333-3333-3333-333333333333"


def write_csv(path: Path, header: list[str], rows: list[list[str]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(header)
        writer.writerows(rows)


@pytest.fixture
def csv_dir(tmp_path: Path) -> Path:
    write_csv(
        tmp_path / "patients.csv",
        [
            "Id",
            "BIRTHDATE",
            "DEATHDATE",
            "SSN",
            "FIRST",
            "LAST",
            "RACE",
            "ETHNICITY",
            "GENDER",
            "CITY",
            "STATE",
        ],
        [
            [
                PATIENT,
                "1978-01-16",
                "",
                "999-55-9547",
                "Guillermo",
                "Von",
                "white",
                "nonhispanic",
                "M",
                "Salem",
                "Massachusetts",
            ],
            [
                OTHER,
                "2001-02-11",
                "2020-05-01",
                "999-32-1995",
                "Jayne",
                "Bruen",
                "asian",
                "nonhispanic",
                "F",
                "Bedford",
                "Massachusetts",
            ],
        ],
    )
    write_csv(
        tmp_path / "encounters.csv",
        [
            "Id",
            "START",
            "STOP",
            "PATIENT",
            "ENCOUNTERCLASS",
            "CODE",
            "DESCRIPTION",
            "TOTAL_CLAIM_COST",
            "REASONDESCRIPTION",
        ],
        [
            [
                ENCOUNTER,
                "1996-03-11T08:35:36Z",
                "1996-03-11T09:21:33Z",
                PATIENT,
                "wellness",
                "162673000",
                "General examination of patient (procedure)",
                "704.20",
                "",
            ]
        ],
    )
    write_csv(
        tmp_path / "conditions.csv",
        ["START", "STOP", "PATIENT", "ENCOUNTER", "CODE", "DESCRIPTION"],
        [["1996-03-11", "", PATIENT, ENCOUNTER, "224299000", "Higher education"]],
    )
    write_csv(
        tmp_path / "medications.csv",
        ["START", "STOP", "PATIENT", "ENCOUNTER", "CODE", "DESCRIPTION", "DISPENSES", "TOTALCOST"],
        [
            [
                "2018-02-05T12:22:02Z",
                "",
                PATIENT,
                ENCOUNTER,
                "1535362",
                "sodium fluoride gel",
                "1",
                "129.94",
            ]
        ],
    )
    return tmp_path


def count(session: Session, table: str) -> int:
    return session.execute(text(f"SELECT count(*) FROM {table}")).scalar_one()


def test_loader_fills_all_four_tables(db_session: Session, csv_dir: Path) -> None:
    counts = load_synthea(db_session, csv_dir)
    assert counts == {"patients": 2, "conditions": 1, "medications": 1, "encounters": 1}
    assert count(db_session, "synthea_patients") == 2
    assert count(db_session, "synthea_encounters") == 1


def test_loader_parses_dates_numbers_and_blanks(db_session: Session, csv_dir: Path) -> None:
    load_synthea(db_session, csv_dir)
    row = db_session.execute(
        text("SELECT birthdate, deathdate, gender FROM synthea_patients WHERE id = :id"),
        {"id": PATIENT},
    ).one()
    assert (str(row.birthdate), row.deathdate, row.gender) == ("1978-01-16", None, "M")
    cost = db_session.execute(text("SELECT total_claim_cost FROM synthea_encounters")).scalar_one()
    assert float(cost) == 704.20


def test_loader_never_stores_identifying_columns(db_session: Session, csv_dir: Path) -> None:
    load_synthea(db_session, csv_dir)
    columns = set(
        db_session.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'synthea_patients'"
            )
        ).scalars()
    )
    assert not columns & {"ssn", "first", "last", "address", "drivers", "passport"}


def test_loading_twice_replaces_rows_instead_of_duplicating(
    db_session: Session, csv_dir: Path
) -> None:
    load_synthea(db_session, csv_dir)
    load_synthea(db_session, csv_dir)
    assert count(db_session, "synthea_patients") == 2
    assert count(db_session, "synthea_conditions") == 1


def test_missing_csv_file_fails_loudly_and_loads_nothing(
    db_session: Session, csv_dir: Path
) -> None:
    (csv_dir / "medications.csv").unlink()
    with pytest.raises(FileNotFoundError):
        load_synthea(db_session, csv_dir)
    assert count(db_session, "synthea_patients") == 0


def test_ac_sql_03_readonly_role_can_select_synthea_tables(
    migrated_url: str, readonly_test_url: str, csv_dir: Path
) -> None:
    engine = make_engine(migrated_url)
    try:
        with Session(engine) as writer:
            load_synthea(writer, csv_dir)
            writer.commit()
        dsn = make_url(readonly_test_url).set(drivername="postgresql")
        with psycopg.connect(dsn.render_as_string(hide_password=False), autocommit=True) as conn:
            assert conn.execute("SELECT count(*) FROM synthea_patients").fetchone()[0] == 2
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                conn.execute("SELECT 1 FROM users")
            denied = (psycopg.errors.InsufficientPrivilege, psycopg.errors.ReadOnlySqlTransaction)
            with pytest.raises(denied):
                conn.execute("DELETE FROM synthea_patients")
    finally:
        with engine.begin() as connection:
            connection.execute(text("DELETE FROM synthea_patients"))
        engine.dispose()


def test_loader_handles_more_rows_than_one_batch(
    db_session: Session, csv_dir: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from docdesk.db import synthea

    monkeypatch.setattr(synthea, "BATCH_SIZE", 2)
    rows = [
        [f"2000-01-{day:02d}", "", PATIENT, ENCOUNTER, str(day), f"condition {day}"]
        for day in range(1, 8)
    ]
    write_csv(
        csv_dir / "conditions.csv",
        ["START", "STOP", "PATIENT", "ENCOUNTER", "CODE", "DESCRIPTION"],
        rows,
    )
    assert load_synthea(db_session, csv_dir)["conditions"] == 7
    assert count(db_session, "synthea_conditions") == 7
