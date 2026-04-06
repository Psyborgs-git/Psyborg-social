# Data Models

Database schema and ORM model definitions for SocialMind. All models use SQLAlchemy 2.x with async support (asyncpg driver).

---

## Entity Relationship Overview

```
Platform ─────┐
              │ 1:N
Account ──────┤─────── AccountSession
  │           │ 1:N
  │           └─────── AccountProxy (sticky assignment)
  │
  │ 1:N
  ├── Task ──────────── TaskLog
  │      └── Campaign ─ CampaignTask
  │
  │ 1:N
  ├── PostRecord
  ├── CommentRecord
  ├── DMRecord
  └── EngagementRecord

Persona ── 1:N ── Account

MediaAsset ── N:M ── Task (via TaskMedia)
```

---

## SQLAlchemy Base

```python
# socialmind/models/base.py
from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import DateTime, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

class Base(DeclarativeBase):
    pass

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

def uuid_pk() -> Mapped[str]:
    return mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
```

---

## Core Models

### Platform

```python
# socialmind/models/platform.py
from enum import StrEnum
from sqlalchemy import String, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

class PlatformSlug(StrEnum):
    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"
    REDDIT = "reddit"
    YOUTUBE = "youtube"
    FACEBOOK = "facebook"
    TWITTER = "twitter"
    THREADS = "threads"

class Platform(Base, TimestampMixin):
    __tablename__ = "platforms"

    id: Mapped[str] = uuid_pk()
    slug: Mapped[PlatformSlug] = mapped_column(String(32), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(64), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Capabilities flags
    supports_dm: Mapped[bool] = mapped_column(Boolean, default=True)
    supports_stories: Mapped[bool] = mapped_column(Boolean, default=False)
    supports_reels: Mapped[bool] = mapped_column(Boolean, default=False)
    supports_video: Mapped[bool] = mapped_column(Boolean, default=False)
    supports_polls: Mapped[bool] = mapped_column(Boolean, default=False)

    accounts: Mapped[list["Account"]] = relationship(back_populates="platform")
```

### Account

```python
# socialmind/models/account.py
from enum import StrEnum
from sqlalchemy import String, ForeignKey, Text, JSON, Boolean, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

class AccountStatus(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    SUSPENDED = "suspended"      # Banned or temp-blocked by platform
    CREDENTIAL_ERROR = "credential_error"
    WARMING_UP = "warming_up"   # New account in warmup phase

class Account(Base, TimestampMixin):
    __tablename__ = "accounts"

    id: Mapped[str] = uuid_pk()
    platform_id: Mapped[str] = mapped_column(ForeignKey("platforms.id"), nullable=False)
    persona_id: Mapped[str | None] = mapped_column(ForeignKey("personas.id"))

    # Identity
    username: Mapped[str] = mapped_column(String(128), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(128))
    email: Mapped[str | None] = mapped_column(String(256))
    phone: Mapped[str | None] = mapped_column(String(32))

    # Credentials (encrypted at rest — see SECURITY.md)
    credentials_encrypted: Mapped[bytes] = mapped_column(nullable=False)

    # Platform-specific metadata (e.g., user_id, pk, subreddit, channel_id)
    platform_user_id: Mapped[str | None] = mapped_column(String(256))
    platform_metadata: Mapped[dict] = mapped_column(JSON, default=dict)

    # Status
    status: Mapped[AccountStatus] = mapped_column(
        String(32), default=AccountStatus.ACTIVE
    )
    suspension_reason: Mapped[str | None] = mapped_column(Text)
    last_active_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Rate limiting & warmup
    daily_action_limit: Mapped[int] = mapped_column(Integer, default=100)
    warmup_phase: Mapped[bool] = mapped_column(Boolean, default=False)
    warmup_day: Mapped[int] = mapped_column(Integer, default=0)  # Day 0–30

    # Proxy assignment (sticky)
    proxy_id: Mapped[str | None] = mapped_column(ForeignKey("proxies.id"))

    # Relationships
    platform: Mapped["Platform"] = relationship(back_populates="accounts")
    persona: Mapped["Persona | None"] = relationship(back_populates="accounts")
    proxy: Mapped["Proxy | None"] = relationship(back_populates="accounts")
    sessions: Mapped[list["AccountSession"]] = relationship(back_populates="account")
    tasks: Mapped[list["Task"]] = relationship(back_populates="account")
```

### AccountSession

