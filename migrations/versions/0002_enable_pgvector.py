"""Enable the pgvector extension, in its own migration as the design requires.

Revision ID: 0002
Revises: 0001
"""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Vector columns and similarity search need the extension first."""
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")


def downgrade() -> None:
    """Remove the extension so a downgrade to base leaves a clean database."""
    op.execute("DROP EXTENSION IF EXISTS vector")
