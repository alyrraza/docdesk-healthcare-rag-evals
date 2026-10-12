"""The query_traces table: one row per request (AC-OBS-01)."""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, Numeric, String, Text, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from docdesk.db.models.base import Base


class QueryTraceRow(Base):
    """Everything needed to replay and judge one request, kept even when it failed."""

    __tablename__ = "query_traces"
    __table_args__ = (
        Index("ix_query_traces_user_id", "user_id"),
        Index("ix_query_traces_created_at", "created_at"),
    )

    trace_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    # SET NULL keeps the trace for evaluation when an account is deleted.
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    route: Mapped[str | None] = mapped_column(String(32), nullable=True)
    question_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    # Stored only when the user allows it, so it is usually empty.
    question_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    config_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    prompt_bundle_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    retrieved: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    used_ids: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    dropped_ids: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    stage_ms: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    tokens: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    guardrails: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    validation: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    cost_usd: Mapped[Decimal | None] = mapped_column(Numeric(12, 6), nullable=True)
    total_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    cache_hit: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    source_trace_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    abstained: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    abstain_reason: Mapped[str | None] = mapped_column(String(64), nullable=True)
    retry_used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    finish_reason: Mapped[str | None] = mapped_column(String(32), nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
