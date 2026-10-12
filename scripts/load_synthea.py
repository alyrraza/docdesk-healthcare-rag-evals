"""Download the public Synthea sample CSVs and load them into the synthea_* tables (T032).

Usage:
    python scripts/load_synthea.py --database main            # load into DATABASE_URL
    python scripts/load_synthea.py --database test            # load into TEST_DATABASE_URL
    python scripts/load_synthea.py --database main --download # fetch the zip first

The database must already be migrated (alembic upgrade head). Synthea data is synthetic.
Only the columns the SQL branch may see are stored; names, SSN and addresses are dropped.
"""

from __future__ import annotations

import argparse
import zipfile
from pathlib import Path
from urllib.request import urlopen

from dotenv import dotenv_values
from sqlalchemy.orm import Session

from docdesk.db.session import make_engine
from docdesk.db.synthea import TABLES, load_synthea

URL = "https://synthetichealth.github.io/synthea-sample-data/downloads/latest/"
ZIP_NAME = "synthea_sample_data_csv_latest.zip"
DATA_DIR = Path("data/synthea")


def download(target: Path) -> None:
    """Fetch the sample zip and extract only the CSV files we use, never trusting archive paths."""
    zip_dir, csv_dir = target / "zip", target / "csv"
    zip_dir.mkdir(parents=True, exist_ok=True)
    csv_dir.mkdir(parents=True, exist_ok=True)
    zip_path = zip_dir / ZIP_NAME
    with urlopen(URL + ZIP_NAME, timeout=120) as response:  # noqa: S310 - fixed https url
        zip_path.write_bytes(response.read())
    wanted = {f"{name}.csv" for name, _, _ in TABLES}
    with zipfile.ZipFile(zip_path) as archive:
        for member in archive.namelist():
            if member in wanted:  # exact top level names only, so no path tricks
                (csv_dir / member).write_bytes(archive.read(member))


def database_url(which: str) -> str:
    """Pick the database from .env; the choice is explicit so main is never loaded by accident."""
    key = "DATABASE_URL" if which == "main" else "TEST_DATABASE_URL"
    url = dotenv_values(".env").get(key)
    if not url:
        raise SystemExit(f"{key} is missing from .env")
    return url


def main() -> None:
    """Parse arguments, optionally download, then load inside one transaction."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--database", choices=["main", "test"], required=True)
    parser.add_argument("--download", action="store_true", help="fetch the sample data first")
    args = parser.parse_args()
    if args.download:
        download(DATA_DIR)
    engine = make_engine(database_url(args.database))
    with Session(engine) as session:
        counts = load_synthea(session, DATA_DIR / "csv")
        session.commit()
    print(f"loaded into {args.database}: {counts}")


if __name__ == "__main__":
    main()
