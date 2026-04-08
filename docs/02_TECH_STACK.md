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
| `chromadb` | Planned local vector store for semantic search over scraped content and memory |
| `dspy` / `openai` | Embeddings via `dspy.Embedder` (currently `openai/text-embedding-3-small`) |
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
| `google-api-python-client` | YouTube | Optional API client for uploads/comments; install only when YouTube automation is enabled |
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
| `ruff` | Fast linting and formatting |
| `mypy` | Static type checking |
| `pytest` | Test runner |
| `uv` | Dependency resolution, lockfile generation, and environment syncing |

---

## Dependency Management

```toml
# pyproject.toml (excerpt)
[project]
name = "socialmind"
version = "0.1.0"
requires-python = ">=3.12,<4.0"
dependencies = [
  "fastapi>=0.111,<0.112",
  "uvicorn[standard]>=0.29,<0.30",
  "sqlalchemy[asyncio]>=2.0,<3.0",
  "celery[redis]>=5.4,<6.0",
  "playwright>=1.44,<2.0",
]

[project.optional-dependencies]
dev = ["ruff>=0.4,<0.5", "mypy>=1.10,<2.0", "pytest>=8.0,<9.0"]
```

- Run `uv lock` to regenerate `uv.lock`
- Run `uv sync --python 3.12 --extra dev` for local development
- Run `uv sync --frozen --no-dev --no-install-project` in Docker builds
- Enable optional integrations with extras such as `browser`, `media`, `social-instagram`, `social-reddit`, `social-twitter`, and `social-youtube`
- Use `bun install` / `bun run build` for the UI package manager and production bundle

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
