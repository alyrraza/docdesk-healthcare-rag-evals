"""Remove smoke test leftovers from DATABASE_URL: chosen uploads and orphan stored files.

Usage:
    python scripts/clean_leftovers.py                         list non-seed documents and orphans
    python scripts/clean_leftovers.py --delete-document ID    name each upload to remove (repeat)
    add --apply to really delete; without it nothing changes

Seed documents are never deleted here, and it refuses a database whose name ends in _test.
"""

from __future__ import annotations

import argparse
import sys
import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.engine import make_url

from docdesk.core.config import get_settings
from docdesk.db.models.documents import DocumentRow
from docdesk.db.session import make_engine, make_session_factory
from docdesk.ingestion.cleanup import delete_documents, find_orphan_files
from docdesk.ingestion.seed.reset import SEED_PREFIX


def main(argv: list[str] | None = None) -> int:
    """List what would go, and delete it only when --apply is given."""
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--delete-document", type=uuid.UUID, action="append", default=[])
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(argv)
    settings = get_settings()
    if (make_url(settings.database_url).database or "").endswith("_test"):
        raise SystemExit("Refusing to run: DATABASE_URL points at a test database")
    root = Path(settings.upload_dir)
    with make_session_factory(make_engine(settings.database_url))() as session:
        uploads = session.execute(
            select(DocumentRow).where(~DocumentRow.source.like(f"{SEED_PREFIX}%"))
        ).scalars()
        for row in uploads:
            print(f"non-seed document {row.id} {row.status} chunks={row.chunk_count} {row.title!r}")
        if args.apply and args.delete_document:
            print(f"deleted {delete_documents(session, args.delete_document)} documents")
            session.commit()
        orphans = find_orphan_files(session, root)
        print(f"orphan files: {len(orphans)}")
        if args.apply:
            for path in orphans:
                path.unlink()
            print(f"removed {len(orphans)} files")
    return 0


if __name__ == "__main__":
    sys.exit(main())
