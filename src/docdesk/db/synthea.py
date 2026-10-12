"""Load the Synthea CSV files into the synthea_* tables."""

from __future__ import annotations

import csv
from collections.abc import Callable, Iterator
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

from sqlalchemy import delete, insert
from sqlalchemy.orm import Session

from docdesk.db.models.synthea import (
    SyntheaConditionRow,
    SyntheaEncounterRow,
    SyntheaMedicationRow,
    SyntheaPatientRow,
)

Row = dict[str, str]

# One INSERT per batch keeps the number of network round trips small on a hosted database.
BATCH_SIZE = 500


def text_or_none(value: str) -> str | None:
    """Treat an empty CSV cell as missing."""
    return value or None


def date_or_none(value: str) -> date | None:
    """Parse a YYYY-MM-DD cell, or None when blank."""
    return date.fromisoformat(value) if value else None


def timestamp_or_none(value: str) -> datetime | None:
    """Parse an ISO timestamp such as 2018-02-05T12:22:02Z, or None when blank."""
    return datetime.fromisoformat(value) if value else None


def number_or_none(value: str) -> Decimal | None:
    """Parse a money cell, or None when blank."""
    return Decimal(value) if value else None


def int_or_none(value: str) -> int | None:
    """Parse an integer cell, or None when blank."""
    return int(value) if value else None


def read_rows(path: Path) -> Iterator[Row]:
    """Stream a CSV file as dictionaries keyed by its header."""
    with path.open(newline="", encoding="utf-8") as handle:
        yield from csv.DictReader(handle)


def patient(row: Row) -> dict[str, Any]:
    """Keep only the demographic columns we allow the SQL branch to see."""
    return {
        "id": row["Id"],
        "birthdate": date.fromisoformat(row["BIRTHDATE"]),
        "deathdate": date_or_none(row["DEATHDATE"]),
        "gender": text_or_none(row["GENDER"]),
        "race": text_or_none(row["RACE"]),
        "ethnicity": text_or_none(row["ETHNICITY"]),
        "city": text_or_none(row["CITY"]),
        "state": text_or_none(row["STATE"]),
    }


def condition(row: Row) -> dict[str, Any]:
    """Map one conditions.csv row to table columns."""
    return {
        "patient_id": row["PATIENT"],
        "encounter_id": text_or_none(row["ENCOUNTER"]),
        "start_date": date.fromisoformat(row["START"]),
        "stop_date": date_or_none(row["STOP"]),
        "code": row["CODE"],
        "description": row["DESCRIPTION"],
    }


def medication(row: Row) -> dict[str, Any]:
    """Map one medications.csv row to table columns."""
    return {
        "patient_id": row["PATIENT"],
        "encounter_id": text_or_none(row["ENCOUNTER"]),
        "start_ts": datetime.fromisoformat(row["START"]),
        "stop_ts": timestamp_or_none(row["STOP"]),
        "code": row["CODE"],
        "description": row["DESCRIPTION"],
        "dispenses": int_or_none(row["DISPENSES"]),
        "total_cost": number_or_none(row["TOTALCOST"]),
    }


def encounter(row: Row) -> dict[str, Any]:
    """Map one encounters.csv row to table columns."""
    return {
        "id": row["Id"],
        "patient_id": row["PATIENT"],
        "start_ts": datetime.fromisoformat(row["START"]),
        "stop_ts": timestamp_or_none(row["STOP"]),
        "encounter_class": text_or_none(row["ENCOUNTERCLASS"]),
        "code": text_or_none(row["CODE"]),
        "description": text_or_none(row["DESCRIPTION"]),
        "total_claim_cost": number_or_none(row["TOTAL_CLAIM_COST"]),
        "reason_description": text_or_none(row["REASONDESCRIPTION"]),
    }


# Parents first so foreign keys hold while inserting; reversed for deleting.
TABLES: list[tuple[str, type, Callable[[Row], dict[str, Any]]]] = [
    ("patients", SyntheaPatientRow, patient),
    ("encounters", SyntheaEncounterRow, encounter),
    ("conditions", SyntheaConditionRow, condition),
    ("medications", SyntheaMedicationRow, medication),
]


def load_synthea(session: Session, csv_dir: Path) -> dict[str, int]:
    """Replace the synthea_* tables with the CSV contents; the caller commits or rolls back."""
    # Open every file up front so a missing file fails before anything is deleted.
    for name, _, _ in TABLES:
        if not (csv_dir / f"{name}.csv").is_file():
            raise FileNotFoundError(csv_dir / f"{name}.csv")
    for _, model, _ in reversed(TABLES):
        session.execute(delete(model))
    counts: dict[str, int] = {}
    for name, model, convert in TABLES:
        rows = [convert(row) for row in read_rows(csv_dir / f"{name}.csv")]
        for start in range(0, len(rows), BATCH_SIZE):
            session.execute(insert(model).values(rows[start : start + BATCH_SIZE]))
        counts[name] = len(rows)
    return counts
