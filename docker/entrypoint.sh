#!/bin/sh
set -e

echo "[entrypoint] Waiting for Postgres..."
python - <<'PY'
from __future__ import annotations

import asyncio
import os
import sys

import asyncpg


def normalized_database_url() -> str:
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        raise SystemExit("[entrypoint] DATABASE_URL must be set")
    return database_url.replace("+asyncpg", "", 1)


async def wait_for_postgres() -> None:
    database_url = normalized_database_url()
    timeout_seconds = int(os.getenv("DB_WAIT_TIMEOUT", "120"))
    attempts = max(timeout_seconds, 1)
    last_error: Exception | None = None

    for attempt in range(1, attempts + 1):
        try:
            connection = await asyncpg.connect(database_url, timeout=5)
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt == attempts:
                break
            await asyncio.sleep(1)
        else:
            await connection.close()
            print(f"[entrypoint] PostgreSQL ready after {attempt} attempt(s)")
            return

    raise SystemExit(
        f"[entrypoint] Timed out waiting for PostgreSQL after {timeout_seconds}s: {last_error}"
    )


try:
    asyncio.run(wait_for_postgres())
except SystemExit:
    raise
except Exception as exc:  # noqa: BLE001
    raise SystemExit(f"[entrypoint] PostgreSQL readiness check failed: {exc}") from exc
PY

echo "[entrypoint] Running migrations..."
alembic upgrade head

echo "[entrypoint] Starting: $@"
exec "$@"
