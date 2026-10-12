"""Add the HNSW cosine index on chunk embeddings (choice recorded in DECISIONS.md, T027).

Revision ID: 0006
Revises: 0005
"""

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Approximate nearest neighbour search needs an index; HNSW needs no training data."""
    op.execute(
        "CREATE INDEX ix_chunks_embedding_hnsw ON chunks "
        "USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)"
    )


def downgrade() -> None:
    """Drop the index."""
    op.execute("DROP INDEX ix_chunks_embedding_hnsw")
