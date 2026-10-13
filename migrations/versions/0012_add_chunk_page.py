"""Add chunks.page: the source page for PDFs, null for sources without pages.

Revision ID: 0012
Revises: 0011
"""

import sqlalchemy as sa
from alembic import op

revision = "0012"
down_revision = "0011"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add a nullable column, so existing rows and page-less sources stay valid."""
    op.add_column("chunks", sa.Column("page", sa.Integer(), nullable=True))


def downgrade() -> None:
    """Remove the column again."""
    op.drop_column("chunks", "page")
