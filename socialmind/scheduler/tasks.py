from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from datetime import UTC, datetime, timedelta
from typing import Any

from celery.exceptions import SoftTimeLimitExceeded
from celery.utils.log import get_task_logger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from socialmind.config.settings import settings
from socialmind.models.account import Account, AccountStatus
from socialmind.models.task import Task, TaskLog, TaskStatus, TaskType
from socialmind.scheduler.celery_app import celery_app

logger = get_task_logger(__name__)

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_engine = create_async_engine(settings.DATABASE_URL, echo=False)
_SessionFactory = async_sessionmaker(_engine, expire_on_commit=False)


@asynccontextmanager
async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    async with _SessionFactory() as session:
        yield session


def get_redis():  # type: ignore[return]
    import redis.asyncio as aioredis

    return aioredis.from_url(settings.REDIS_URL, decode_responses=True)


async def acquire_account_lock(account_id: str, redis: Any) -> bool:
    """Return True if lock acquired; False if account is already busy."""
    key = f"sm:task:running:{account_id}"
    result = await redis.set(key, "1", nx=True, ex=600)
    return result is not None


async def release_account_lock(account_id: str, redis: Any) -> None:
    await redis.delete(f"sm:task:running:{account_id}")


def _day_bucket() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d")


async def _get_adapter(account: Account, db: AsyncSession) -> Any:
    from socialmind.adapters.registry import get_adapter
    from socialmind.stealth.proxy import ProxyPoolManager

    redis_client = get_redis()
    proxy_manager = ProxyPoolManager(redis_client, db)
    proxy = await proxy_manager.get_proxy_for_account(account)

    session = None
    if account.sessions:
        session = account.sessions[0]

    return get_adapter(account=account, session=session, proxy=proxy)


async def _log(db: AsyncSession, task: Task, level: str, message: str) -> None:
    db.add(TaskLog(task_id=task.id, level=level, message=message))
    await db.flush()


# ---------------------------------------------------------------------------
# Tasks
# ---------------------------------------------------------------------------


@celery_app.task(
    bind=True,
    name="socialmind.scheduler.tasks.execute_post",
    max_retries=3,
    default_retry_delay=120,
)
def execute_post(self: Any, task_id: str) -> dict[str, Any]:
    """Execute a post task for one account."""
    return asyncio.run(_execute_post_async(self, task_id))


async def _execute_post_async(celery_self: Any, task_id: str) -> dict[str, Any]:
    from socialmind.ai.pipelines.post_pipeline import PostCampaignPipeline
    from socialmind.models.media import PostRecord
    from socialmind.stealth.rate_limiter import AccountRateLimiter

    redis_client = get_redis()

    async with get_db_session() as db:
        task: Task | None = await db.get(Task, task_id)
        if task is None:
            logger.error("Task %s not found", task_id)
            return {"status": "not_found"}

        if task.status == TaskStatus.SUCCESS:
            logger.info("Task %s already succeeded, skipping", task_id)
            return {"status": "skipped"}

        existing = await db.execute(
            select(PostRecord).where(PostRecord.task_id == task_id)
        )
        if existing.scalar():
            task.status = TaskStatus.SUCCESS
            await db.commit()
            return {"status": "skipped"}

        account: Account | None = await db.get(Account, task.account_id)
        if account is None:
            return {"status": "account_not_found"}

        if account.status != AccountStatus.ACTIVE:
            task.status = TaskStatus.SKIPPED
            await _log(db, task, "WARNING", f"Account {account.status}, skipping")
            await db.commit()
            return {"status": "skipped"}

        if not await acquire_account_lock(account.id, redis_client):
            logger.warning("Account %s busy, requeueing", account.username)
            raise celery_self.retry(countdown=60)

        limiter = AccountRateLimiter(redis_client)
        allowed = await limiter.check_and_increment(
            account.id, account.platform.slug, "posts"
        )
        if not allowed:
            await release_account_lock(account.id, redis_client)
            logger.warning("Rate limit hit for %s, requeueing in 2h", account.username)
            raise celery_self.retry(countdown=7200)

        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now(UTC)
        await db.commit()

        try:
            adapter = await _get_adapter(account, db)
            await adapter.authenticate()

            pipeline = PostCampaignPipeline()
            result = await pipeline.run_post(account, task, adapter)

            if result.success:
                task.status = TaskStatus.SUCCESS
                db.add(
                    PostRecord(
                        task_id=task.id,
                        account_id=account.id,
                        platform_post_id=result.platform_post_id or "",
                        platform_url=result.platform_url,
                        published_at=datetime.now(UTC),
                    )
                )
            else:
                task.status = TaskStatus.FAILED
                await _log(db, task, "ERROR", result.error or "Unknown error")

        except SoftTimeLimitExceeded:
            task.status = TaskStatus.FAILED
            await _log(db, task, "ERROR", "Task timed out")
        except Exception as exc:
            task.status = TaskStatus.RETRYING
            task.retry_count += 1
            logger.exception("Task %s failed: %s", task_id, exc)
            await db.commit()
            raise celery_self.retry(exc=exc)
        finally:
            task.completed_at = datetime.now(UTC)
            await db.commit()
            await release_account_lock(account.id, redis_client)
            await redis_client.aclose()

    return {"status": task.status}