```python
class AccountSession(Base, TimestampMixin):
    """Persisted browser/API session state for an account."""
    __tablename__ = "account_sessions"

    id: Mapped[str] = uuid_pk()
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), nullable=False)

    # Browser session state
    cookies: Mapped[dict | None] = mapped_column(JSON)           # Playwright cookies
    local_storage: Mapped[dict | None] = mapped_column(JSON)     # Browser localStorage
    session_storage: Mapped[dict | None] = mapped_column(JSON)

    # API session tokens (encrypted)
    api_tokens_encrypted: Mapped[bytes | None] = mapped_column()

    # Session health
    is_valid: Mapped[bool] = mapped_column(Boolean, default=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    invalidation_reason: Mapped[str | None] = mapped_column(String(256))

    account: Mapped["Account"] = relationship(back_populates="sessions")
```

### Proxy

```python
class ProxyProtocol(StrEnum):
    SOCKS5 = "socks5"
    SOCKS4 = "socks4"
    HTTP = "http"
    HTTPS = "https"

class Proxy(Base, TimestampMixin):
    __tablename__ = "proxies"

    id: Mapped[str] = uuid_pk()
    protocol: Mapped[ProxyProtocol] = mapped_column(String(16), nullable=False)
    host: Mapped[str] = mapped_column(String(256), nullable=False)
    port: Mapped[int] = mapped_column(Integer, nullable=False)
    username: Mapped[str | None] = mapped_column(String(256))
    password_encrypted: Mapped[bytes | None] = mapped_column()

    # Health tracking
    is_healthy: Mapped[bool] = mapped_column(Boolean, default=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failure_count: Mapped[int] = mapped_column(Integer, default=0)
    country_code: Mapped[str | None] = mapped_column(String(8))
    provider: Mapped[str | None] = mapped_column(String(64))  # e.g. "brightdata", "oxylabs"

    accounts: Mapped[list["Account"]] = relationship(back_populates="proxy")
```

### Persona

```python
class Persona(Base, TimestampMixin):
    """AI persona configuration that controls how the LLM generates content."""
    __tablename__ = "personas"

    id: Mapped[str] = uuid_pk()
    name: Mapped[str] = mapped_column(String(128), nullable=False)

    # AI generation instructions
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    tone: Mapped[str] = mapped_column(String(64), default="casual")  # casual, professional, humorous
    niche: Mapped[str] = mapped_column(String(128))  # e.g., "fitness", "crypto", "cooking"
    language: Mapped[str] = mapped_column(String(16), default="en")
    vocab_level: Mapped[str] = mapped_column(String(32), default="conversational")
    emoji_usage: Mapped[str] = mapped_column(String(16), default="moderate")  # none, light, moderate, heavy
    hashtag_strategy: Mapped[str] = mapped_column(String(32), default="relevant")

    # Behavioral config
    reply_probability: Mapped[float] = mapped_column(default=0.7)   # 0.0–1.0
    like_probability: Mapped[float] = mapped_column(default=0.8)
    follow_back_probability: Mapped[float] = mapped_column(default=0.5)

    accounts: Mapped[list["Account"]] = relationship(back_populates="persona")
```

---

## Task & Scheduling Models

### Task

```python
class TaskType(StrEnum):
    POST = "post"
    COMMENT = "comment"
    REPLY_DM = "reply_dm"
    LIKE = "like"
    FOLLOW = "follow"
    UNFOLLOW = "unfollow"
    STORY = "story"
    REEL = "reel"
    RESEARCH = "research"
    ENGAGE_FEED = "engage_feed"  # Like + comment on feed items
    WARMUP = "warmup"            # Gradual activity during warmup

class TaskStatus(StrEnum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"
    SKIPPED = "skipped"   # Skipped due to account suspension etc.

class Task(Base, TimestampMixin):
    __tablename__ = "tasks"

    id: Mapped[str] = uuid_pk()
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    campaign_id: Mapped[str | None] = mapped_column(ForeignKey("campaigns.id"))

    task_type: Mapped[TaskType] = mapped_column(String(32), nullable=False)
    status: Mapped[TaskStatus] = mapped_column(String(32), default=TaskStatus.PENDING)

    # Scheduling
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Task configuration
    config: Mapped[dict] = mapped_column(JSON, default=dict)
    # Example config for POST task:
    # {
    #   "prompt": "Write about healthy breakfast ideas",
    #   "target_url": null,
    #   "target_id": null,
    #   "include_image": true,
    #   "image_prompt": "healthy colorful breakfast bowl",
    # }

    # Retry logic
    max_retries: Mapped[int] = mapped_column(Integer, default=3)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    celery_task_id: Mapped[str | None] = mapped_column(String(256))

    account: Mapped["Account"] = relationship(back_populates="tasks")
    logs: Mapped[list["TaskLog"]] = relationship(back_populates="task")
    media: Mapped[list["MediaAsset"]] = relationship(secondary="task_media")
```

