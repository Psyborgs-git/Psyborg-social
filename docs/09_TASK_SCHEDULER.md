# Task Scheduler

SocialMind uses Celery for distributed task execution and Celery Beat for time-based scheduling. This document covers task design, the schedule, workflow chains, and monitoring.

---

## Architecture

```
Celery Beat (scheduler)
    │  Reads schedule from DB + celeryconfig.py
    │  Dispatches tasks at the right time
    ▼
Redis (message broker)
    │  Task queue
    ▼
Celery Workers (executors)
    │  Pull tasks from queue
    │  Execute automation logic
    │  Write results to PostgreSQL
    ▼
Flower (monitoring UI, port 5555)
```

---

## Celery Configuration

```python
# socialmind/scheduler/celery_app.py
from celery import Celery
from kombu import Exchange, Queue

celery_app = Celery("socialmind")

celery_app.conf.update(
    # Broker & backend
    broker_url=settings.REDIS_URL,
    result_backend=settings.REDIS_URL,
    result_expires=86400,  # 24 hours

    # Serialization
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],

    # Task routing — different queues for different priority levels
    task_routes={
        "socialmind.scheduler.tasks.execute_post":       {"queue": "high"},
        "socialmind.scheduler.tasks.execute_dm_reply":   {"queue": "high"},
        "socialmind.scheduler.tasks.engage_feed":        {"queue": "normal"},
        "socialmind.scheduler.tasks.research_trends":    {"queue": "low"},
        "socialmind.scheduler.tasks.health_check_proxy": {"queue": "low"},
        "socialmind.scheduler.tasks.collect_analytics":  {"queue": "low"},
    },

    # Queue definitions
    task_queues=(
        Queue("high",   Exchange("high"),   routing_key="high",   max_priority=10),
        Queue("normal", Exchange("normal"), routing_key="normal", max_priority=5),
        Queue("low",    Exchange("low"),    routing_key="low",    max_priority=1),
    ),
    task_default_queue="normal",

    # Concurrency & execution
    worker_concurrency=4,               # 4 tasks per worker container
    worker_prefetch_multiplier=1,       # Don't prefetch — one task at a time per slot
    task_acks_late=True,                # Ack only after completion (safer for long tasks)
    task_reject_on_worker_lost=True,    # Re-queue if worker crashes

    # Timeouts
    task_soft_time_limit=300,   # 5 min soft limit — raise SoftTimeLimitExceeded
    task_time_limit=360,        # 6 min hard limit — SIGKILL

    # Retry behavior
    task_max_retries=3,
    task_default_retry_delay=60,  # 1 minute between retries

    # Beat schedule (periodic tasks — supplemented by DB-driven dynamic schedule)
    beat_scheduler="celery.beat:PersistentScheduler",
    beat_schedule_filename="/data/celerybeat-schedule",
)
```

---

## Task Definitions

### Core Automation Tasks

