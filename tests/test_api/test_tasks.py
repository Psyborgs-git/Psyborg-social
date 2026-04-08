from __future__ import annotations

import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock

from socialmind.api.main import app
from socialmind.api.routers.tasks import _cancel_task
from socialmind.models.platform import Platform
from socialmind.models.task import Task, TaskStatus, TaskType
from socialmind.services.account_service import AccountService


@pytest.mark.asyncio
async def test_list_tasks_requires_auth():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/tasks/")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_task_not_found_with_auth():
    from socialmind.api.dependencies import get_current_user, get_db
    from sqlalchemy.ext.asyncio import AsyncSession

    mock_db = AsyncMock(spec=AsyncSession)
    mock_db.get = AsyncMock(return_value=None)

    app.dependency_overrides[get_current_user] = lambda: "user-123"
    app.dependency_overrides[get_db] = lambda: mock_db

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/tasks/nonexistent-id")
        assert response.status_code == 404
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_task_status_values():
    assert TaskStatus.PENDING == "pending"
    assert TaskStatus.RUNNING == "running"
    assert TaskStatus.SUCCESS == "success"
    assert TaskStatus.FAILED == "failed"


@pytest.mark.asyncio
async def test_task_type_values():
    assert TaskType.POST == "post"
    assert TaskType.FOLLOW == "follow"
    assert TaskType.LIKE == "like"


@pytest.mark.asyncio
async def test_cancel_task_marks_pending_task_as_skipped(db_session):
    platform_slug = "task-test-linkedin"
    platform = Platform(
        slug=platform_slug,
        display_name="LinkedIn",
        is_active=True,
        supports_dm=True,
        supports_stories=False,
        supports_reels=False,
        supports_video=True,
        supports_polls=True,
    )
    db_session.add(platform)
    await db_session.flush()

    account = await AccountService(db_session).create_account(
        platform=platform_slug,
        username="task-cancel@example.com",
        credentials={"password": "super-secret"},
    )

    task = Task(
        account_id=account.id,
        task_type=TaskType.LIKE,
        status=TaskStatus.PENDING,
        config={},
    )
    db_session.add(task)
    await db_session.commit()
    await db_session.refresh(task)

    cancelled_task = await _cancel_task(task.id, db_session)

    assert cancelled_task.status == TaskStatus.SKIPPED
