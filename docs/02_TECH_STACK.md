# Tech Stack

Complete inventory of every library, framework, and tool used in SocialMind, with rationale for each choice.

---

## Language & Runtime

| Technology | Version | Role | Rationale |
|---|---|---|---|
| **Python** | 3.12+ | Core language | Best ecosystem for DSPy, Playwright, ML tooling, and private API clients |
| **Node.js** | 20 LTS | UI build toolchain | Vite + React for dashboard only; no Node in runtime |
| **Docker** | 24+ | Container runtime | Reproducible environments, easy deployment |
| **Docker Compose** | v2 | Multi-service orchestration | Single-command startup of entire stack |

---

## AI & LLM Layer

### DSPy

| Library | Version | Purpose |
|---|---|---|
| `dspy-ai` | 2.x | Core AI pipeline framework — replaces prompt engineering with compiled modules |
| `openai` | 1.x | DSPy LM provider (GPT-4o, GPT-4o-mini) |
| `anthropic` | 0.x | DSPy LM provider (Claude 3.5 Sonnet, Haiku) |
| `ollama` (Python SDK) | 0.x | DSPy LM provider for local models |
| `litellm` | 1.x | Unified LLM gateway — lets DSPy route to any provider transparently |

**Why DSPy over raw prompting?**
DSPy compiles natural language task descriptions into optimized prompts automatically. This means:
- Switching LLM providers doesn't require rewriting prompts
- Pipelines can be auto-optimized via `BootstrapFewShot`, `MIPRO`, etc.
- Structured I/O via `TypedPredictor` prevents hallucinated schemas

### Embedding & Retrieval

| Library | Purpose |
|---|---|
| `chromadb` | Local vector store for semantic search over scraped content and memory |
| `sentence-transformers` | Embedding model runner (used with Ollama `nomic-embed-text` as primary) |
| `langchain-text-splitters` | Document chunking utilities (no LangChain orchestration used) |

---

## Platform Adapters

### Private API Clients

| Library | Platform | Notes |
|---|---|---|
| `instagrapi` | Instagram | Reverse-engineered Instagram private API. Session-based, no official approval needed |
| `tikhub` / `pyktok` | TikTok | TikTok private API wrappers; browser automation primary fallback |
| `praw` | Reddit | Official Reddit API (free tier). Rate limited but officially supported |
| `yt-dlp` | YouTube | Scraping and downloading; use YouTube Data API v3 for uploads |
| `google-api-python-client` | YouTube | Official API for uploads, comments, channel management |
| `tweepy` | X (Twitter) | Official API v2. Free tier has heavy limits; browser automation fills gaps |
| `facebook-sdk` | Facebook | Official Graph API where scope allows; Playwright for the rest |

### Browser Automation

| Library | Purpose |
|---|---|
| `playwright` (async) | Primary browser automation engine — Chromium, Firefox, WebKit |
| `playwright-stealth` | Patches Playwright to evade bot detection (removes `navigator.webdriver`, spoofs canvas, etc.) |
| `rebrowser-patches` | Additional Chromium-level patches for advanced bot detection bypass |
| `fake-useragent` | Real-world user agent rotation database |
| `undetected-playwright` | Fork of Playwright with additional stealth patches |

**Why Playwright over Selenium?**
- Native async support (critical for managing 10–100 concurrent sessions)
- Better stealth patching ecosystem
- Built-in browser context isolation (one context per account)
- Faster and more reliable than Selenium

---

## Web Framework & API

| Library | Purpose |
|---|---|
| `fastapi` | Async REST API for web dashboard backend |
| `uvicorn` | ASGI server |
| `pydantic` v2 | Request/response validation, settings management |
| `pydantic-settings` | `.env` file parsing and settings injection |
| `python-multipart` | File upload handling (media uploads) |
| `httpx` | Async HTTP client (used in adapters for private API calls) |
| `websockets` | Real-time log streaming to dashboard |

---

## Database & Storage

| Technology | Purpose | Rationale |
|---|---|---|
| **PostgreSQL** 16 | Primary relational database | Accounts, tasks, logs, campaigns — structured relational data |
| **Redis** 7 | Message broker + cache + session store | Celery broker, rate limit counters, proxy pool cache |
| **SQLAlchemy** 2.x | Async ORM | Type-safe DB access, works with Alembic migrations |
| **Alembic** | Database migrations | Version-controlled schema changes |
| **MinIO** | Object storage (S3-compatible) | Stores generated images, videos, downloaded media locally |
| **ChromaDB** | Vector store | Semantic memory for AI pipelines, trend research cache |

---

## Task Queue & Scheduling

| Library | Purpose |
|---|---|
| `celery` | Distributed task queue — executes all automation actions |
| `celery[redis]` | Redis as Celery broker and result backend |
| `celery-beat` | Cron-style periodic task scheduler |
| `flower` | Celery monitoring web UI |
| `kombu` | Celery's messaging library (transitive dep, configured directly) |

---

## MCP Server

| Library | Purpose |
|---|---|
| `mcp` (Anthropic Python SDK) | MCP server implementation |
| `sse-starlette` | Server-Sent Events transport for MCP over HTTP |

The MCP server is implemented as a Starlette app mounted on FastAPI, exposing all automation tools to external AI agents.

---

## Stealth & Anti-Detection

