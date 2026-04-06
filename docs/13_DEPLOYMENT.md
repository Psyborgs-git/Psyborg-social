# Deployment

SocialMind is Docker-first. Everything runs in containers. This document covers the full Docker Compose configuration, environment setup, and production hardening.

---

## docker-compose.yml

```yaml
# docker-compose.yml
version: "3.9"

x-api-common: &api-common
  build:
    context: .
    dockerfile: docker/api.Dockerfile
  environment:
    - DATABASE_URL=postgresql+asyncpg://socialmind:${POSTGRES_PASSWORD}@postgres:5432/socialmind
    - REDIS_URL=redis://redis:6379/0
    - MINIO_ENDPOINT=minio:9000
    - MINIO_ACCESS_KEY=${MINIO_ACCESS_KEY}
    - MINIO_SECRET_KEY=${MINIO_SECRET_KEY}
    - OLLAMA_URL=http://ollama:11434
    - SECRET_KEY=${SECRET_KEY}
    - ENCRYPTION_KEY=${ENCRYPTION_KEY}
    - LLM_PROVIDER=${LLM_PROVIDER:-ollama}
    - OLLAMA_MODEL=${OLLAMA_MODEL:-llama3.2}
    - IMAGE_PROVIDER=${IMAGE_PROVIDER:-dalle}
    - OPENAI_API_KEY=${OPENAI_API_KEY:-}
    - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY:-}
    - MCP_API_KEY=${MCP_API_KEY}
    - CHROMADB_URL=http://chromadb:8002
  volumes:
    - ./socialmind:/app/socialmind   # Dev: live code reload
    - playwright_data:/ms-playwright  # Playwright browser binaries
  depends_on:
    postgres:
      condition: service_healthy
    redis:
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
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # ─── MCP Server ────────────────────────────────────────────────────
  mcp:
    <<: *api-common
    command: uvicorn socialmind.mcp.app:app --host 0.0.0.0 --port 8001 --workers 1
    ports:
      - "8001:8001"
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
      - "3000:3000"
    depends_on:
      - api
    restart: unless-stopped

  # ─── PostgreSQL ─────────────────────────────────────────────────────
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: socialmind
      POSTGRES_USER: socialmind
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U socialmind -d socialmind"]
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
    volumes:
      - ollama_models:/root/.ollama
    ports:
      - "11434:11434"
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: all
              capabilities: [gpu]   # Remove if no GPU
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
  ollama_models:
  minio_data:
  chroma_data:
  playwright_data:
  celery_beat_data:
```

---

## Dockerfiles

```dockerfile
# docker/api.Dockerfile
FROM python:3.12-slim

# System dependencies for Playwright + FFmpeg
RUN apt-get update && apt-get install -y \
    curl wget git ffmpeg \
    # Playwright browser dependencies
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libxkbcommon0 libxcomposite1 \
    libxdamage1 libxfixes3 libxrandr2 libgbm1 libasound2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies
COPY pyproject.toml poetry.lock* ./
RUN pip install poetry==1.8.3 && \
    poetry config virtualenvs.create false && \
    poetry install --no-interaction --no-ansi --no-root

# Install Playwright browsers
RUN playwright install chromium --with-deps

# Copy application
COPY socialmind/ ./socialmind/
COPY migrations/ ./migrations/
COPY alembic.ini ./

# Run DB migrations on startup
COPY docker/entrypoint.sh ./
RUN chmod +x entrypoint.sh
ENTRYPOINT ["./entrypoint.sh"]
```

```bash
#!/bin/bash
# docker/entrypoint.sh
set -e

# Wait for Postgres
echo "Waiting for PostgreSQL..."
until python -c "import asyncpg; import asyncio; asyncio.run(asyncpg.connect('$DATABASE_URL'))"; do
  sleep 1
done

# Run migrations
echo "Running DB migrations..."
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

# 3. Start infrastructure first
docker-compose up -d postgres redis minio

# 4. Pull Ollama model (wait for ollama to start)
docker-compose up -d ollama
sleep 10
docker exec socialmind-ollama-1 ollama pull llama3.2
docker exec socialmind-ollama-1 ollama pull nomic-embed-text

# 5. Start everything
docker-compose up -d

# 6. Create MinIO bucket
docker exec socialmind-minio-1 mc alias set local http://localhost:9000 $MINIO_ACCESS_KEY $MINIO_SECRET_KEY
docker exec socialmind-minio-1 mc mb local/socialmind

# 7. Create first admin user
docker exec socialmind-api-1 python -m socialmind.cli user create \
  --username admin \
  --password <your password>

# 8. Open dashboard
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
    command: npm run dev -- --host 0.0.0.0 --port 3000
    volumes:
      - ./ui:/app
      - /app/node_modules
```

```bash
# Start in dev mode
docker-compose -f docker-compose.yml -f docker-compose.dev.yml up
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
# Automated daily PostgreSQL backup
docker exec socialmind-postgres-1 pg_dump -U socialmind socialmind | gzip > backup_$(date +%Y%m%d).sql.gz

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
