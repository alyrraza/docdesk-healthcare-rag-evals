"""The access rule, applied inside the SQL so no leg can return a hidden chunk (AC-RET-05)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import Select, or_

from docdesk.db.models.chunks import ChunkRow
from docdesk.db.models.documents import DocumentRow, DocumentStatus


def restrict_to_visible(query: Select[Any], user_id: uuid.UUID) -> Select[Any]:
    """Join chunks to their documents and keep only ready ones the user owns or that are shared."""
    return query.join(DocumentRow, DocumentRow.id == ChunkRow.document_id).where(
        DocumentRow.status == DocumentStatus.READY.value,
        or_(DocumentRow.owner_id == user_id, DocumentRow.is_shared.is_(True)),
    )
