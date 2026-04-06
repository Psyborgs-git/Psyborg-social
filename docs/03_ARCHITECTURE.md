# System Architecture

---

## High-Level Overview

SocialMind is organized into five horizontal layers, each with a single responsibility. They communicate through well-defined interfaces — no layer reaches down more than one level.

```
┌─────────────────────────────────────────────────────────────────────┐
│                        INTERFACE LAYER                              │
│  ┌────────────────────────┐    ┌─────────────────────────────────┐  │
│  │    React Web Dashboard  │    │      MCP Server (HTTP/SSE)      │  │
│  │    (port 3000)          │    │      (port 8001)                │  │
│  └───────────┬────────────┘    └────────────────┬────────────────┘  │
└──────────────┼──────────────────────────────────┼───────────────────┘
               │ REST + WebSocket                  │ MCP Protocol
┌──────────────▼──────────────────────────────────▼───────────────────┐
│                       API LAYER (FastAPI)                            │
│  Accounts │ Tasks │ Campaigns │ Logs │ Media │ Analytics │ Auth      │
│                         (port 8000)                                  │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ Task dispatch
┌──────────────────────────────▼──────────────────────────────────────┐
│                    ORCHESTRATION LAYER                               │
│  ┌───────────────────┐    ┌─────────────────┐    ┌───────────────┐  │
│  │  Celery Workers   │    │  Celery Beat    │    │  DSPy Pipelines│ │
│  │  (task execution) │    │  (scheduling)   │    │  (AI logic)   │  │
│  └────────┬──────────┘    └─────────────────┘    └───────┬───────┘  │
└───────────┼────────────────────────────────────────────  ┼──────────┘
            │ Adapter calls                                │ LLM calls
┌───────────▼──────────────────┐    ┌─────────────────────▼──────────┐
│      ADAPTER LAYER           │    │         AI/LLM LAYER            │
│  Instagram │ TikTok │ Reddit │    │  Ollama  │ OpenAI │ Anthropic  │
│  YouTube   │ Facebook│ X     │    │  (via LiteLLM + DSPy)          │
│  Threads   │         │       │    │  ChromaDB │ Embeddings          │
└───────────┬──────────────────┘    └────────────────────────────────┘
            │
┌───────────▼──────────────────────────────────────────────────────┐
│                    STEALTH LAYER                                  │
│   Proxy Pool │ Browser Fingerprints │ Timing Engine │ Sessions    │
└──────────────────────────────────────────────────────────────────┘
            │
┌───────────▼──────────────────────────────────────────────────────┐
│                 INFRASTRUCTURE LAYER                              │
│  PostgreSQL │ Redis │ MinIO │ ChromaDB │ Playwright Browsers       │
└──────────────────────────────────────────────────────────────────┘
```

---

## Component Deep-Dives

### 1. Adapter Layer

Each platform has an adapter that implements a shared `BasePlatformAdapter` interface. The adapter decides — at runtime — whether to use the private API client or fall back to browser automation, based on action type, session health, and detection risk.

```
BasePlatformAdapter (abstract)
├── post(content: PostContent) → PostResult
├── comment(target_id: str, text: str) → CommentResult
├── reply_dm(dm_id: str, text: str) → DMResult
├── like(target_id: str) → bool
├── follow(user_id: str) → bool
├── get_feed() → list[FeedItem]
├── get_dms() → list[DirectMessage]
├── search(query: str) → list[SearchResult]
└── get_trending(niche: str) → list[TrendingItem]
```

Each platform adapter is internally composed of two sub-adapters:

```python
class InstagramAdapter(BasePlatformAdapter):
    def __init__(self):
        self._api = InstagrapiClient()      # Private API client
        self._browser = PlaywrightSession() # Browser fallback

    async def post(self, content):
        try:
            return await self._api.post(content)
        except (APIError, DetectionError):
            return await self._browser.post(content)
```

### 2. Stealth Layer

Every adapter call flows through the Stealth Layer before hitting a platform. This layer:

- Assigns a proxy from the pool (per-account sticky proxy)
- Injects browser fingerprint configuration
- Wraps the call in human-like timing delays
- Manages session cookies and tokens

See `06_ANTI_DETECTION.md` for full details.

### 3. Orchestration Layer

**Celery Workers** execute automation tasks. Workers are stateless — all state lives in PostgreSQL or Redis. Multiple worker containers can run simultaneously for horizontal scaling.

**Celery Beat** reads the task schedule from PostgreSQL and dispatches tasks to the Celery queue at the right time.

**DSPy Pipelines** are invoked by workers when a task requires AI content generation or decision-making. Pipelines are stateless Python modules that call the configured LLM backend.

### 4. API Layer

FastAPI serves two consumers:
- The **React dashboard** (REST + WebSocket for real-time logs)
- The **MCP server** (internal Python function calls, not HTTP)

