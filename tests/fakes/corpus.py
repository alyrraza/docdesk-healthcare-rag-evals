"""Helpers that write users, documents and chunks with hand-made vectors into a test session."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

import numpy as np
from sqlalchemy.orm import Session

from docdesk.db.models.chunks import EMBEDDING_DIM, ChunkRow
from docdesk.db.models.documents import DocumentStatus
from docdesk.db.repositories.documents import Document, DocumentRepository
from docdesk.db.repositories.users import UserRepository


def one_hot(index: int) -> list[float]:
    """A unit vector with a single 1, so cosine distance between two of them is 0 or 1."""
    vector = [0.0] * EMBEDDING_DIM
    vector[index] = 1.0
    return vector


@dataclass
class Corpus:
    """Small builder so a retrieval test reads like a story."""

    session: Session

    def user(self) -> uuid.UUID:
        email = f"{uuid.uuid4().hex}@example.com"
        return UserRepository(self.session).add(email, "hash", "user").id

    def document(
        self,
        owner: uuid.UUID,
        title: str = "Label",
        shared: bool = False,
        status: DocumentStatus = DocumentStatus.READY,
    ) -> Document:
        repo = DocumentRepository(self.session)
        document = repo.add(owner, title, "upload", uuid.uuid4().hex, is_shared=shared)
        return repo.set_status(document.id, status)

    def chunk(self, document: Document, text: str, hot: int, position: int = 0) -> ChunkRow:
        row = ChunkRow(
            document_id=document.id,
            position=position,
            text=text,
            token_count=len(text.split()),
            embedding=one_hot(hot),
            chunker_version="fixed.v1",
            embed_model_version="test@1",
        )
        self.session.add(row)
        self.session.flush()
        return row


class FixedEncoder:
    """Embeds every question as the same one-hot vector, so a test controls what is nearest."""

    model_name = "fixed"
    revision = "1"
    max_length = 256

    def __init__(self, hot: int = 0) -> None:
        self.hot = hot

    def encode(self, texts: list[str]) -> np.ndarray:
        return np.array([one_hot(self.hot) for _ in texts], dtype=np.float32)
