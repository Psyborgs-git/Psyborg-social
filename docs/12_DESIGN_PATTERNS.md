# Design Patterns

Documented design patterns used throughout the SocialMind codebase. Understanding these patterns is essential for contributing and extending the system.

---

## 1. Adapter Pattern

**Where**: `socialmind/adapters/`

**Problem**: Seven platforms with completely different APIs, authentication flows, and capabilities need to be controlled through a single unified interface.

**Solution**: Each platform implements `BasePlatformAdapter`. All callers (Celery tasks, MCP tools) program against the base class only.

```python
# All callers look like this — no platform-specific code
async def execute_any_post(task: Task, account: Account):
    adapter = get_adapter(account, session, proxy)  # Returns correct subclass
    await adapter.authenticate()
    result = await adapter.post(content)  # Same call regardless of platform
```

**Key rule**: Platform-specific logic NEVER leaks above the adapter layer. If a Celery task contains an `if platform == "instagram":` block, that's an architecture violation.

---

## 2. Strategy Pattern

**Where**: `socialmind/adapters/*/adapter.py`, `socialmind/content/image.py`

**Problem**: Within a single platform adapter, the method of execution (private API vs. browser) needs to switch at runtime based on conditions.

**Solution**: Each adapter composes two strategy objects — the private API client and the browser automation client — and selects between them.

```python
class InstagramAdapter(BasePlatformAdapter):
    def __init__(self):
        self._strategies = {
            "api": InstagrapiStrategy(),
            "browser": PlaywrightStrategy(),
        }

    async def post(self, content: PostContent) -> PostResult:
        strategy = self._select_strategy("post")
        return await strategy.post(content)

    def _select_strategy(self, action: str) -> BaseStrategy:
        if self._api_healthy and action in self._api_supported_actions:
            return self._strategies["api"]
        return self._strategies["browser"]
```

The same pattern applies to image generation — `DalleImageGenerator` and `StableDiffusionGenerator` implement `ImageGenerator`, and `get_image_generator()` selects at runtime.

---

## 3. Repository Pattern

**Where**: `socialmind/models/`, `socialmind/api/dependencies.py`

**Problem**: Database access scattered through business logic makes testing and refactoring hard.

**Solution**: Repositories encapsulate all DB access for each entity. Service functions call repositories, not SQLAlchemy directly.

```python
# socialmind/repositories/account_repository.py
class AccountRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_id(self, account_id: str) -> Account | None:
        return await self._session.get(Account, account_id)

    async def get_active_by_platform(self, platform_slug: str) -> list[Account]:
        result = await self._session.execute(
            select(Account)
            .join(Platform)
            .where(Platform.slug == platform_slug)
            .where(Account.status == AccountStatus.ACTIVE)
        )
        return list(result.scalars())

    async def update_status(self, account_id: str, status: AccountStatus) -> Account:
        account = await self.get_by_id(account_id)
        account.status = status
        await self._session.commit()
        return account

# Usage in service layer
class AccountService:
    def __init__(self, repo: AccountRepository):
        self._repo = repo

    async def pause(self, account_id: str, reason: str) -> Account:
        account = await self._repo.update_status(account_id, AccountStatus.PAUSED)
        # Revoke pending Celery tasks for this account
        await revoke_account_tasks(account_id)
        return account
```

---

## 4. Circuit Breaker Pattern

**Where**: `socialmind/adapters/base.py`, `socialmind/stealth/`

**Problem**: When a platform starts detecting us, we must stop immediately — not retry and get the account banned.

**Solution**: A circuit breaker tracks failure rates per account. After N failures, the circuit opens and all calls fail fast for a cool-down period.

