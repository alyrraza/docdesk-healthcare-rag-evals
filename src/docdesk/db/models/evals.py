"""Evaluation runs and the per item results stored for each run."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from docdesk.db.models.base import Base


class EvalRunRow(Base):
    """One run of one config over one golden split, tied to a git commit."""

    __tablename__ = "eval_runs"
    __table_args__ = (CheckConstraint("split IN ('dev', 'test')", name="ck_eval_runs_split"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    config_id: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt_bundle_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    split: Mapped[str] = mapped_column(String(8), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    git_sha: Mapped[str] = mapped_column(String(40), nullable=False)


class EvalResultRow(Base):
    """The scores, failure label and full trace for one golden item in one run."""

    __tablename__ = "eval_results"

    run_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("eval_runs.id", ondelete="CASCADE"), primary_key=True
    )
    item_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    metrics: Mapped[dict] = mapped_column(JSONB, nullable=False)
    failure_label: Mapped[str | None] = mapped_column(String(64), nullable=True)
    trace: Mapped[dict] = mapped_column(JSONB, nullable=False)