The MCP server is a Starlette sub-application mounted on FastAPI at `/mcp`. It exposes the same underlying service functions as the REST API, wrapped as MCP tools.

### 5. AI/LLM Layer

All LLM traffic is routed through **LiteLLM**, which provides a unified interface. DSPy is configured with a LiteLLM backend, so switching from Ollama (local) to Claude or GPT-4 is a single environment variable change.

```
DSPy Module
    → LiteLLM
        → Ollama (local, default)
        → OpenAI (if LITELLM_PROVIDER=openai)
        → Anthropic (if LITELLM_PROVIDER=anthropic)
        → Any other LiteLLM-supported provider
```

---

## Data Flow: Executing an Automation Task

```
1. Celery Beat fires a scheduled task
       │
       ▼
2. Celery worker picks up task from Redis queue
       │
       ▼
3. Worker loads Account from PostgreSQL
   (credentials, proxy assignment, session state)
       │
       ▼
4. Worker calls DSPy pipeline with task context
   (e.g., PostGenerationPipeline with niche + persona)
       │
       ▼
5. DSPy calls LiteLLM → Ollama/OpenAI/Claude
   Returns: structured PostContent object
       │
       ▼
6. If multimedia needed: ContentPipeline generates/processes media
   Stores result in MinIO, returns URL
       │
       ▼
7. Worker calls PlatformAdapter.post(content)
       │
       ├─── Stealth Layer: assign proxy, timing, fingerprint
       │
       ├─── Try: Private API client (instagrapi, etc.)
       │         └── Success → return PostResult
       │
       └─── Fallback: Playwright browser session
                 └── Returns PostResult
       │
       ▼
8. Worker writes TaskLog to PostgreSQL
   (status, result, latency, errors)
       │
       ▼
9. WebSocket pushes log update to dashboard
```

---

## Data Flow: MCP Agent Request

```
External AI Agent (e.g., Claude Desktop)
       │ MCP tool call: "post_to_instagram"
       ▼
MCP Server (port 8001)
       │ Validates tool input schema
       │ Deserializes arguments
       ▼
SocialMindService (internal)
       │ Same service functions used by REST API
       ▼
Celery task dispatched (or executed inline for sync tools)
       │
       ▼
Returns MCP tool result to agent
```

---

## Multi-Account Isolation

Each account runs in complete isolation:

| Resource | Isolation Mechanism |
|---|---|
| Browser session | Separate Playwright `BrowserContext` per account |
| Cookies & storage | Persisted per account in PostgreSQL |
| Proxy | Sticky proxy assignment per account (same IP always) |
| Rate limits | Per-account Redis counters |
| LLM persona | Per-account `persona` field used in DSPy system prompts |
| Media storage | Per-account prefix in MinIO bucket |

---

## Service Map (Docker Compose)

```
Service         Image                    Ports     Depends On
──────────────────────────────────────────────────────────────
api             socialmind/api           8000      postgres, redis
worker          socialmind/api           —         postgres, redis, ollama
beat            socialmind/api           —         postgres, redis
mcp             socialmind/mcp           8001      api (internal)
ui              socialmind/ui            3000      api
postgres        postgres:16              5432      —
redis           redis:7-alpine           6379      —
ollama          ollama/ollama            11434     —
minio           minio/minio              9000,9001 —
chromadb        chromadb/chroma          8002      —
flower          mher/flower              5555      redis
nginx           nginx:alpine             80,443    ui, api, mcp
```

---

## Failure Modes & Recovery

| Failure | Detection | Recovery |
|---|---|---|
| Platform bans account | HTTP 401/403 from adapter | Mark account `suspended`, alert via dashboard, pause tasks |
| Proxy IP blocked | HTTP 429 or CAPTCHA detected | Rotate to next proxy in pool, retry task |
| LLM provider down | LiteLLM timeout | Automatic fallback to next provider in priority list |
| Celery worker crash | Flower monitoring | Docker restart policy `always`; task is requeued (idempotent design) |
| Browser context leaked | Memory usage monitor | Periodic context recycling after N actions |
| PostgreSQL connection lost | SQLAlchemy pool timeout | Exponential backoff retry with circuit breaker |

---

## Scalability Considerations

For the target scale of 10–100 accounts:

- **Workers**: Start with 2 worker containers, each running 4 concurrent tasks (`--concurrency=4`). Scale to 4 workers if needed.
- **Database connections**: Use `asyncpg` connection pool (min=5, max=20 per worker)
- **Browser instances**: Max 1 Playwright browser per worker (browsers are heavy). Use API clients preferentially.
- **Redis memory**: ~50MB for 100 accounts' worth of rate limit counters and session data.
- **Ollama**: Single container on the host GPU. All workers share it via HTTP.

For 500+ accounts, migrate to Kubernetes and replace Celery Beat with a proper scheduler (Temporal or Prefect).
