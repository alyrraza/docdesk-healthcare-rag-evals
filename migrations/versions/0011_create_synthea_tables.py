"""Create the synthea_* tables and let the read-only role SELECT from them.

Revision ID: 0011
Revises: 0010
"""

import sqlalchemy as sa
from alembic import op

revision = "0011"
down_revision = "0010"
branch_labels = None
depends_on = None

ROLE = "docdesk_readonly"
TABLES = ["synthea_patients", "synthea_conditions", "synthea_medications", "synthea_encounters"]
PATIENT_FK = "synthea_patients.id"


def upgrade() -> None:
    """Add the four tables, then grant SELECT on exactly these tables and nothing else."""
    op.create_table(
        "synthea_patients",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("birthdate", sa.Date(), nullable=False),
        sa.Column("deathdate", sa.Date(), nullable=True),
        sa.Column("gender", sa.String(8), nullable=True),
        sa.Column("race", sa.String(64), nullable=True),
        sa.Column("ethnicity", sa.String(64), nullable=True),
        sa.Column("city", sa.String(128), nullable=True),
        sa.Column("state", sa.String(64), nullable=True),
    )
    op.create_table(
        "synthea_encounters",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "patient_id", sa.Uuid(), sa.ForeignKey(PATIENT_FK, ondelete="CASCADE"), nullable=False
        ),
        sa.Column("start_ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("stop_ts", sa.DateTime(timezone=True), nullable=True),
        sa.Column("encounter_class", sa.String(32), nullable=True),
        sa.Column("code", sa.String(32), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("total_claim_cost", sa.Numeric(12, 2), nullable=True),
        sa.Column("reason_description", sa.Text(), nullable=True),
    )
    op.create_table(
        "synthea_conditions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "patient_id", sa.Uuid(), sa.ForeignKey(PATIENT_FK, ondelete="CASCADE"), nullable=False
        ),
        sa.Column("encounter_id", sa.Uuid(), nullable=True),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("stop_date", sa.Date(), nullable=True),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
    )
    op.create_table(
        "synthea_medications",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "patient_id", sa.Uuid(), sa.ForeignKey(PATIENT_FK, ondelete="CASCADE"), nullable=False
        ),
        sa.Column("encounter_id", sa.Uuid(), nullable=True),
        sa.Column("start_ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("stop_ts", sa.DateTime(timezone=True), nullable=True),
        sa.Column("code", sa.String(32), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("dispenses", sa.Integer(), nullable=True),
        sa.Column("total_cost", sa.Numeric(12, 2), nullable=True),
    )
    for table in ("synthea_conditions", "synthea_medications", "synthea_encounters"):
        op.create_index(f"ix_{table}_patient_id", table, ["patient_id"])
    for table in TABLES:
        op.execute(f"GRANT SELECT ON {table} TO {ROLE}")


def downgrade() -> None:
    """Drop children first because they reference patients."""
    for table in ("synthea_medications", "synthea_conditions", "synthea_encounters"):
        op.drop_table(table)
    op.drop_table("synthea_patients")