### TaskLog

```python
class TaskLog(Base):
    __tablename__ = "task_logs"

    id: Mapped[str] = uuid_pk()
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id"), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    level: Mapped[str] = mapped_column(String(16))  # INFO, WARNING, ERROR
    message: Mapped[str] = mapped_column(Text)
    metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    # metadata example: {"adapter": "instagram_api", "http_status": 200, "latency_ms": 340}

    task: Mapped["Task"] = relationship(back_populates="logs")
```

### Campaign

```python
class Campaign(Base, TimestampMixin):
    """A named collection of tasks that share a goal."""
    __tablename__ = "campaigns"

    id: Mapped[str] = uuid_pk()
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Cron schedule for auto-generating tasks
    cron_expression: Mapped[str | None] = mapped_column(String(128))

    # Which accounts participate
    accounts: Mapped[list["Account"]] = relationship(secondary="campaign_accounts")
    tasks: Mapped[list["Task"]] = relationship(back_populates="campaign")
```

---

## Content & Media Models

### MediaAsset

```python
class MediaType(StrEnum):
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    GIF = "gif"

class MediaAsset(Base, TimestampMixin):
    __tablename__ = "media_assets"

    id: Mapped[str] = uuid_pk()
    media_type: Mapped[MediaType] = mapped_column(String(16), nullable=False)
    filename: Mapped[str] = mapped_column(String(512), nullable=False)

    # Storage
    storage_bucket: Mapped[str] = mapped_column(String(256), default="socialmind")
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)  # MinIO key
    file_size_bytes: Mapped[int | None] = mapped_column(Integer)
    mime_type: Mapped[str | None] = mapped_column(String(64))

    # Generation metadata
    generated_by: Mapped[str | None] = mapped_column(String(64))  # "dalle3", "stable_diffusion", "uploaded"
    generation_prompt: Mapped[str | None] = mapped_column(Text)

    # Dimensions
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    duration_seconds: Mapped[float | None] = mapped_column()
```

### PostRecord

```python
class PostRecord(Base, TimestampMixin):
    """Record of a successfully published post."""
    __tablename__ = "post_records"

    id: Mapped[str] = uuid_pk()
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id"), nullable=False)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), nullable=False)

    platform_post_id: Mapped[str] = mapped_column(String(256))  # Platform's own ID
    platform_url: Mapped[str | None] = mapped_column(String(512))
    content_text: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    # Engagement snapshot (updated by scheduled collection task)
    likes_count: Mapped[int] = mapped_column(Integer, default=0)
    comments_count: Mapped[int] = mapped_column(Integer, default=0)
    shares_count: Mapped[int] = mapped_column(Integer, default=0)
    views_count: Mapped[int] = mapped_column(Integer, default=0)
    engagement_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
```

---

## Association Tables

```python
# task_media — many-to-many between Task and MediaAsset
task_media = Table(
    "task_media",
    Base.metadata,
    Column("task_id", ForeignKey("tasks.id"), primary_key=True),
    Column("media_asset_id", ForeignKey("media_assets.id"), primary_key=True),
)

# campaign_accounts — many-to-many between Campaign and Account
campaign_accounts = Table(
    "campaign_accounts",
    Base.metadata,
    Column("campaign_id", ForeignKey("campaigns.id"), primary_key=True),
    Column("account_id", ForeignKey("accounts.id"), primary_key=True),
)
```

---

## Redis Key Schema

All Redis keys are namespaced by `sm:` prefix.

| Key Pattern | Type | TTL | Purpose |
|---|---|---|---|
| `sm:rl:{account_id}:{action}:{date}` | String (int) | 25h | Daily action rate limit counter |
| `sm:session:{account_id}` | Hash | 30d | Cached session state (fast access) |
| `sm:proxy:pool` | Sorted Set | — | Proxy pool sorted by failure score |
| `sm:proxy:lock:{proxy_id}` | String | 30s | Lock during proxy health check |
| `sm:task:running:{account_id}` | String | 10m | Lock: one task per account at a time |
| `sm:trend:{platform}:{niche}:{date}` | String (JSON) | 6h | Cached trending content |
| `sm:celery:results:{task_id}` | String | 24h | Celery task result store |

---

## Migrations

Alembic is used for all schema migrations.

```bash
# Generate a new migration
alembic revision --autogenerate -m "add persona emoji_usage field"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1
```

Migration files live in `migrations/versions/`. All migrations are idempotent and support rollback.