```python
# socialmind/scheduler/tasks.py
from celery import shared_task
from celery.utils.log import get_task_logger
from socialmind.scheduler.celery_app import celery_app

logger = get_task_logger(__name__)

@celery_app.task(
    bind=True,
    name="socialmind.scheduler.tasks.execute_post",
    max_retries=3,
    default_retry_delay=120,
)
async def execute_post(self, task_id: str):
    """Execute a post task for one account."""
    async with get_db_session() as db:
        task = await db.get(Task, task_id)
        if not task or task.status == TaskStatus.SKIPPED:
            return

        account = await db.get(Account, task.account_id)
        if account.status != AccountStatus.ACTIVE:
            task.status = TaskStatus.SKIPPED
            task.logs.append(TaskLog(level="WARNING", message=f"Account {account.status}, skipping"))
            await db.commit()
            return

        # Rate limit check
        limiter = AccountRateLimiter(get_redis())
        allowed = await limiter.check_and_increment(account.id, account.platform.slug, "posts")
        if not allowed:
            logger.warning("Rate limit hit for %s, requeueing in 2h", account.username)
            raise self.retry(countdown=7200)

        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now(UTC)
        await db.commit()

        try:
            # Get proxy and session
            proxy_manager = ProxyPoolManager(get_redis(), db)
            proxy = await proxy_manager.get_proxy_for_account(account)
            session = await get_or_create_session(account, db)

            # Get adapter
            adapter = get_adapter(account, session, proxy)
            await adapter.authenticate()

            # Run AI pipeline + post
            pipeline = PostCampaignPipeline()
            result = await pipeline.run_post(account, task, adapter)

            # Persist result
            if result.success:
                task.status = TaskStatus.SUCCESS
                db.add(PostRecord(
                    task_id=task.id,
                    account_id=account.id,
                    platform_post_id=result.platform_post_id,
                    platform_url=result.platform_url,
                    published_at=datetime.now(UTC),
                ))
            else:
                task.status = TaskStatus.FAILED
                task.logs.append(TaskLog(level="ERROR", message=result.error or "Unknown error"))

        except SoftTimeLimitExceeded:
            task.status = TaskStatus.FAILED
            task.logs.append(TaskLog(level="ERROR", message="Task timed out"))
        except DetectionError as e:
            task.status = TaskStatus.FAILED
            task.logs.append(TaskLog(level="WARNING", message=f"Detection: {e}"))
            await handle_detection_event(account, e, db)
        except Exception as e:
            task.status = TaskStatus.RETRYING
            task.retry_count += 1
            logger.exception("Task %s failed: %s", task_id, e)
            raise self.retry(exc=e)
        finally:
            task.completed_at = datetime.now(UTC)
            await db.commit()
            # Persist browser session
            await BrowserContextFactory.save_state(account)


@celery_app.task(name="socialmind.scheduler.tasks.execute_dm_reply")
async def execute_dm_reply(task_id: str):
    """Check and respond to DMs for one account."""
    async with get_db_session() as db:
        task = await db.get(Task, task_id)
        account = await db.get(Account, task.account_id)
        # ... similar setup ...
        pipeline = PostCampaignPipeline()
        results = await pipeline.run_dm_responses(account, adapter)
        task.status = TaskStatus.SUCCESS
        await db.commit()


@celery_app.task(name="socialmind.scheduler.tasks.engage_feed")
async def engage_feed(task_id: str):
    """Like and comment on feed items for one account."""
    async with get_db_session() as db:
        task = await db.get(Task, task_id)
        account = await db.get(Account, task.account_id)
        duration_minutes = task.config.get("duration_minutes", 10)
        actions = task.config.get("actions", ["like", "comment"])
        # ... run FeedEngager pipeline for duration_minutes ...


@celery_app.task(name="socialmind.scheduler.tasks.research_trends")
async def research_trends(platform: str, niche: str):
    """Fetch and cache trending content for a platform/niche combo."""
    # This task is idempotent — safe to run multiple times
    # Result cached in Redis for 6 hours
    async with get_db_session() as db:
        # Use any healthy account on this platform for access
        account = await get_any_healthy_account(platform, db)
        if not account:
            return

        adapter = get_adapter(account, ...)
        trends = await adapter.get_trending(niche, limit=30)

        cache_key = f"sm:trend:{platform}:{niche}:{day_bucket()}"
        await get_redis().setex(cache_key, 21600, json.dumps([t.__dict__ for t in trends]))


@celery_app.task(name="socialmind.scheduler.tasks.health_check_proxy")
async def health_check_proxy():
    """Validate all proxies in the pool."""
    async with get_db_session() as db:
        manager = ProxyPoolManager(get_redis(), db)
        await manager.health_check_all()


@celery_app.task(name="socialmind.scheduler.tasks.collect_analytics")
async def collect_analytics():
    """Refresh engagement counts on recent posts."""
    async with get_db_session() as db:
        recent_posts = await db.execute(
            select(PostRecord)
            .where(PostRecord.published_at > datetime.now(UTC) - timedelta(days=7))
            .where(PostRecord.engagement_updated_at < datetime.now(UTC) - timedelta(hours=4))
        )
        for post in recent_posts.scalars():
            # Fetch updated engagement via adapter
            # Update post.likes_count, etc.
            pass


@celery_app.task(name="socialmind.scheduler.tasks.run_warmup")
async def run_warmup(account_id: str):
    """Execute one day's warmup activities for a new account."""
    async with get_db_session() as db:
        account = await db.get(Account, account_id)
        day = account.warmup_day
        schedule = WARMUP_SCHEDULE.get(day, WARMUP_SCHEDULE[30])

        adapter = get_adapter(account, ...)
        await adapter.authenticate()

        # Execute warmup actions
        for _ in range(schedule["likes"]):
            feed = await adapter.get_feed(limit=5)
            for item in feed[:schedule["likes"]]:
                await adapter.like(item.platform_id)
                await TimingEngine.delay("like")

        account.warmup_day += 1
        if account.warmup_day >= 30:
            account.warmup_phase = False
            account.status = AccountStatus.ACTIVE
        await db.commit()
```

