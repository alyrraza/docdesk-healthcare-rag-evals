"""Create eval_runs and eval_results.

Revision ID: 0009
Revises: 0008
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "0009"
down_revision = "0008"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add runs and their per item results."""
    op.create_table(
        "eval_runs",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("config_id", sa.String(64), nullable=False),
        sa.Column("prompt_bundle_id", sa.String(64), nullable=True),
        sa.Column("split", sa.String(8), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("git_sha", sa.String(40), nullable=False),
        sa.CheckConstraint("split IN ('dev', 'test')", name="ck_eval_runs_split"),
    )
    op.create_table(
        "eval_results",
        sa.Column(
            "run_id",
            sa.Uuid(),
            sa.ForeignKey("eval_runs.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("item_id", sa.String(64), primary_key=True),
        sa.Column("metrics", JSONB(), nullable=False),
        sa.Column("failure_label", sa.String(64), nullable=True),
        sa.Column("trace", JSONB(), nullable=False),
    )


def downgrade() -> None:
    """Drop results before runs."""
    op.drop_table("eval_results")
    op.drop_table("eval_runs")
