"""Alembic environment: the database url comes from the caller or from settings."""

from logging.config import fileConfig

from alembic import context

from docdesk.db.models import Base
from docdesk.db.session import make_engine

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

# Every table model hangs off Base, so autogenerate can compare against the database.
target_metadata = Base.metadata


def database_url() -> str:
    """Prefer a url handed in by tests so they never touch DATABASE_URL."""
    url = config.attributes.get("url")
    if url:
        return url
    from docdesk.core.config import get_settings

    return get_settings().database_url


def readonly_password() -> str | None:
    """Password for the read-only role: from the caller, else from settings, else none."""
    if "readonly_password" in config.attributes:
        return config.attributes["readonly_password"]
    from sqlalchemy.engine import make_url

    from docdesk.core.config import get_settings

    url = get_settings().readonly_database_url
    return make_url(url).password if url else None


def run_migrations_offline() -> None:
    """Emit SQL without a connection, useful for reviewing a migration."""
    context.configure(
        url=database_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations on a real connection inside one transaction."""
    config.attributes["readonly_password"] = readonly_password()
    with make_engine(database_url()).connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
