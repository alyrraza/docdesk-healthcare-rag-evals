"""Create the chunks table with a vector column and a generated tsvector column.

Revision ID: 0005
Revises: 0004
"""

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects.postgresql import TSVECTOR

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

EMBEDDING_DIM = 384


def upgrade() -> None:
    """Add chunks, a GIN index for keyword search and a per-document unique position."""
    op.create_table(
        "chunks",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "document_id",
            sa.Uuid(),
            sa.ForeignKey("documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("token_count", sa.Integer(), nullable=False),
        sa.Column("embedding", Vector(EMBEDDING_DIM), nullable=False),
        sa.Column(
            "tsv",
            TSVECTOR(),
            sa.Computed("to_tsvector('english', text)", persisted=True),
            nullable=False,
        ),
        sa.Column("chunker_version", sa.String(64), nullable=False),
        sa.Column("embed_model_version", sa.String(128), nullable=False),
        sa.UniqueConstraint("document_id", "position", name="uq_chunks_document_position"),
    )
    op.create_index("ix_chunks_tsv", "chunks", ["tsv"], postgresql_using="gin")
    op.create_index("ix_chunks_document_id", "chunks", ["document_id"])


def downgrade() -> None:
    """Drop the table and its indexes."""
    op.drop_table("chunks")
