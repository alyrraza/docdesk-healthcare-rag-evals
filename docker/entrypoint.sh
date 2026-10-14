#!/bin/sh
# Runs the database migrations when RUN_MIGRATIONS=1 (the api service), then starts the command.
set -eu
if [ "${RUN_MIGRATIONS:-0}" = "1" ]; then
    alembic upgrade head
fi
exec "$@"