@celery_app.task(
    bind=True,
    name="socialmind.scheduler.tasks.execute_dm_reply",
    max_retries=3,
    default_retry_delay=60,
)
def execute_dm_reply(self: Any, task_id: str) -> dict[str, Any]:
    """Check and respond to DMs for one account."""
    return asyncio.run(_execute_dm_reply_async(self, task_id))


async def _execute_dm_reply_async(celery_self: Any, task_id: str) -> dict[str, Any]:
    from socialmind.ai.pipelines.post_pipeline import PostCampaignPipeline

    redis_client = get_redis()

    async with get_db_session() as db:
        task: Task | None = await db.get(Task, task_id)
        if task is None:
            return {"status": "not_found"}

        if task.status == TaskStatus.SUCCESS:
            return {"status": "skipped"}

        account: Account | None = await db.get(Account, task.account_id)
        if account is None:
            return {"status": "account_not_found"}

        if account.status != AccountStatus.ACTIVE:
            task.status = TaskStatus.SKIPPED
            await db.commit()
            return {"status": "skipped"}

        if not await acquire_account_lock(account.id, redis_client):
            raise celery_self.retry(countdown=60)

        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now(UTC)
        await db.commit()

        try:
            adapter = await _get_adapter(account, db)
            await adapter.authenticate()

            pipeline = PostCampaignPipeline()
            results = await pipeline.run_dm_responses(account, adapter)

            task.status = TaskStatus.SUCCESS
            await _log(db, task, "INFO", f"Replied to {len(results)} DMs")

        except SoftTimeLimitExceeded:
            task.status = TaskStatus.FAILED
            await _log(db, task, "ERROR", "Task timed out")
        except Exception as exc:
            task.status = TaskStatus.RETRYING
            task.retry_count += 1
            logger.exception("DM task %s failed: %s", task_id, exc)
            await db.commit()
            raise celery_self.retry(exc=exc)
        finally:
            task.completed_at = datetime.now(UTC)
            await db.commit()
            await release_account_lock(account.id, redis_client)
            await redis_client.aclose()

    return {"status": task.status}


@celery_app.task(
    bind=True,
    name="socialmind.scheduler.tasks.engage_feed",
    max_retries=3,
    default_retry_delay=60,
)
def engage_feed(self: Any, task_id: str) -> dict[str, Any]:
    """Like and comment on feed items for one account."""
    return asyncio.run(_engage_feed_async(self, task_id))


