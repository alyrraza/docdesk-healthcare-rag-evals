"""Empty baseline so the migration chain has a first link.

Revision ID: 0001
Revises:
"""

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Nothing to create yet; real tables arrive in their own migrations."""


def downgrade() -> None:
    """Nothing to undo."""
