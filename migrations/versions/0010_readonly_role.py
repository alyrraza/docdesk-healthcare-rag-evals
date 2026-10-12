"""Create the docdesk_readonly role used by the SQL branch.

The role can connect and see the schema but holds no table privileges. The Synthea migration
(T032) grants SELECT on the synthetic tables only. The password comes from the caller through
config.attributes and never from this file.

Revision ID: 0010
Revises: 0009
"""

from alembic import context, op

revision = "0010"
down_revision = "0009"
branch_labels = None
depends_on = None

ROLE = "docdesk_readonly"


def upgrade() -> None:
    """Create the role, set its password if given, and make it read-only by default."""
    op.execute(
        f"""
        DO $$ BEGIN
            IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '{ROLE}') THEN
                CREATE ROLE {ROLE} NOLOGIN;
            END IF;
        END $$
        """
    )
    password = context.config.attributes.get("readonly_password")
    if password:
        # set_config keeps the password out of the SQL text; the DO block reads it back.
        op.get_bind().exec_driver_sql(
            "SELECT set_config('docdesk.readonly_pw', %s, true)", (password,)
        )
        op.execute(
            f"""
            DO $$ BEGIN
                EXECUTE format('ALTER ROLE {ROLE} LOGIN PASSWORD %L',
                               current_setting('docdesk.readonly_pw'));
            END $$
            """
        )
    # Even if a table grant is added by mistake, every transaction of this role is read-only.
    op.execute(f"ALTER ROLE {ROLE} SET default_transaction_read_only = on")
    op.execute(f"REVOKE ALL ON SCHEMA public FROM {ROLE}")
    op.execute(f"GRANT USAGE ON SCHEMA public TO {ROLE}")
    op.execute(
        f"""
        DO $$ BEGIN
            EXECUTE format('GRANT CONNECT ON DATABASE %I TO {ROLE}', current_database());
        END $$
        """
    )


def downgrade() -> None:
    """Remove this database's grants. The role itself stays because roles span all databases."""
    op.execute(f"REVOKE ALL ON ALL TABLES IN SCHEMA public FROM {ROLE}")
    op.execute(f"REVOKE ALL ON SCHEMA public FROM {ROLE}")
    op.execute(
        f"""
        DO $$ BEGIN
            EXECUTE format('REVOKE CONNECT ON DATABASE %I FROM {ROLE}', current_database());
        END $$
        """
    )
