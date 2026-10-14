"""Add per call token usage to eval_results, so tokens and cost are counted per run.

Revision ID: 0015
Revises: 0014
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """A nullable column: rows stored before this change have no per call numbers, not zeros."""
    op.add_column("eval_results", sa.Column("usage", JSONB, nullable=True))


def downgrade() -> None:
    """Drop the usage column."""
    op.drop_column("eval_results", "usage")
