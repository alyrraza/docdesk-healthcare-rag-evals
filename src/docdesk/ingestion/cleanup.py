"""Remove chosen non-seed documents and stored files that no document owns any more."""

from __future__ import annotations

import uuid
from pathlib import Path

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from docdesk.db.models.documents import DocumentRow
from docdesk.ingestion.seed.reset import SEED_PREFIX


def delete_documents(session: Session, document_ids: list[uuid.UUID]) -> int:
    """Delete named documents (their chunks go too) and refuse seed ones, so the corpus is safe."""
    rows = session.execute(select(DocumentRow).where(DocumentRow.id.in_(document_ids))).scalars()
    found = {row.id: row for row in rows}
    for document_id in document_ids:
        if document_id not in found:
            raise LookupError(f"document {document_id} not found")
        if found[document_id].source.startswith(SEED_PREFIX):
            raise ValueError(f"document {document_id} is a seed document, use the reset script")
    session.execute(delete(DocumentRow).where(DocumentRow.id.in_(document_ids)))
    return len(found)


def find_orphan_files(session: Session, root: Path) -> list[Path]:
    """List files named by a document id that no document row has, e.g. after a re-ingest."""
    known = {str(document_id) for document_id in session.execute(select(DocumentRow.id)).scalars()}
    orphans = []
    for path in sorted(root.iterdir()):
        try:
            uuid.UUID(path.name)
        except ValueError:
            continue  # not one of our files, leave it alone
        if path.is_file() and path.name not in known:
            orphans.append(path)
    return orphans
