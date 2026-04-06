from __future__ import annotations

from typing import TYPE_CHECKING

from socialmind.config.settings import settings
from socialmind.models.account import Account, AccountStatus
from socialmind.repositories.account_repository import AccountRepository
from socialmind.security.encryption import get_vault

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession


class AccountService:
    def __init__(self, session: AsyncSession) -> None:
        self._repo = AccountRepository(session)
        self._session = session

    async def get_account(self, account_id: str) -> Account:
        account = await self._repo.get_by_id(account_id)
        if account is None:
            raise ValueError(f"Account {account_id} not found")
        return account

    async def list_accounts(
        self,
        platform: str | None = None,
        status: str | None = None,
    ) -> list[Account]:
        return await self._repo.get_all(platform_slug=platform, status=status)

    async def create_account(
        self,
        platform: str,
        username: str,
        credentials: dict,
        proxy_url: str | None = None,
    ) -> Account:
        from sqlalchemy import select

        from socialmind.models.platform import Platform

        result = await self._session.execute(
            select(Platform).where(Platform.slug == platform)
        )
        db_platform = result.scalar()
        if db_platform is None:
            raise ValueError(f"Platform {platform!r} not found")

        encrypted_creds = get_vault().encrypt(credentials)
        account = await self._repo.create(
            platform_id=db_platform.id,
            username=username,
            credentials_encrypted=encrypted_creds,
            status=AccountStatus.ACTIVE,
        )
        return account

    async def pause(self, account_id: str, reason: str) -> Account:
        account = await self._repo.update_status(account_id, AccountStatus.PAUSED)
        await self._repo.update(account_id, suspension_reason=reason)
        await self._revoke_pending_tasks(account_id)
        return account

    async def resume(self, account_id: str) -> Account:
        account = await self._repo.update_status(account_id, AccountStatus.ACTIVE)
        await self._repo.update(account_id, suspension_reason=None)
        return account

    async def delete(self, account_id: str) -> None:
        await self._revoke_pending_tasks(account_id)
        await self._repo.delete(account_id)

    async def get_rate_limit_usage(self, account_id: str) -> dict:
        from datetime import UTC, datetime

        import redis.asyncio as aioredis

        redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        account = await self.get_account(account_id)

        try:
            hour_bucket = datetime.now(UTC).strftime("%Y-%m-%dT%H")
            day_bucket = datetime.now(UTC).strftime("%Y-%m-%d")
            platform = account.platform.slug

            usage: dict = {}
            for action in ("posts", "likes", "follows", "comments", "dms"):
                hour_key = f"sm:rl:{account_id}:{platform}:{action}:h:{hour_bucket}"
                day_key = f"sm:rl:{account_id}:{platform}:{action}:d:{day_bucket}"
                hour_count = await redis_client.get(hour_key)
                day_count = await redis_client.get(day_key)
                usage[action] = {
                    "hourly": int(hour_count or 0),
                    "daily": int(day_count or 0),
                }
            return usage
        finally:
            await redis_client.aclose()

    async def _revoke_pending_tasks(self, account_id: str) -> None:
        """Cancel queued Celery tasks for this account."""
        from sqlalchemy import select

        from socialmind.models.task import Task, TaskStatus

        result = await self._session.execute(
            select(Task)
            .where(Task.account_id == account_id)
            .where(Task.status.in_([TaskStatus.QUEUED, TaskStatus.PENDING]))
        )
        for task in result.scalars():
            if task.celery_task_id:
                from celery.result import AsyncResult

                AsyncResult(task.celery_task_id).revoke(terminate=False)
            task.status = TaskStatus.SKIPPED
        await self._session.flush()

