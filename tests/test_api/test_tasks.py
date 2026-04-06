from __future__ import annotations

import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock

from socialmind.api.main import app
from socialmind.models.task import Task, TaskStatus, TaskType


@pytest.mark.asyncio
async def test_list_tasks_requires_auth():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
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
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
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
