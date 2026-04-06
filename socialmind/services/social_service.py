from __future__ import annotations

from typing import TYPE_CHECKING

from socialmind.adapters.base import PostResult
from socialmind.content.pipeline import generate_full_post_content
from socialmind.repositories.account_repository import AccountRepository
from socialmind.repositories.campaign_repository import CampaignRepository

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

    from socialmind.adapters.base import TrendingItem
    from socialmind.models.account import Account
    from socialmind.models.task import Campaign


class SocialMindService:
    """Facade that coordinates adapters, AI pipelines, and the task queue."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._account_repo = AccountRepository(session)
        self._campaign_repo = CampaignRepository(session)

    async def create_post_now(
        self,
        account_id: str,
        prompt: str,
        include_image: bool = True,
    ) -> PostResult:
        """High-level: generate content and post immediately."""
        from socialmind.adapters.registry import get_adapter
        from socialmind.models.task import Task, TaskStatus, TaskType

        account = await self._account_repo.get_by_id(account_id)
        if account is None:
            return PostResult(success=False, error=f"Account {account_id} not found")

        trends = await self._get_cached_trends(account)

        task = Task(
            account_id=account_id,
            task_type=TaskType.POST,
            status=TaskStatus.RUNNING,
            config={"prompt": prompt, "include_image": include_image},
        )
        self._session.add(task)
        await self._session.flush()

        try:
            content = await generate_full_post_content(account, task, trends)
            adapter = get_adapter(
                account=account,
                session=account.sessions[0] if account.sessions else None,
                proxy=account.proxy,
            )
            await adapter.authenticate()
            return await adapter.post(content)
        except Exception as exc:
            return PostResult(success=False, error=str(exc))

    async def schedule_campaign(self, campaign_config: dict) -> Campaign:
        """High-level: create campaign with all its scheduled tasks."""
        return await self._campaign_repo.create(**campaign_config)

    async def _get_cached_trends(self, account: Account) -> list[TrendingItem]:
        """Return cached trending items from Redis, or an empty list."""
        import json

        import redis.asyncio as aioredis

        from socialmind.config.settings import settings

        if account.persona is None:
            return []

        redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        try:
            from datetime import UTC, datetime

            day_bucket = datetime.now(UTC).strftime("%Y-%m-%d")
            cache_key = (
                f"sm:trend:{account.platform.slug}:{account.persona.niche}:{day_bucket}"
            )
            cached = await redis_client.get(cache_key)
            if not cached:
                return []

            from socialmind.adapters.base import TrendingItem

            raw = json.loads(cached)
            return [
                TrendingItem(
                    title=item["title"],
                    url=item.get("url"),
                    engagement_score=item.get("score", 0.0),
                    hashtags=item.get("hashtags", []),
                )
                for item in raw
            ]
        except Exception:
            return []
        finally:
            await redis_client.aclose()

