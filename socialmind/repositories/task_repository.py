from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from socialmind.models.task import Task, TaskLog, TaskStatus


class TaskRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_id(self, task_id: str) -> Task | None:
        return await self._session.get(Task, task_id)

    async def get_for_account(
        self, account_id: str, limit: int = 20
    ) -> list[Task]:
        result = await self._session.execute(
            select(Task)
            .where(Task.account_id == account_id)
            .order_by(Task.created_at.desc())
            .limit(limit)
        )
        return list(result.scalars())

    async def create(self, **kwargs: object) -> Task:
        task = Task(**kwargs)
        self._session.add(task)
        await self._session.flush()
        await self._session.refresh(task)
        return task

    async def update_status(self, task_id: str, status: TaskStatus) -> Task:
        task = await self.get_by_id(task_id)
        if task is None:
            raise ValueError(f"Task {task_id} not found")
        task.status = status
        await self._session.flush()
        return task

    async def get_logs(self, task_id: str) -> list[TaskLog]:
        result = await self._session.execute(
            select(TaskLog)
            .where(TaskLog.task_id == task_id)
            .order_by(TaskLog.timestamp.asc())
        )
        return list(result.scalars())

