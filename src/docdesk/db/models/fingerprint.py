"""The corpus fingerprint: one row that says how the stored chunks were made."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from docdesk.db.models.base import Base


class CorpusFingerprintRow(Base):
    """At most one row; the ingest script rewrites it after every full corpus load."""

    __tablename__ = "corpus_fingerprint"
    __table_args__ = (CheckConstraint("id = 1", name="ck_corpus_fingerprint_single_row"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    chunker: Mapped[str] = mapped_column(String(64), nullable=False)
    chunk_size: Mapped[int] = mapped_column(Integer, nullable=False)
    overlap: Mapped[int] = mapped_column(Integer, nullable=False)
    embedding_model: Mapped[str] = mapped_column(String(128), nullable=False)
    written_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
