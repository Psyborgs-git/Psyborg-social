#!/bin/sh
set -e

echo "[entrypoint] Waiting for Postgres..."
until pg_isready -h "${POSTGRES_HOST:-postgres}" -U "${POSTGRES_USER:-socialmind}" 2>/dev/null; do
    sleep 1
done

echo "[entrypoint] Running migrations..."
alembic upgrade head

echo "[entrypoint] Starting: $@"
exec "$@"
