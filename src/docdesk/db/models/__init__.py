"""Table definitions, one file per table group."""

from docdesk.db.models.base import Base
from docdesk.db.models.chunks import ChunkRow
from docdesk.db.models.documents import DocumentRow
from docdesk.db.models.users import UserRow

__all__ = ["Base", "ChunkRow", "DocumentRow", "UserRow"]
