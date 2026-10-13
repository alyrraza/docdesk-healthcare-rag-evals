"""Local disk store for uploaded files, one file per document id."""

from __future__ import annotations

import uuid
from pathlib import Path


class LocalFileStore:
    """Keeps the original bytes so the worker can read them after the upload request has ended."""

    def __init__(self, root: Path) -> None:
        self._root = root

    def save(self, document_id: uuid.UUID, data: bytes) -> None:
        """Write the upload, naming the file by id so a user's file name never touches the disk."""
        self._root.mkdir(parents=True, exist_ok=True)
        (self._root / str(document_id)).write_bytes(data)

    def read(self, document_id: uuid.UUID) -> bytes:
        """Return the stored bytes, or say which document is missing."""
        path = self._root / str(document_id)
        if not path.is_file():
            raise FileNotFoundError(f"no stored file for document {document_id}")
        return path.read_bytes()