async def _engage_feed_async(celery_self: Any, task_id: str) -> dict[str, Any]:
    import random

    from socialmind.ai.modules.content import FeedEngager

    redis_client = get_redis()

    async with get_db_session() as db:
        task: Task | None = await db.get(Task, task_id)
        if task is None:
            return {"status": "not_found"}

        if task.status == TaskStatus.SUCCESS:
            return {"status": "skipped"}

        account: Account | None = await db.get(Account, task.account_id)
        if account is None:
            return {"status": "account_not_found"}

        if account.status != AccountStatus.ACTIVE:
            task.status = TaskStatus.SKIPPED
            await db.commit()
            return {"status": "skipped"}

        if not await acquire_account_lock(account.id, redis_client):
            raise celery_self.retry(countdown=60)

        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now(UTC)
        await db.commit()

        actions_taken = 0
        try:
            adapter = await _get_adapter(account, db)
            await adapter.authenticate()

            duration_minutes = task.config.get("duration_minutes", 10)
            actions = task.config.get("actions", ["like", "comment"])
            niche = account.persona.niche if account.persona else "general"
            engager = FeedEngager()

            end_time = datetime.now(UTC) + timedelta(minutes=duration_minutes)

            while datetime.now(UTC) < end_time:
                feed = await adapter.get_feed(limit=10)
                for item in feed:
                    if datetime.now(UTC) >= end_time:
                        break
                    plan = engager(feed_item=item, persona=account.persona, niche=niche)

                    if "like" in actions and plan.should_like:
                        await adapter.like(item.platform_id)
                        actions_taken += 1
                        await asyncio.sleep(random.uniform(2, 8))

                    if "comment" in actions and plan.should_comment and plan.comment_text:
                        await adapter.comment(item.platform_id, plan.comment_text)
                        actions_taken += 1
                        await asyncio.sleep(random.uniform(10, 30))

                await asyncio.sleep(random.uniform(30, 90))

            task.status = TaskStatus.SUCCESS
            await _log(db, task, "INFO", f"Took {actions_taken} feed actions")

        except SoftTimeLimitExceeded:
            task.status = TaskStatus.FAILED
            await _log(db, task, "ERROR", "Task timed out")
        except Exception as exc:
            task.status = TaskStatus.RETRYING
            task.retry_count += 1
            logger.exception("Feed task %s failed: %s", task_id, exc)
            await db.commit()
            raise celery_self.retry(exc=exc)
        finally:
            task.completed_at = datetime.now(UTC)
            await db.commit()
            await release_account_lock(account.id, redis_client)
            await redis_client.aclose()

    return {"status": task.status, "actions_taken": actions_taken}


@celery_app.task(name="socialmind.scheduler.tasks.research_trends")
def research_trends(platform: str, niche: str) -> dict[str, Any]:
    """Fetch and cache trending content for a platform/niche combo."""
    return asyncio.run(_research_trends_async(platform, niche))


async def _research_trends_async(platform: str, niche: str) -> dict[str, Any]:
    redis_client = get_redis()

    cache_key = f"sm:trend:{platform}:{niche}:{_day_bucket()}"
    cached = await redis_client.get(cache_key)
    if cached:
        await redis_client.aclose()
        return {"status": "cached"}

    async with get_db_session() as db:
        result = await db.execute(
            select(Account)
            .join(Account.platform)
            .where(Account.status == AccountStatus.ACTIVE)
            .limit(1)
        )
        account = result.scalar()
        if account is None:
            await redis_client.aclose()
            return {"status": "no_healthy_account"}

        try:
            adapter = await _get_adapter(account, db)
            await adapter.authenticate()
            trends = await adapter.get_trending(niche, limit=30)
            serialized = json.dumps(
                [
                    {
                        "title": t.title,
                        "url": t.url,
                        "hashtags": t.hashtags,
                        "score": t.engagement_score,
                    }
                    for t in trends
                ]
            )
            await redis_client.setex(cache_key, 21600, serialized)
        except Exception as exc:
            logger.exception("research_trends failed for %s/%s: %s", platform, niche, exc)
            await redis_client.aclose()
            return {"status": "failed", "error": str(exc)}

    await redis_client.aclose()
    return {"status": "ok"}


@celery_app.task(name="socialmind.scheduler.tasks.health_check_proxy")
def health_check_proxy() -> dict[str, Any]:
    """Validate all proxies in the pool."""
    return asyncio.run(_health_check_proxy_async())


async def _health_check_proxy_async() -> dict[str, Any]:
    from socialmind.stealth.proxy import ProxyPoolManager

    redis_client = get_redis()
    async with get_db_session() as db:
        manager = ProxyPoolManager(redis_client=redis_client, db_session=db)
        await manager.health_check_all()
    await redis_client.aclose()
    return {"status": "ok"}


@celery_app.task(name="socialmind.scheduler.tasks.collect_analytics")
def collect_analytics() -> dict[str, Any]:
    """Refresh engagement counts on recent posts."""
    return asyncio.run(_collect_analytics_async())


async def _collect_analytics_async() -> dict[str, Any]:
    from socialmind.models.media import PostRecord

    async with get_db_session() as db:
        result = await db.execute(
            select(PostRecord)
            .where(PostRecord.published_at > datetime.now(UTC) - timedelta(days=7))
            .where(
                (PostRecord.engagement_updated_at.is_(None))
                | (
                    PostRecord.engagement_updated_at
                    < datetime.now(UTC) - timedelta(hours=4)
                )
            )
        )
        posts = result.scalars().all()
        logger.info("collect_analytics: %d posts to refresh", len(posts))
        # Adapters would be called here to fetch live engagement data
    return {"status": "ok", "posts_checked": len(posts)}


