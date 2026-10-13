"""Reads and writes the corpus fingerprint, and compares it with what a config expects."""

from __future__ import annotations

from dataclasses import dataclass, fields

from sqlalchemy.orm import Session

from docdesk.core import clock
from docdesk.db.models.fingerprint import CorpusFingerprintRow


@dataclass(frozen=True)
class CorpusFingerprint:
    """The choices that shape every stored chunk; embedding_model is name@revision."""

    chunker: str
    chunk_size: int
    overlap: int
    embedding_model: str


def differences(stored: CorpusFingerprint, expected: CorpusFingerprint) -> list[str]:
    """Name each field that differs, so a refusal message can say exactly what is wrong."""
    return [
        field.name
        for field in fields(CorpusFingerprint)
        if getattr(stored, field.name) != getattr(expected, field.name)
    ]


class FingerprintRepository:
    """Access to the single fingerprint row."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def read(self) -> CorpusFingerprint | None:
        """Return the fingerprint, or None when no corpus has been loaded by the script yet."""
        row = self._session.get(CorpusFingerprintRow, 1)
        if row is None:
            return None
        return CorpusFingerprint(row.chunker, row.chunk_size, row.overlap, row.embedding_model)

    def write(self, fingerprint: CorpusFingerprint) -> None:
        """Replace the row, because the corpus has exactly one current way of being built."""
        self._session.merge(
            CorpusFingerprintRow(
                id=1,
                chunker=fingerprint.chunker,
                chunk_size=fingerprint.chunk_size,
                overlap=fingerprint.overlap,
                embedding_model=fingerprint.embedding_model,
                written_at=clock.utc_now(),
            )
        )
        self._session.flush()
