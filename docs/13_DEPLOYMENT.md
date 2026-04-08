# Deployment

SocialMind is Docker-first for application services. The default local topology uses a PostgreSQL cluster running on the host machine while the API, worker, MCP, UI, Redis, Ollama, MinIO, and ChromaDB run in containers. An optional `docker-db` profile is still available if you want Docker to manage PostgreSQL too.

---

## docker-compose.yml

```yaml
# docker-compose.yml
x-api-common: &api-common
  build:
    context: .
    dockerfile: docker/api.Dockerfile
    args:
      UV_EXTRAS: ${UV_EXTRAS:-}
      INSTALL_PLAYWRIGHT: ${INSTALL_PLAYWRIGHT:-false}
  environment:
    - DATABASE_URL=postgresql+asyncpg://${POSTGRES_USER:-socialmind}:${POSTGRES_PASSWORD}@${DATABASE_HOST:-host.docker.internal}:${DATABASE_PORT:-5432}/${DATABASE_NAME:-socialmind}
    - REDIS_URL=redis://redis:6379/0
    - MINIO_ENDPOINT=minio:9000
    - MINIO_ACCESS_KEY=${MINIO_ACCESS_KEY}
    - MINIO_SECRET_KEY=${MINIO_SECRET_KEY}
    - OLLAMA_URL=http://ollama:11434
    - SECRET_KEY=${SECRET_KEY}
    - ENCRYPTION_KEY=${ENCRYPTION_KEY}
    - LLM_PROVIDER=${LLM_PROVIDER:-ollama}
    - OLLAMA_MODEL=${OLLAMA_MODEL:-llama3.2}
    - OLLAMA_EMBED_MODEL=${OLLAMA_EMBED_MODEL:-nomic-embed-text}
    - EMBED_PROVIDER=${EMBED_PROVIDER:-ollama}
    - IMAGE_PROVIDER=${IMAGE_PROVIDER:-dalle}
    - OPENAI_API_KEY=${OPENAI_API_KEY:-}
    - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY:-}
    - MCP_API_KEY=${MCP_API_KEY}
    - MCP_REQUIRE_AUTH=${MCP_REQUIRE_AUTH:-true}
    - CHROMADB_URL=http://chromadb:8002
  extra_hosts:
    - "host.docker.internal:host-gateway"
  depends_on:
    redis:
      condition: service_healthy
    ollama:
      condition: service_healthy
  restart: unless-stopped

services:
  # ─── FastAPI Backend ───────────────────────────────────────────────
  api:
    <<: *api-common
    command: uvicorn socialmind.api.main:app --host 0.0.0.0 --port 8000 --workers 2
    ports:
      - "8000:8000"
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"]
      interval: 30s
      timeout: 10s
      retries: 3

  # ─── MCP Server ────────────────────────────────────────────────────
  mcp:
    <<: *api-common
    command: uvicorn socialmind.mcp.app:app --host 0.0.0.0 --port 8001 --workers 1
    ports:
      - "8001:8001"
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8001/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
    depends_on:
      api:
        condition: service_healthy

  # ─── Celery Worker ─────────────────────────────────────────────────
  worker:
    <<: *api-common
    command: >
      celery -A socialmind.scheduler.celery_app worker
      --loglevel=info
      --concurrency=4
      --queues=high,normal,low
      --hostname=worker@%h
    deploy:
      replicas: 2  # Start with 2 workers; scale as needed

  # ─── Celery Beat (Scheduler) ────────────────────────────────────────
  beat:
    <<: *api-common
    command: >
      celery -A socialmind.scheduler.celery_app beat
      --loglevel=info
      --scheduler=celery.beat:PersistentScheduler
      --schedule=/data/celerybeat-schedule
    volumes:
      - celery_beat_data:/data

  # ─── Flower (Celery Monitor) ────────────────────────────────────────
  flower:
    <<: *api-common
    command: >
      celery -A socialmind.scheduler.celery_app flower
      --port=5555
      --basic_auth=admin:${FLOWER_PASSWORD}
    ports:
      - "5555:5555"

  # ─── React Dashboard ────────────────────────────────────────────────
  ui:
    build:
      context: .
      dockerfile: docker/ui.Dockerfile
    ports:
      - "3000:80"
    depends_on:
      - api
    restart: unless-stopped

  # ─── PostgreSQL (optional local replacement for host DB) ───────────
  postgres:
    image: postgres:16-alpine
    profiles: ["docker-db"]
    environment:
      POSTGRES_DB: ${DATABASE_NAME:-socialmind}
      POSTGRES_USER: ${POSTGRES_USER:-socialmind}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "${POSTGRES_HOST_PORT:-5432}:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER:-socialmind} -d ${DATABASE_NAME:-socialmind}"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  # ─── Redis ──────────────────────────────────────────────────────────
  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes --maxmemory 512mb --maxmemory-policy allkeys-lru
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  # ─── Ollama (Local LLM) ─────────────────────────────────────────────
  ollama:
    image: ollama/ollama:latest
    environment:
      OLLAMA_HOST: 0.0.0.0:11434
    volumes:
      - ollama_data:/root/.ollama
    ports:
      - "11434:11434"
    healthcheck:
      test: ["CMD", "ollama", "list"]
      interval: 15s
      timeout: 10s
      retries: 10
    restart: unless-stopped

  # ─── MinIO (Object Storage) ─────────────────────────────────────────
  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    environment:
      MINIO_ROOT_USER: ${MINIO_ACCESS_KEY}
      MINIO_ROOT_PASSWORD: ${MINIO_SECRET_KEY}
    volumes:
      - minio_data:/data
    ports:
      - "9000:9000"
      - "9001:9001"  # MinIO Console
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"]
      interval: 30s
      timeout: 10s
      retries: 3
    restart: unless-stopped

  # ─── ChromaDB (Vector Store) ────────────────────────────────────────
  chromadb:
    image: chromadb/chroma:latest
    volumes:
      - chroma_data:/chroma/chroma
    ports:
      - "8002:8000"
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
  ollama_data:
  minio_data:
  chroma_data:
  playwright_data:
  celery_beat_data:
```

