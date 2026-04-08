from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from socialmind.models.task import TaskStatus, TaskType
from socialmind.repositories.task_repository import TaskRepository

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession
    from socialmind.models.task import Task


@dataclass
class PostRecordDTO:
    """Lightweight DTO returned by PostService (wraps the PostRecord DB model)."""

    task_id: str
    account_id: str
    platform_post_id: str
    platform_url: str | None
    published_at: str
    likes_count: int
    comments_count: int
    shares_count: int


class PostService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        self._task_repo = TaskRepository(session)

    async def create_post_task(
        self,
        account_id: str,
        prompt: str,
        post_type: str = "feed",
        include_image: bool = True,
        schedule_at: str | None = None,
    ) -> "Task":
        """Create a scheduled post task and enqueue it in Celery."""
        from datetime import UTC, datetime

        from socialmind.scheduler.tasks import execute_post

        scheduled_dt = (
            datetime.fromisoformat(schedule_at) if schedule_at else datetime.now(UTC)
        )

        task = await self._task_repo.create(
            account_id=account_id,
            task_type=TaskType.POST,
            status=TaskStatus.QUEUED,
            scheduled_at=scheduled_dt,
            config={
                "prompt": prompt,
                "post_type": post_type,
                "include_image": include_image,
            },
        )

        eta = scheduled_dt if schedule_at else None
        celery_result = execute_post.apply_async(args=[task.id], eta=eta)
        task.celery_task_id = celery_result.id
        await self._session.flush()
        await self._session.commit()
        await self._session.refresh(task)

        return task

    async def get_recent_posts(
        self, account_id: str, limit: int = 10
    ) -> list[PostRecordDTO]:
        """Return recent successfully-published posts for an account."""
        from sqlalchemy import select

        from socialmind.models.media import PostRecord as DBPostRecord

        result = await self._session.execute(
            select(DBPostRecord)
            .where(DBPostRecord.account_id == account_id)
            .order_by(DBPostRecord.published_at.desc())
            .limit(limit)
        )
        rows = result.scalars().all()
        return [
            PostRecordDTO(
                task_id=r.task_id,
                account_id=r.account_id,
                platform_post_id=r.platform_post_id,
                platform_url=r.platform_url,
                published_at=r.published_at.isoformat(),
                likes_count=r.likes_count,
                comments_count=r.comments_count,
                shares_count=r.shares_count,
            )
            for r in rows
        ]