---

## Static Beat Schedule

These tasks run on a fixed cron regardless of user configuration:

```python
# socialmind/scheduler/beat.py
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    # Proxy health check — every 30 minutes
    "health-check-proxies": {
        "task": "socialmind.scheduler.tasks.health_check_proxy",
        "schedule": crontab(minute="*/30"),
    },

    # Trend research — every 6 hours, all platforms
    "research-trends-instagram-fitness": {
        "task": "socialmind.scheduler.tasks.research_trends",
        "schedule": crontab(hour="*/6", minute=0),
        "args": ("instagram", "fitness"),
    },

    # Analytics collection — every 4 hours
    "collect-analytics": {
        "task": "socialmind.scheduler.tasks.collect_analytics",
        "schedule": crontab(hour="*/4", minute=15),
    },

    # Warmup tasks — once per day for each account in warmup
    "run-warmup-accounts": {
        "task": "socialmind.scheduler.tasks.dispatch_warmup_tasks",
        "schedule": crontab(hour=10, minute=0),  # 10am daily
    },

    # DM check — every 15 minutes for all active accounts
    "check-dms-all-accounts": {
        "task": "socialmind.scheduler.tasks.dispatch_dm_tasks",
        "schedule": crontab(minute="*/15"),
    },
}
```

---

## Dynamic Schedule (DB-Driven)

User-configured campaigns generate tasks dynamically. A dispatcher task reads active campaigns and enqueues tasks:

```python
@celery_app.task(name="socialmind.scheduler.tasks.dispatch_campaign_tasks")
async def dispatch_campaign_tasks():
    """
    Runs every minute. Checks which campaigns are due and creates tasks.
    Uses croniter to evaluate cron expressions against current time.
    """
    from croniter import croniter
    now = datetime.now(UTC)

    async with get_db_session() as db:
        campaigns = await db.execute(
            select(Campaign).where(Campaign.is_active == True)
        )
        for campaign in campaigns.scalars():
            if not campaign.cron_expression:
                continue
            cron = croniter(campaign.cron_expression, now - timedelta(minutes=1))
            next_run = cron.get_next(datetime)
            if next_run <= now:
                # This campaign is due — create tasks for all its accounts
                for account in campaign.accounts:
                    if account.status != AccountStatus.ACTIVE:
                        continue
                    task = Task(
                        account_id=account.id,
                        campaign_id=campaign.id,
                        task_type=TaskType(campaign.task_type),
                        status=TaskStatus.QUEUED,
                        config=campaign.config,
                        scheduled_at=now,
                    )
                    db.add(task)
                    await db.flush()
                    # Dispatch to Celery
                    celery_task_fn = TASK_TYPE_TO_CELERY[campaign.task_type]
                    celery_result = celery_task_fn.delay(task.id)
                    task.celery_task_id = celery_result.id
        await db.commit()
```

---

## Task Isolation (One Task Per Account)

To prevent race conditions, only one task runs per account at a time:

```python
async def acquire_account_lock(account_id: str, redis: Redis) -> bool:
    """Returns True if lock acquired, False if account is already busy."""
    key = f"sm:task:running:{account_id}"
    result = await redis.set(key, "1", nx=True, ex=600)  # 10 min TTL
    return result is not None

async def release_account_lock(account_id: str, redis: Redis):
    await redis.delete(f"sm:task:running:{account_id}")
```

---

## Monitoring with Flower

Flower runs at port 5555 and provides:
- Real-time task queue visualization
- Worker status and CPU/memory
- Task success/failure rates
- Ability to manually revoke or retry tasks

Access: `http://localhost:5555`

For production, secure Flower behind basic auth:
```yaml
# docker-compose.yml
flower:
  command: celery -A socialmind.scheduler.celery_app flower
    --basic_auth=admin:${FLOWER_PASSWORD}
    --url_prefix=flower
```