---

## Dockerfiles

```dockerfile
# docker/api.Dockerfile
FROM ghcr.io/astral-sh/uv:0.10.12 AS uv
FROM python:3.12-slim

WORKDIR /app

ARG UV_EXTRAS=""
ARG INSTALL_PLAYWRIGHT="false"

COPY --from=uv /uv /uvx /bin/

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

ENV VIRTUAL_ENV=/app/.venv
ENV PATH=/app/.venv/bin:$PATH

COPY . .

RUN if [ "$INSTALL_PLAYWRIGHT" = "true" ] && command -v playwright >/dev/null 2>&1; then \
      playwright install chromium --with-deps; \
    fi

COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]
```

```bash
#!/bin/bash
# docker/entrypoint.sh
set -e

# Wait for PostgreSQL using DATABASE_URL
echo "[entrypoint] Waiting for Postgres..."
python - <<'PY'
from __future__ import annotations

import asyncio
import os

import asyncpg


async def wait_for_postgres() -> None:
    database_url = os.environ["DATABASE_URL"].replace("+asyncpg", "", 1)
    timeout_seconds = int(os.getenv("DB_WAIT_TIMEOUT", "120"))
    attempts = max(timeout_seconds, 1)
    last_error = None

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


asyncio.run(wait_for_postgres())
PY

# Run migrations
echo "[entrypoint] Running migrations..."
alembic upgrade head

# Execute the container's command
exec "$@"
```

---

## Environment Configuration

```bash
# .env.example — Copy to .env and fill in values

# ── Security ──────────────────────────────────────────────────────────
SECRET_KEY=<generate with: python -c "import secrets; print(secrets.token_hex(32))">
ENCRYPTION_KEY=<generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())">
MCP_API_KEY=<generate with: python -c "import secrets; print(secrets.token_hex(32))">
FLOWER_PASSWORD=<strong password>

# ── Database ──────────────────────────────────────────────────────────
POSTGRES_PASSWORD=<strong password>

# ── Object Storage ────────────────────────────────────────────────────
MINIO_ACCESS_KEY=socialmind
MINIO_SECRET_KEY=<strong password>

# ── LLM Configuration ─────────────────────────────────────────────────
LLM_PROVIDER=ollama           # ollama | openai | anthropic | litellm
OLLAMA_MODEL=llama3.2         # or mistral, qwen2.5, etc.
OLLAMA_EMBED_MODEL=nomic-embed-text
EMBED_PROVIDER=ollama         # ollama | openai

# Optional: Cloud LLM providers (if LLM_PROVIDER != ollama)
OPENAI_API_KEY=
ANTHROPIC_API_KEY=

# ── Image Generation ──────────────────────────────────────────────────
IMAGE_PROVIDER=dalle          # dalle | stable_diffusion | none
SD_API_URL=http://localhost:7860  # If using local SD

# ── CAPTCHA Solving (optional) ────────────────────────────────────────
CAPTCHA_SOLVER=2captcha       # 2captcha | anticaptcha | capsolver | manual
CAPTCHA_API_KEY=

# ── Application ───────────────────────────────────────────────────────
DEBUG=false
LOG_LEVEL=INFO
```

---

## First-Time Setup

