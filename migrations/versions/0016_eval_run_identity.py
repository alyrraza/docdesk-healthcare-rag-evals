"""Add the run identity to eval_runs, so a resume can check what it is resuming.

Revision ID: 0016
Revises: 0015
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0016"
down_revision = "0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """A nullable column: runs stored before this change have a legacy identity, not a guess."""
    op.add_column("eval_runs", sa.Column("identity", JSONB, nullable=True))


def downgrade() -> None:
    """Drop the identity column."""
    op.drop_column("eval_runs", "identity")
