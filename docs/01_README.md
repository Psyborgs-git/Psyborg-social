# SocialMind — AI-Powered Social Media Automation Platform

> A self-hosted, Docker-deployable system for automating social media activity across Instagram, TikTok, Reddit, YouTube, Facebook, X (Twitter), Threads, and LinkedIn — powered by DSPy AI pipelines, full stealth infrastructure, and an MCP server for agent-first access.

---

## What This Is

SocialMind is a **team-scale automation library and platform** designed to manage 10–100 social media accounts across 8 platforms. It behaves like a human — composing posts, replying to DMs, commenting, researching trends, scheduling content — using AI pipelines built on DSPy, with support for local models (Ollama) and any LLM provider DSPy supports.

It is **not** a tool that relies on approved developer APIs (most platforms won't approve this use case). Instead, it uses a dual-layer approach:

- **Private API clients** — reverse-engineered Python libraries that mimic official app behavior at the HTTP level
- **Browser automation** — Playwright-based fallback for actions not covered by private APIs, with full stealth (fingerprint spoofing, proxy rotation, human timing)

---

## Core Capabilities

| Capability | Description |
|---|---|
| **Multi-account management** | Connect and manage 10–100 accounts across 8 platforms |
| **AI content generation** | DSPy pipelines generate posts, replies, comments, DMs |
| **Multimedia support** | Text, images (AI-generated or uploaded), video, reels, stories |
| **Autonomous engagement** | Like, comment, follow, DM, reply — all with human-like timing |
| **Trend research** | Scrape and summarize trending content per niche per platform |
| **Task scheduling** | Celery + Redis job queue for cron-style and event-driven tasks |
| **MCP server** | Expose all tools to AI agents via the Model Context Protocol |
| **Web dashboard** | React UI to configure accounts, view logs, manage campaigns |
| **Full stealth** | Proxy rotation, browser fingerprint spoofing, randomized delays |
| **Docker-first** | Single `docker-compose up` to run the entire stack |

---

## Quick Start

### Prerequisites

- Docker + Docker Compose v2
- 16 GB RAM recommended (for local Ollama models)
- GPU optional but recommended for Ollama inference

### 1. Clone and configure

```bash
git clone https://github.com/your-org/socialmind.git
cd socialmind
cp .env.example .env
# Edit .env with your proxy provider credentials, LLM settings, etc.
```

### 2. Start the stack

```bash
docker compose up -d --build
```

The default Compose setup connects the containers to a PostgreSQL cluster running on the host machine at `localhost:5432`. If you prefer a containerized database, start the optional profile with `docker compose --profile docker-db up -d postgres`.

This starts:
- `api` — FastAPI backend (port 8000)
- `worker` — Celery task worker
- `beat` — Celery scheduler
- `redis` — Message broker + cache
- host PostgreSQL cluster — Primary database (default)
- `postgres` — Optional PostgreSQL service behind the `docker-db` profile
- `ollama` — Local LLM server (port 11434)
- `mcp` — MCP server (port 8001)
- `ui` — Bun-built React dashboard (port 3000)
- `flower` — Celery monitoring UI (port 5555)

### 3. Pull your first Ollama model

```bash
docker compose exec ollama ollama pull llama3.2
docker compose exec ollama ollama pull nomic-embed-text
```

### 4. Add your first account

```bash
# Via CLI
docker exec -it socialmind-api python -m socialmind.cli account add \
  --platform instagram \
  --username myaccount \
  --password mypassword \
  --proxy socks5://user:pass@proxy.host:port

# Or via the Web UI at http://localhost:3000
```

### 5. Create your first automation task

```bash
docker exec -it socialmind-api python -m socialmind.cli task create \
  --account myaccount \
  --type post \
  --schedule "0 9 * * *" \
  --prompt "Write a motivational post about entrepreneurship"
```

---

## Repository Structure

```
socialmind/
├── socialmind/                    # Core Python package
│   ├── adapters/                  # Platform adapters
│   │   ├── base.py                # Abstract base adapter interface
│   │   ├── instagram/             # instagrapi + Playwright
│   │   ├── tiktok/                # TikTok private API + Playwright
│   │   ├── reddit/                # PRAW + Playwright
│   │   ├── youtube/               # yt-dlp + Playwright
│   │   ├── facebook/              # Playwright + Graph API where possible
│   │   ├── twitter/               # Tweepy + Playwright
│   │   └── threads/               # Playwright + Instagram Graph API
│   ├── ai/                        # DSPy AI pipelines
│   │   ├── signatures/            # DSPy Signature definitions
│   │   ├── modules/               # DSPy Module implementations
│   │   ├── pipelines/             # Composed multi-step pipelines
│   │   └── optimizers/            # DSPy optimizer configs
│   ├── stealth/                   # Anti-detection infrastructure
│   │   ├── proxy.py               # Proxy pool manager
│   │   ├── fingerprint.py         # Browser fingerprint spoofing
│   │   ├── timing.py              # Human-like delay engine
│   │   └── session.py             # Session persistence & rotation
│   ├── scheduler/                 # Task scheduling
│   │   ├── tasks.py               # Celery task definitions
│   │   ├── beat.py                # Celery beat schedule
│   │   └── workflows.py           # Multi-step task chains
│   ├── mcp/                       # MCP server
│   │   ├── server.py              # MCP server entry point
│   │   ├── tools/                 # MCP tool definitions
│   │   └── resources/             # MCP resource definitions
│   ├── api/                       # FastAPI web API
│   │   ├── routers/               # Route handlers
│   │   ├── schemas/               # Pydantic request/response schemas
│   │   └── dependencies.py        # FastAPI dependency injection
│   ├── models/                    # SQLAlchemy ORM models
│   ├── content/                   # Media handling
│   │   ├── image.py               # Image generation + processing
│   │   ├── video.py               # Video processing
│   │   └── media_store.py         # Media storage abstraction
│   ├── config/                    # Configuration management
│   │   ├── settings.py            # Pydantic Settings
│   │   └── logging.py             # Structured logging setup
│   └── cli.py                     # Typer CLI
├── ui/                            # React + Vite web dashboard
├── docker/                        # Dockerfiles per service
├── migrations/                    # Alembic DB migrations
├── tests/                         # pytest test suite
├── docker-compose.yml
├── docker-compose.dev.yml
├── .env.example
└── pyproject.toml
```

---

## Documentation Index

| File | Description |
|---|---|
| `01_README.md` | This file — overview and quick start |
| `02_TECH_STACK.md` | All libraries, frameworks, and tools with rationale |
| `03_ARCHITECTURE.md` | System architecture, components, data flow diagrams |
| `04_DATA_MODELS.md` | Database schema and ORM model definitions |
| `05_PLATFORM_ADAPTERS.md` | Per-platform adapter design and API/browser strategies |
| `06_ANTI_DETECTION.md` | Stealth infrastructure — proxies, fingerprinting, timing |
| `07_DSPY_PIPELINES.md` | AI pipeline design with DSPy signatures and modules |
| `08_MCP_SERVER.md` | MCP server design, tools catalog, transport |
| `09_TASK_SCHEDULER.md` | Celery task queue, beat schedule, workflow chains |
| `10_CONTENT_PIPELINE.md` | Multimedia content generation and processing |
| `11_WEB_UI.md` | Dashboard architecture, components, API contract |
| `12_DESIGN_PATTERNS.md` | Design patterns used throughout the codebase |
| `13_DEPLOYMENT.md` | Docker Compose, environment config, production hardening |
| `14_SECURITY.md` | Credential management, secrets, account safety |

---

## Legal & Ethical Notice

This software automates interactions on platforms that may prohibit automated access in their Terms of Service. Using this software may result in account bans or legal action from platforms. It is your responsibility to understand and comply with the laws and terms applicable in your jurisdiction and use case. This project is provided for educational and research purposes.