```python
# socialmind/stealth/circuit_breaker.py
class CircuitBreaker:
    """
    States:
      CLOSED  — Normal operation, requests pass through
      OPEN    — Failure threshold exceeded, requests fail fast
      HALF    — Cool-down expired, allowing one test request through
    """
    def __init__(self, account_id: str, redis: Redis):
        self._key = f"sm:circuit:{account_id}"
        self._redis = redis
        self.failure_threshold = 3
        self.cooldown_seconds = 3600  # 1 hour

    async def call(self, fn: Callable, *args, **kwargs):
        state = await self._get_state()
        if state == "OPEN":
            raise CircuitOpenError(f"Circuit open for account, cooling down")
        try:
            result = await fn(*args, **kwargs)
            await self._on_success()
            return result
        except (DetectionError, RateLimitError) as e:
            await self._on_failure()
            raise

    async def _on_failure(self):
        failures = await self._redis.incr(f"{self._key}:failures")
        await self._redis.expire(f"{self._key}:failures", 3600)
        if failures >= self.failure_threshold:
            await self._redis.set(f"{self._key}:state", "OPEN", ex=self.cooldown_seconds)

    async def _on_success(self):
        await self._redis.delete(f"{self._key}:failures")
        await self._redis.delete(f"{self._key}:state")
```

---

## 5. Factory Pattern

**Where**: `socialmind/adapters/registry.py`, `socialmind/content/image.py`, `socialmind/stealth/session.py`

**Problem**: Creating the right type of object (correct adapter, generator, browser context) requires conditional logic that shouldn't live in calling code.

**Solution**: Factory functions and registries centralize object creation.

```python
# Adapter factory
def get_adapter(account: Account, session: AccountSession, proxy: Proxy | None) -> BasePlatformAdapter:
    AdapterClass = ADAPTER_REGISTRY[account.platform.slug]
    return AdapterClass(account=account, session=session, proxy=proxy)

# Image generator factory
def get_image_generator() -> ImageGenerator:
    return {
        "dalle": DalleImageGenerator,
        "stable_diffusion": StableDiffusionGenerator,
    }[settings.IMAGE_PROVIDER]()

# Browser context factory
async def get_browser_context(account: Account) -> BrowserContext:
    return await BrowserContextFactory.get_or_create(account, account.proxy)
```

---

## 6. Observer Pattern (Event System)

**Where**: `socialmind/events.py`, detection handling

**Problem**: When significant events occur (account banned, proxy failed, task failed), multiple subsystems need to react — the dashboard should update, the account should be paused, an alert should fire.

**Solution**: A lightweight async event bus. Publishers emit events; subscribers react independently.

```python
# socialmind/events.py
from typing import Callable, Any
import asyncio

class EventBus:
    _subscribers: dict[str, list[Callable]] = {}

    @classmethod
    def subscribe(cls, event: str, handler: Callable):
        cls._subscribers.setdefault(event, []).append(handler)

    @classmethod
    async def emit(cls, event: str, **kwargs):
        for handler in cls._subscribers.get(event, []):
            asyncio.create_task(handler(**kwargs))

# Events
ACCOUNT_SUSPENDED = "account.suspended"
PROXY_FAILED = "proxy.failed"
TASK_COMPLETED = "task.completed"
DETECTION_TRIGGERED = "detection.triggered"

# Subscriptions (registered at startup)
EventBus.subscribe(ACCOUNT_SUSPENDED, notify_dashboard)
EventBus.subscribe(ACCOUNT_SUSPENDED, pause_account_tasks)
EventBus.subscribe(PROXY_FAILED, reassign_proxy)
EventBus.subscribe(TASK_COMPLETED, push_websocket_update)
EventBus.subscribe(DETECTION_TRIGGERED, open_circuit_breaker)

# Emitting
await EventBus.emit(ACCOUNT_SUSPENDED, account_id=account.id, reason="ban_detected")
```

---

## 7. Decorator Pattern

**Where**: Throughout, especially in stealth and rate limiting

**Problem**: Cross-cutting concerns (rate limiting, delays, logging, circuit breaking) would pollute business logic if written inline.

**Solution**: Decorators wrap adapter methods cleanly.

