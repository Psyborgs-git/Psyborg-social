from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


async def run_post_workflow(account_id: str, content_config: dict[str, Any]) -> dict[str, Any]:
    """
    Orchestrate a full post workflow:
    1. Validate the account and campaign config
    2. Create a Task record in the database
    3. Dispatch the execute_post Celery task
    Returns a dict with ``task_id`` and ``status`` on success.
    """

    from socialmind.models.account import Account, AccountStatus
    from socialmind.models.task import Task, TaskStatus, TaskType
    from socialmind.scheduler.celery_app import celery_app
    from socialmind.scheduler.tasks import _SessionFactory

    async with _SessionFactory() as db:
        account: Account | None = await db.get(Account, account_id)
        if account is None:
            return {"status": "error", "error": f"Account {account_id} not found"}

        if account.status != AccountStatus.ACTIVE:
            return {
                "status": "error",
                "error": f"Account {account_id} is {account.status}, not active",
            }

        task = Task(
            account_id=account.id,
            task_type=TaskType(content_config.get("task_type", TaskType.POST)),
            status=TaskStatus.QUEUED,
            config=content_config,
            scheduled_at=datetime.now(UTC),
        )
        db.add(task)
        await db.commit()
        await db.refresh(task)

        celery_result = celery_app.send_task(
            "socialmind.scheduler.tasks.execute_post",
            args=[task.id],
        )
        task.celery_task_id = celery_result.id
        await db.commit()

    return {"status": "scheduled", "task_id": task.id, "celery_task_id": celery_result.id}
