from __future__ import annotations

import asyncio
from typing import Any

from loguru import logger

from socialmind.scheduler.celery_app import celery_app


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def execute_task(self, task_id: str) -> dict[str, Any]:
    """Execute a SocialMind automation task by ID."""
    return asyncio.run(_execute_task_async(task_id))


async def _execute_task_async(task_id: str) -> dict[str, Any]:
    """Async implementation of task execution."""
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from socialmind.adapters.registry import get_adapter
    from socialmind.config.settings import settings
    from socialmind.models.task import Task, TaskStatus

    engine = create_async_engine(settings.DATABASE_URL)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as db:
        task: Task | None = await db.get(Task, task_id)
        if task is None:
            logger.error("Task %s not found", task_id)
            return {"status": "not_found"}

        task.status = TaskStatus.RUNNING
        await db.commit()

        try:
            adapter = get_adapter(
                account=task.account,
                session=task.account.sessions[0] if task.account.sessions else None,
                proxy=task.account.proxy,
            )
            authenticated = await adapter.authenticate()
            if not authenticated:
                task.status = TaskStatus.FAILED
                await db.commit()
                return {"status": "auth_failed"}

            task.status = TaskStatus.SUCCESS
            await db.commit()
            return {"status": "success"}
        except Exception as exc:
            logger.exception("Task %s failed: %s", task_id, exc)
            task.status = TaskStatus.FAILED
            await db.commit()
            return {"status": "failed", "error": str(exc)}
    await engine.dispose()


@celery_app.task
def check_proxy_health() -> None:
    """Periodic task to validate all proxies in the pool."""
    asyncio.run(_check_proxy_health_async())


async def _check_proxy_health_async() -> None:
    """Async implementation of proxy health check."""
    import redis.asyncio as aioredis
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from socialmind.config.settings import settings
    from socialmind.stealth.proxy import ProxyPoolManager

    engine = create_async_engine(settings.DATABASE_URL)
    redis_client = aioredis.from_url(settings.REDIS_URL)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    async with session_factory() as db:
        manager = ProxyPoolManager(redis_client=redis_client, db_session=db)
        await manager.health_check_all()

    await engine.dispose()
    await redis_client.aclose()
