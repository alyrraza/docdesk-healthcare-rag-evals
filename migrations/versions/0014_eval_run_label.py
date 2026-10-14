"""Add an optional label to eval_runs, so a smoke run can be told from a full run.

Revision ID: 0014
Revises: 0013
"""

import sqlalchemy as sa
from alembic import op

revision = "0014"
down_revision = "0013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """A nullable column: runs made before this change simply have no label."""
    op.add_column("eval_runs", sa.Column("label", sa.String(128), nullable=True))


def downgrade() -> None:
    """Drop the label column."""
    op.drop_column("eval_runs", "label")
