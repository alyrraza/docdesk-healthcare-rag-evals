"""Add per item latency to eval_results, so a report can show p50 and p95.

Revision ID: 0017
Revises: 0016
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0017"
down_revision = "0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """A nullable column: rows stored before this change have no timings, not zeros."""
    op.add_column("eval_results", sa.Column("latency", JSONB, nullable=True))


def downgrade() -> None:
    """Drop the latency column."""
    op.drop_column("eval_results", "latency")
