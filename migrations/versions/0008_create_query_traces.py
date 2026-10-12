"""Create the query_traces table.

Revision ID: 0008
Revises: 0007
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None

FALSE = sa.false()


def upgrade() -> None:
    """Add one row per request with JSON columns for the per stage details."""
    op.create_table(
        "query_traces",
        sa.Column("trace_id", sa.String(32), primary_key=True),
        sa.Column(
            "user_id", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("route", sa.String(32), nullable=True),
        sa.Column("question_hash", sa.String(64), nullable=False),
        sa.Column("question_text", sa.Text(), nullable=True),
        sa.Column("config_id", sa.String(64), nullable=True),
        sa.Column("prompt_bundle_id", sa.String(64), nullable=True),
        sa.Column("retrieved", JSONB(), nullable=False, server_default="[]"),
        sa.Column("used_ids", JSONB(), nullable=False, server_default="[]"),
        sa.Column("dropped_ids", JSONB(), nullable=False, server_default="[]"),
        sa.Column("stage_ms", JSONB(), nullable=False, server_default="{}"),
        sa.Column("tokens", JSONB(), nullable=False, server_default="{}"),
        sa.Column("guardrails", JSONB(), nullable=False, server_default="{}"),
        sa.Column("validation", JSONB(), nullable=False, server_default="{}"),
        sa.Column("cost_usd", sa.Numeric(12, 6), nullable=True),
        sa.Column("total_ms", sa.Float(), nullable=True),
        sa.Column("cache_hit", sa.Boolean(), nullable=False, server_default=FALSE),
        sa.Column("source_trace_id", sa.String(32), nullable=True),
        sa.Column("abstained", sa.Boolean(), nullable=False, server_default=FALSE),
        sa.Column("abstain_reason", sa.String(64), nullable=True),
        sa.Column("retry_used", sa.Boolean(), nullable=False, server_default=FALSE),
        sa.Column("finish_reason", sa.String(32), nullable=True),
        sa.Column("error_code", sa.String(64), nullable=True),
    )
    op.create_index("ix_query_traces_user_id", "query_traces", ["user_id"])
    op.create_index("ix_query_traces_created_at", "query_traces", ["created_at"])


def downgrade() -> None:
    """Drop the table."""
    op.drop_table("query_traces")
