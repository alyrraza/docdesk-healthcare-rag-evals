"""Fakes for ingestion tests: a word counter, a model stand-in and an in-memory file store."""

from __future__ import annotations

import uuid

import numpy as np

from docdesk.db.models.chunks import EMBEDDING_DIM


class WordCounter:
    """One token per whitespace separated word."""

    def count(self, text: str) -> int:
        return len(text.split())


class FakeEncoder:
    """Returns valid unit vectors without loading a model; can be told to fail or send bad data."""

    model_name = "fake-model"
    revision = "rev1"
    max_length = 256

    def __init__(self, fail: bool = False, nan_in_last_row: bool = False) -> None:
        self.fail = fail
        self.nan_in_last_row = nan_in_last_row

    def encode(self, texts: list[str]) -> np.ndarray:
        if self.fail:
            raise RuntimeError("model crashed: secret internal detail")
        vectors = np.zeros((len(texts), EMBEDDING_DIM), dtype=np.float32)
        vectors[np.arange(len(texts)), np.arange(len(texts)) % EMBEDDING_DIM] = 1.0
        if self.nan_in_last_row and len(texts):
            vectors[-1, 0] = np.nan
        return vectors


class FakeStore:
    """Holds uploaded bytes by document id, like the real file store will."""

    def __init__(self) -> None:
        self.files: dict[uuid.UUID, bytes] = {}

    def save(self, document_id: uuid.UUID, data: bytes) -> None:
        self.files[document_id] = data

    def read(self, document_id: uuid.UUID) -> bytes:
        return self.files[document_id]