```bash
# 1. Clone repo
git clone https://github.com/your-org/socialmind.git && cd socialmind

# 2. Configure environment
cp .env.example .env
# Edit .env with your values

# 3. Ensure the host PostgreSQL cluster has the app role and database
psql -U postgres -d postgres <<'SQL'
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'socialmind') THEN
        CREATE ROLE socialmind LOGIN PASSWORD 'socialmind';
    ELSE
        ALTER ROLE socialmind WITH LOGIN PASSWORD 'socialmind';
    END IF;
END
$$;
SELECT 'CREATE DATABASE socialmind OWNER socialmind'
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = 'socialmind')\gexec
ALTER DATABASE socialmind OWNER TO socialmind;
GRANT ALL PRIVILEGES ON DATABASE socialmind TO socialmind;
SQL

# Optional: use Docker-managed Postgres instead of the host cluster
# docker compose --profile docker-db up -d postgres

# 4. Start containerized infrastructure
docker compose up -d redis minio chromadb ollama

# 5. Pull Ollama model (wait for ollama to start)
sleep 10
docker compose exec ollama ollama pull llama3.2
docker compose exec ollama ollama pull nomic-embed-text

# 6. Start everything
docker compose up -d --build

# 7. Create MinIO bucket
docker exec socialmind-minio-1 mc alias set local http://localhost:9000 $MINIO_ACCESS_KEY $MINIO_SECRET_KEY
docker exec socialmind-minio-1 mc mb local/socialmind

# 8. Create first admin user
docker exec socialmind-api-1 python -m socialmind.cli user create \
  --username admin \
  --password <your password>

# 9. Open dashboard
open http://localhost:3000
```

---

## Development Mode

```yaml
# docker-compose.dev.yml — Override for development
services:
  api:
    command: uvicorn socialmind.api.main:app --host 0.0.0.0 --port 8000 --reload
    volumes:
      - .:/app  # Mount entire project for hot reload
    environment:
      - DEBUG=true
      - LOG_LEVEL=DEBUG

  worker:
    command: >
      celery -A socialmind.scheduler.celery_app worker
      --loglevel=debug
      --concurrency=2
    volumes:
      - .:/app

  ui:
    # In dev, run Vite dev server directly instead of nginx
    build:
      context: ui
      dockerfile: Dockerfile.dev
    command: bun run dev -- --host 0.0.0.0 --port 3000
    volumes:
      - ./ui:/app
      - /app/node_modules
```

```bash
# Start in dev mode
docker compose -f docker-compose.yml -f docker-compose.dev.yml up
```

---

## Production Hardening

### 1. Secrets Management

Never store secrets in `.env` in production. Use:
- **Docker Swarm secrets** (`docker secret create`)
- **HashiCorp Vault** (recommended for teams)
- **Environment-injected secrets** from your CI/CD system

### 2. Reverse Proxy (Nginx / Traefik)

In production, put Nginx in front of all services:
```nginx
# Route /api/ → api:8000
# Route /mcp/ → mcp:8001
# Route /     → ui:3000
# Route /flower/ → flower:5555 (restrict access)
```

### 3. TLS

Use Traefik with Let's Encrypt for automatic HTTPS:
```yaml
traefik:
  image: traefik:v3
  command:
    - "--certificatesresolvers.letsencrypt.acme.email=you@example.com"
    - "--certificatesresolvers.letsencrypt.acme.storage=/letsencrypt/acme.json"
    - "--certificatesresolvers.letsencrypt.acme.tlschallenge=true"
```

### 4. Backups

```bash
# Automated daily PostgreSQL backup against the default host cluster
PGPASSWORD=$POSTGRES_PASSWORD pg_dump -h localhost -U ${POSTGRES_USER:-socialmind} ${DATABASE_NAME:-socialmind} \
  | gzip > backup_$(date +%Y%m%d).sql.gz

# If you use the optional docker-db profile instead:
# docker exec socialmind-postgres-1 pg_dump -U socialmind socialmind | gzip > backup_$(date +%Y%m%d).sql.gz

# MinIO backup to external S3
mc mirror local/socialmind s3/your-backup-bucket/socialmind/
```

### 5. Resource Limits

```yaml
# In docker-compose.yml, add resource limits per service
services:
  worker:
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: "2.0"
  ollama:
    deploy:
      resources:
        limits:
          memory: 8G
```

### 6. Log Rotation

```yaml
services:
  api:
    logging:
      driver: "json-file"
      options:
        max-size: "100m"
        max-file: "5"
```

---

## Monitoring Stack (Optional)

For production monitoring, add to docker-compose:

```yaml
prometheus:
  image: prom/prometheus
  volumes:
    - ./docker/prometheus.yml:/etc/prometheus/prometheus.yml

grafana:
  image: grafana/grafana
  volumes:
    - grafana_data:/var/lib/grafana
  ports:
    - "3001:3000"
```

FastAPI exposes Prometheus metrics at `/metrics` via `prometheus-fastapi-instrumentator`.