```python
def rate_limited(action: str):
    """Decorator that enforces per-account rate limits."""
    def decorator(fn):
        @functools.wraps(fn)
        async def wrapper(self, *args, **kwargs):
            limiter = AccountRateLimiter(get_redis())
            allowed = await limiter.check_and_increment(
                self.account.id, self.platform_slug, action
            )
            if not allowed:
                raise RateLimitError(f"Rate limit exceeded for {action}")
            return await fn(self, *args, **kwargs)
        return wrapper
    return decorator

def with_human_delay(action: str):
    """Decorator that applies a human-like delay before the action."""
    def decorator(fn):
        @functools.wraps(fn)
        async def wrapper(self, *args, **kwargs):
            await TimingEngine.delay(action)
            return await fn(self, *args, **kwargs)
        return wrapper
    return decorator

# Usage in adapters
class InstagramAdapter(BasePlatformAdapter):

    @rate_limited("likes")
    @with_human_delay("like")
    async def like(self, target_id: str) -> bool:
        return self._api.media_like(target_id)

    @rate_limited("posts")
    @with_human_delay("post")
    async def post(self, content: PostContent) -> PostResult:
        ...
```

---

## 8. Command Pattern

**Where**: `socialmind/scheduler/tasks.py`, MCP tool handlers

**Problem**: Automation actions need to be serializable (to pass through Redis), retryable, loggable, and undoable in some cases.

**Solution**: Each automation action is a Command — a data object describing what to do, not the execution itself.

```python
@dataclass
class PostCommand:
    account_id: str
    content: PostContent
    task_id: str

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "PostCommand":
        return cls(**d)

# The command is serialized into the Celery task args
execute_post.delay(PostCommand(
    account_id=account.id,
    content=post_content,
    task_id=task.id,
).to_dict())
```

---

## 9. Facade Pattern

**Where**: `socialmind/services/`, MCP tool handlers

**Problem**: The UI and MCP server shouldn't need to understand the internals of adapters, DSPy pipelines, and the task queue simultaneously to accomplish a simple action like "post to Instagram".

**Solution**: A `SocialMindService` facade provides high-level methods that internally coordinate all subsystems.

```python
# socialmind/services/social_service.py
class SocialMindService:
    """Facade that coordinates adapters, AI pipelines, and task queue."""

    async def create_post_now(self, account_id: str, prompt: str, include_image: bool) -> PostResult:
        """High-level: generate content + post immediately."""
        account = await self._account_repo.get_by_id(account_id)
        trends = await self._get_cached_trends(account)
        content = await generate_full_post_content(account, prompt, trends, include_image)
        adapter = get_adapter(account, ...)
        return await adapter.post(content)

    async def schedule_campaign(self, campaign_config: dict) -> Campaign:
        """High-level: create campaign + all its scheduled tasks."""
        campaign = await self._campaign_repo.create(campaign_config)
        await self._register_celery_beat_entry(campaign)
        return campaign
```

---

## 10. Idempotency Pattern

**Where**: All Celery tasks, all DB write operations

**Problem**: Celery tasks can be retried. Network failures can cause duplicate executions. This cannot result in double-posts or double-follows.

**Solution**: Every task checks for a prior successful execution before running. All DB writes use upserts or existence checks.

```python
@celery_app.task
async def execute_post(task_id: str):
    async with get_db_session() as db:
        task = await db.get(Task, task_id)

        # Idempotency check: already completed?
        if task.status == TaskStatus.SUCCESS:
            logger.info("Task %s already succeeded, skipping", task_id)
            return

        # Idempotency check: was a post already created for this task?
        existing_post = await db.execute(
            select(PostRecord).where(PostRecord.task_id == task_id)
        )
        if existing_post.scalar():
            task.status = TaskStatus.SUCCESS
            await db.commit()
            return

        # ... proceed with execution
```

---

## Anti-Patterns to Avoid

| Anti-Pattern | Problem | Correct Approach |
|---|---|---|
| `if platform == "instagram":` outside adapter | Platform logic leaks upward | Keep it in the adapter |
| Direct SQLAlchemy queries in Celery tasks | Bypasses repository layer | Use repositories |
| `time.sleep()` in async code | Blocks the event loop | Use `await asyncio.sleep()` |
| Storing credentials as plain text | Security breach | Always encrypt with Fernet |
| One Playwright browser per task | Memory explosion (browsers ~300MB each) | Shared browser, per-account contexts |
| Hardcoded rate limits | Inflexible, hard to tune | Read from DB/config per account |
| Catching bare `Exception` without re-raising | Silent failures | Log + re-raise or handle specifically |
