"""Create prompt_versions and active_prompts.

Revision ID: 0007
Revises: 0006
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add the version store and the active pointer."""
    op.create_table(
        "prompt_versions",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("version", sa.String(32), nullable=False),
        sa.Column("content_hash", sa.String(64), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("params", JSONB(), nullable=False),
        sa.Column("schema_version", sa.String(64), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("name", "version", name="uq_prompt_versions_name_version"),
        sa.CheckConstraint(
            "status IN ('draft', 'released', 'retired')", name="ck_prompt_versions_status"
        ),
    )
    op.create_table(
        "active_prompts",
        sa.Column("name", sa.String(64), primary_key=True),
        sa.Column(
            "prompt_version_id",
            sa.Uuid(),
            sa.ForeignKey("prompt_versions.id"),
            nullable=False,
        ),
        sa.Column(
            "activated_by", sa.Uuid(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True
        ),
        sa.Column("activated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    """Drop the pointer first because it references versions."""
    op.drop_table("active_prompts")
    op.drop_table("prompt_versions")