| Library | Purpose |
|---|---|
| `playwright-stealth` | Browser fingerprint patching |
| `gologin` (API client) | Cloud antidetect browser profiles (optional premium feature) |
| `python-socks` | SOCKS4/5 proxy support for HTTP clients |
| `aiohttp-socks` | Async SOCKS proxy support |
| `curl-cffi` | HTTP client that mimics browser TLS fingerprints (curl-impersonate) |
| `fake-useragent` | User agent rotation |
| Custom timing engine | Gaussian-distributed delays mimicking human behavior |

---

## Content Generation & Media

| Library | Purpose |
|---|---|
| `Pillow` | Image manipulation, resizing, watermarking |
| `ffmpeg-python` | Video processing (trim, transcode, add audio, generate reels) |
| `openai` (images) | DALL-E image generation via OpenAI API |
| `diffusers` + `torch` | Local image generation via Stable Diffusion (optional, GPU) |
| `moviepy` | High-level video editing (overlays, text, transitions) |
| `yt-dlp` | Download reference content from YouTube for research |
| `beautifulsoup4` | HTML parsing for web scraping in research pipelines |
| `trafilatura` | Clean article text extraction from web pages |

---

## Web Dashboard (Frontend)

| Technology | Purpose |
|---|---|
| **React** 18 | UI component framework |
| **Vite** | Build tool and dev server |
| **TypeScript** | Type safety in UI code |
| **TanStack Query** | Server state management + API caching |
| **TanStack Router** | Type-safe file-based routing |
| **shadcn/ui** | Accessible component library (Radix UI + Tailwind) |
| **Tailwind CSS** | Utility-first styling |
| **Recharts** | Dashboard charts (task throughput, engagement metrics) |
| **Zustand** | Lightweight client-side state (auth, UI state) |
| **Socket.IO client** | Real-time log streaming from backend |

---

## Developer Tooling

| Tool | Purpose |
|---|---|
| `ruff` | Extremely fast Python linter + formatter (replaces black, isort, flake8) |
| `mypy` | Static type checking |
| `pytest` | Test runner |
| `pytest-asyncio` | Async test support |
| `pytest-playwright` | Browser automation testing |
| `factory-boy` | Test data factories |
| `pre-commit` | Git hooks for linting |
| `typer` | CLI framework (management commands) |
| `rich` | Beautiful terminal output for CLI |
| `loguru` | Structured logging with rotation |
| `sentry-sdk` | Error tracking (optional, self-hosted Sentry or Sentry.io) |

---

## Infrastructure & DevOps

| Tool | Purpose |
|---|---|
| **Docker** | Container runtime |
| **Docker Compose** | Multi-service local orchestration |
| **Nginx** | Reverse proxy in front of FastAPI + UI (production) |
| **Traefik** | Alternative to Nginx with automatic TLS (optional) |
| **GitHub Actions** | CI/CD pipeline |
| **Watchtower** | Auto-pull updated Docker images in production |

---

## Dependency Management

```toml
# pyproject.toml (excerpt)
[tool.poetry]
name = "socialmind"
version = "0.1.0"
python = "^3.12"

[tool.poetry.dependencies]
# AI
dspy-ai = "^2.0"
litellm = "^1.0"
chromadb = "^0.5"
sentence-transformers = "^3.0"

# Platform adapters
instagrapi = "^2.0"
praw = "^7.0"
tweepy = "^4.0"
google-api-python-client = "^2.0"
yt-dlp = "*"
httpx = "^0.27"
curl-cffi = "^0.7"

# Browser automation
playwright = "^1.44"
playwright-stealth = "^1.0"
fake-useragent = "^1.5"

# Web framework
fastapi = "^0.111"
uvicorn = {extras = ["standard"], version = "^0.29"}
pydantic = "^2.7"
pydantic-settings = "^2.2"

# Database
sqlalchemy = {extras = ["asyncio"], version = "^2.0"}
alembic = "^1.13"
asyncpg = "^0.29"
redis = {extras = ["hiredis"], version = "^5.0"}

# Task queue
celery = {extras = ["redis"], version = "^5.4"}
flower = "^2.0"

# MCP
mcp = "^1.0"

# Media
Pillow = "^10.0"
ffmpeg-python = "^0.2"
moviepy = "^1.0"

# Stealth
python-socks = "^2.0"

# Utilities
loguru = "^0.7"
typer = "^0.12"
rich = "^13.0"
```

---

## Version Pinning Strategy

- **AI libraries** (`dspy-ai`, `litellm`): Pin minor version, allow patch updates. These change rapidly.
- **Platform adapter libraries** (`instagrapi`, `praw`): Pin exact version. Platform API changes can silently break these.
- **Infrastructure libraries** (`sqlalchemy`, `celery`): Pin minor version.
- **Docker base images**: Always pin to a specific digest in production.

---

## Why Not LangChain?

LangChain was evaluated and rejected for the following reasons:

1. **DSPy is more appropriate** — Our use case requires optimizable, compiled AI pipelines, not chains of prompt templates
2. **Complexity without benefit** — LangChain adds significant abstraction overhead for no gain over direct library usage
3. **DSPy's `Retrieve` modules** replace LangChain's retrieval abstractions cleanly
4. **Faster iteration** — DSPy modules are plain Python classes; no framework-specific patterns to learn

---

## Why Not Selenium?

Playwright was chosen over Selenium because:
- Native Python async/await (Selenium requires `selenium-wire` or thread hacks)
- Superior browser context isolation for multi-account management
- Better maintained stealth patching ecosystem (`playwright-stealth`)
- Faster execution and more reliable element detection
- Built-in network interception for request/response inspection