@celery_app.task(
    bind=True,
    name="socialmind.scheduler.tasks.run_warmup",
    max_retries=3,
    default_retry_delay=3600,
)
def run_warmup(self: Any, account_id: str) -> dict[str, Any]:
    """Execute one day's warmup activities for a new account."""
    return asyncio.run(_run_warmup_async(self, account_id))


# Warmup ramp: day → {likes, follows}
_WARMUP_SCHEDULE: dict[int, dict[str, int]] = {
    **{d: {"likes": d * 2, "follows": d} for d in range(1, 8)},      # week 1
    **{d: {"likes": 15, "follows": 8} for d in range(8, 15)},         # week 2
    **{d: {"likes": 25, "follows": 12} for d in range(15, 22)},        # week 3
    **{d: {"likes": 35, "follows": 15} for d in range(22, 30)},        # week 4
    30: {"likes": 40, "follows": 20},
}


async def _run_warmup_async(celery_self: Any, account_id: str) -> dict[str, Any]:
    from socialmind.stealth.timing import TimingEngine

    redis_client = get_redis()

    async with get_db_session() as db:
        account: Account | None = await db.get(Account, account_id)
        if account is None:
            return {"status": "not_found"}

        if not await acquire_account_lock(account.id, redis_client):
            raise celery_self.retry(countdown=3600)

        day = min(account.warmup_day, 30)
        schedule = _WARMUP_SCHEDULE.get(day, _WARMUP_SCHEDULE[30])

        try:
            adapter = await _get_adapter(account, db)
            await adapter.authenticate()

            feed = await adapter.get_feed(limit=schedule["likes"] + 5)
            for item in feed[: schedule["likes"]]:
                await adapter.like(item.platform_id)
                await TimingEngine.delay("like")
                await asyncio.sleep(0)

            account.warmup_day += 1
            if account.warmup_day >= 30:
                account.warmup_phase = False
                account.status = AccountStatus.ACTIVE

            await db.commit()

        except Exception as exc:
            logger.exception("Warmup failed for %s: %s", account_id, exc)
            await db.commit()
            raise celery_self.retry(exc=exc)
        finally:
            await release_account_lock(account.id, redis_client)
            await redis_client.aclose()

    return {"status": "ok", "day": account.warmup_day}


@celery_app.task(name="socialmind.scheduler.tasks.dispatch_campaign_tasks")
def dispatch_campaign_tasks() -> dict[str, Any]:
    """Runs every minute; checks which campaigns are due and creates tasks."""
    return asyncio.run(_dispatch_campaign_tasks_async())


_TASK_TYPE_TO_CELERY: dict[str, Any] = {
    TaskType.POST: execute_post,
    TaskType.REPLY_DM: execute_dm_reply,
    TaskType.ENGAGE_FEED: engage_feed,
}


async def _dispatch_campaign_tasks_async() -> dict[str, Any]:
    from croniter import croniter

    from socialmind.models.task import Campaign

    now = datetime.now(UTC)
    dispatched = 0

    async with get_db_session() as db:
        result = await db.execute(
            select(Campaign).where(Campaign.is_active.is_(True))
        )
        campaigns = result.scalars().all()

        for campaign in campaigns:
            if not campaign.cron_expression:
                continue
            cron = croniter(campaign.cron_expression, now - timedelta(minutes=1))
            next_run = cron.get_next(datetime)
            if next_run > now:
                continue

            for account in campaign.accounts:
                if account.status != AccountStatus.ACTIVE:
                    continue
                task_type_str = campaign.config.get("task_type", TaskType.POST)
                task = Task(
                    account_id=account.id,
                    campaign_id=campaign.id,
                    task_type=task_type_str,
                    status=TaskStatus.QUEUED,
                    config=campaign.config,
                    scheduled_at=now,
                )
                db.add(task)
                await db.flush()

                celery_fn = _TASK_TYPE_TO_CELERY.get(task_type_str)
                if celery_fn:
                    celery_result = celery_fn.delay(task.id)
                    task.celery_task_id = celery_result.id
                    dispatched += 1

        await db.commit()

    return {"status": "ok", "dispatched": dispatched}

