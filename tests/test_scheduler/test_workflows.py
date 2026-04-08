from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from socialmind.scheduler.workflows import run_post_workflow


@pytest.mark.asyncio
async def test_run_post_workflow_returns_error_for_missing_account():
    """When the account does not exist, run_post_workflow returns an error."""
    mock_db = AsyncMock()
    mock_db.get = AsyncMock(return_value=None)
    mock_db.commit = AsyncMock()
    mock_db.add = MagicMock()
    mock_db.refresh = AsyncMock()
    mock_db.__aenter__ = AsyncMock(return_value=mock_db)
    mock_db.__aexit__ = AsyncMock(return_value=False)

    with patch("socialmind.scheduler.tasks._SessionFactory", MagicMock(return_value=mock_db)):
        result = await run_post_workflow("nonexistent-account", {})

    assert result["status"] == "error"
    assert "not found" in result["error"]


@pytest.mark.asyncio
async def test_run_post_workflow_returns_error_for_inactive_account():
    """When the account is paused, run_post_workflow returns an error."""
    from socialmind.models.account import Account, AccountStatus

    mock_account = MagicMock(spec=Account)
    mock_account.status = AccountStatus.PAUSED
    mock_account.id = "acc-1"

    mock_db = AsyncMock()
    mock_db.get = AsyncMock(return_value=mock_account)
    mock_db.__aenter__ = AsyncMock(return_value=mock_db)
    mock_db.__aexit__ = AsyncMock(return_value=False)

    with patch("socialmind.scheduler.tasks._SessionFactory", MagicMock(return_value=mock_db)):
        result = await run_post_workflow("acc-1", {})

    assert result["status"] == "error"
    assert "not active" in result["error"]


@pytest.mark.asyncio
async def test_run_post_workflow_schedules_task_for_active_account():
    """When account is active, a task is created and dispatched to Celery."""
    from socialmind.models.account import Account, AccountStatus
    from socialmind.models.task import Task

    mock_account = MagicMock(spec=Account)
    mock_account.status = AccountStatus.ACTIVE
    mock_account.id = "acc-active"

    mock_task = MagicMock(spec=Task)
    mock_task.id = "task-scheduled"
    mock_task.celery_task_id = None

    mock_celery_result = MagicMock()
    mock_celery_result.id = "celery-task-id"

    mock_db = AsyncMock()
    mock_db.get = AsyncMock(return_value=mock_account)
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()
    mock_db.__aenter__ = AsyncMock(return_value=mock_db)
    mock_db.__aexit__ = AsyncMock(return_value=False)

    mock_celery_app = MagicMock()
    mock_celery_app.send_task = MagicMock(return_value=mock_celery_result)

    # All three names are imported inside the function body, so we patch at the source.
    with (
        patch("socialmind.scheduler.tasks._SessionFactory", MagicMock(return_value=mock_db)),
        patch("socialmind.models.task.Task", return_value=mock_task),
        patch("socialmind.scheduler.celery_app.celery_app", mock_celery_app),
    ):
        result = await run_post_workflow("acc-active", {"prompt": "Write a great post"})

    assert result["status"] == "scheduled"
    assert result["task_id"] == mock_task.id
    mock_celery_app.send_task.assert_called_once()



@pytest.mark.asyncio
async def test_run_post_workflow_schedules_task_for_active_account(monkeypatch):
    """When account is active, a task is created and dispatched to Celery."""
    from socialmind.models.account import Account, AccountStatus
    from socialmind.models.task import Task

    mock_account = MagicMock(spec=Account)
    mock_account.status = AccountStatus.ACTIVE
    mock_account.id = "acc-active"

    mock_task = MagicMock(spec=Task)
    mock_task.id = "task-scheduled"
    mock_task.celery_task_id = None

    mock_celery_result = MagicMock()
    mock_celery_result.id = "celery-task-id"

    mock_db = AsyncMock()
    mock_db.get = AsyncMock(return_value=mock_account)
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.refresh = AsyncMock()
    mock_db.__aenter__ = AsyncMock(return_value=mock_db)
    mock_db.__aexit__ = AsyncMock(return_value=False)

    mock_celery_app = MagicMock()
    mock_celery_app.send_task = MagicMock(return_value=mock_celery_result)

    # Patch the source modules that are imported inside the function body
    with (
        patch("socialmind.scheduler.tasks._SessionFactory", MagicMock(return_value=mock_db)),
        patch("socialmind.models.task.Task", return_value=mock_task),
        patch("socialmind.scheduler.celery_app.celery_app", mock_celery_app),
    ):
        result = await run_post_workflow("acc-active", {"prompt": "Write a great post"})

    assert result["status"] == "scheduled"
    assert result["task_id"] == mock_task.id
    mock_celery_app.send_task.assert_called_once()
