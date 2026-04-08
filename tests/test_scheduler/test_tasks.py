from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from socialmind.scheduler.tasks import (
    acquire_account_lock,
    release_account_lock,
    _day_bucket,
    _log,
)


# ---------------------------------------------------------------------------
# acquire_account_lock / release_account_lock
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_acquire_lock_succeeds_on_first_call():
    redis = AsyncMock()
    redis.set = AsyncMock(return_value=True)

    acquired = await acquire_account_lock("acc-1", redis)

    assert acquired is True
    redis.set.assert_called_once_with("sm:task:running:acc-1", "1", nx=True, ex=600)


@pytest.mark.asyncio
async def test_acquire_lock_fails_when_already_locked():
    redis = AsyncMock()
    redis.set = AsyncMock(return_value=None)  # Redis returns None when NX fails

    acquired = await acquire_account_lock("acc-1", redis)

    assert acquired is False


@pytest.mark.asyncio
async def test_release_lock_deletes_key():
    redis = AsyncMock()
    redis.delete = AsyncMock(return_value=1)

    await release_account_lock("acc-1", redis)

    redis.delete.assert_called_once_with("sm:task:running:acc-1")


# ---------------------------------------------------------------------------
# _day_bucket
# ---------------------------------------------------------------------------


def test_day_bucket_returns_date_string():
    bucket = _day_bucket()
    # Should match YYYY-MM-DD
    import re

    assert re.match(r"\d{4}-\d{2}-\d{2}", bucket)


# ---------------------------------------------------------------------------
# _log helper
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_log_adds_task_log_and_flushes():
    from socialmind.models.task import Task, TaskStatus, TaskType

    task = Task(
        account_id="acc-1",
        task_type=TaskType.POST,
        status=TaskStatus.PENDING,
        config={},
    )
    task.id = "task-1"

    db = AsyncMock()
    db.add = MagicMock()
    db.flush = AsyncMock()

    await _log(db, task, "INFO", "Test message")

    db.add.assert_called_once()
    db.flush.assert_called_once()
    added_log = db.add.call_args[0][0]
    assert added_log.level == "INFO"
    assert added_log.message == "Test message"
    assert added_log.task_id == "task-1"


# ---------------------------------------------------------------------------
# dispatch_campaign_tasks — unit tests with mocked DB
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_dispatch_campaign_tasks_returns_ok_with_no_campaigns(monkeypatch):
    """When there are no active campaigns, dispatch returns ok with 0 dispatched."""
    from socialmind.scheduler import tasks as tasks_mod

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.commit = AsyncMock()
    mock_db.__aenter__ = AsyncMock(return_value=mock_db)
    mock_db.__aexit__ = AsyncMock(return_value=False)

    mock_factory = MagicMock(return_value=mock_db)

    monkeypatch.setattr(tasks_mod, "_SessionFactory", mock_factory)

    result = await tasks_mod._dispatch_campaign_tasks_async()
    assert result["status"] == "ok"
    assert result["dispatched"] == 0


# ---------------------------------------------------------------------------
# research_trends — caching behaviour
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_research_trends_returns_cached_when_cache_hit(monkeypatch):
    """When the Redis cache key exists, research_trends returns early."""
    from socialmind.scheduler import tasks as tasks_mod

    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value='[{"title": "cached"}]')
    mock_redis.aclose = AsyncMock()

    monkeypatch.setattr(tasks_mod, "get_redis", MagicMock(return_value=mock_redis))

    result = await tasks_mod._research_trends_async("instagram", "fitness")

    assert result["status"] == "cached"
    mock_redis.aclose.assert_called_once()


@pytest.mark.asyncio
async def test_research_trends_returns_no_healthy_account_when_db_empty(monkeypatch):
    """When no active accounts exist, research_trends returns no_healthy_account."""
    from socialmind.scheduler import tasks as tasks_mod

    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=None)
    mock_redis.aclose = AsyncMock()

    mock_result = MagicMock()
    mock_result.scalar.return_value = None

    mock_db = AsyncMock()
    mock_db.execute = AsyncMock(return_value=mock_result)
    mock_db.__aenter__ = AsyncMock(return_value=mock_db)
    mock_db.__aexit__ = AsyncMock(return_value=False)

    monkeypatch.setattr(tasks_mod, "get_redis", MagicMock(return_value=mock_redis))
    monkeypatch.setattr(tasks_mod, "_SessionFactory", MagicMock(return_value=mock_db))

    result = await tasks_mod._research_trends_async("twitter", "tech")

    assert result["status"] == "no_healthy_account"
