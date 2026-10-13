"""Create corpus_fingerprint: one row saying how the stored chunks were made.

Revision ID: 0013
Revises: 0012
"""

import sqlalchemy as sa
from alembic import op

revision = "0013"
down_revision = "0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add the single row table; it stays empty until the corpus is loaded by the script."""
    op.create_table(
        "corpus_fingerprint",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("chunker", sa.String(64), nullable=False),
        sa.Column("chunk_size", sa.Integer(), nullable=False),
        sa.Column("overlap", sa.Integer(), nullable=False),
        sa.Column("embedding_model", sa.String(128), nullable=False),
        sa.Column("written_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("id = 1", name="ck_corpus_fingerprint_single_row"),
    )


def downgrade() -> None:
    """Drop the table."""
    op.drop_table("corpus_fingerprint")
