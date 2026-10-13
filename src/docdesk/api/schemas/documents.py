"""Response models for the document routes."""

from __future__ import annotations

from pydantic import BaseModel

from docdesk.db.repositories.documents import Document


class DocumentOut(BaseModel):
    """What the API says about a document; never the file path or the content hash."""

    id: str
    title: str
    status: str
    chunk_count: int
    fail_reason: str | None
    created_at: str

    @classmethod
    def from_document(cls, document: Document) -> DocumentOut:
        """Convert the repository dataclass to the public shape."""
        return cls(
            id=str(document.id),
            title=document.title,
            status=document.status.value,
            chunk_count=document.chunk_count,
            fail_reason=document.fail_reason,
            created_at=document.created_at.isoformat(),
        )


class UploadOut(DocumentOut):
    """The upload answer also says whether this file had already been uploaded."""

    duplicate: bool
