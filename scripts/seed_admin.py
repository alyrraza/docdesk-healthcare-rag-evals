"""Create the first admin user from ADMIN_EMAIL and ADMIN_PASSWORD in .env (T033).

Usage:
    python scripts/seed_admin.py --database main
    python scripts/seed_admin.py --database test

The password is read from .env and is never printed. Running it again does nothing.
"""

from __future__ import annotations

import argparse

from dotenv import dotenv_values
from sqlalchemy.orm import Session

from docdesk.auth.seed import ensure_admin
from docdesk.db.session import make_engine


def main() -> None:
    """Read the admin login and the chosen database from .env, then ensure the admin exists."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--database", choices=["main", "test"], required=True)
    args = parser.parse_args()
    env = dotenv_values(".env")
    url = env.get("DATABASE_URL" if args.database == "main" else "TEST_DATABASE_URL")
    email, password = env.get("ADMIN_EMAIL"), env.get("ADMIN_PASSWORD")
    if not (url and email and password):
        raise SystemExit("Need the database url, ADMIN_EMAIL and ADMIN_PASSWORD in .env")
    with Session(make_engine(url)) as session:
        user, created = ensure_admin(session, email, password)
        session.commit()
    print(f"admin {user.email} {'created' if created else 'already exists'} in {args.database}")


if __name__ == "__main__":
    main()
