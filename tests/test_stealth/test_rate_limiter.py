from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from socialmind.stealth.rate_limiter import AccountRateLimiter


def test_limits_defined_for_platforms():
    expected = {"instagram", "twitter", "linkedin"}
    for platform in expected:
        assert platform in AccountRateLimiter.LIMITS, f"No limits for {platform}"


def test_instagram_limits():
    instagram = AccountRateLimiter.LIMITS["instagram"]
    assert "likes" in instagram
    assert "follows" in instagram
    assert "posts" in instagram
    hourly, daily = instagram["likes"]
    assert hourly > 0
    assert daily >= hourly


@pytest.mark.asyncio
async def test_rate_limiter_check_with_mock_redis():
    mock_redis = AsyncMock()
    mock_pipeline = AsyncMock()
    mock_pipeline.incr = MagicMock()
    mock_pipeline.expire = MagicMock()
    mock_pipeline.execute = AsyncMock(return_value=[1, True, 1, True])
    mock_redis.pipeline = MagicMock(return_value=mock_pipeline)

    limiter = AccountRateLimiter(redis_client=mock_redis)

    result = await limiter.check_and_increment("acc-123", "instagram", "likes")
    assert result is True


@pytest.mark.asyncio
async def test_rate_limiter_blocks_when_over_limit():
    mock_redis = AsyncMock()
    mock_pipeline = AsyncMock()
    mock_pipeline.incr = MagicMock()
    mock_pipeline.expire = MagicMock()
    mock_pipeline.execute = AsyncMock(return_value=[61, True, 1, True])
    mock_pipeline2 = AsyncMock()
    mock_pipeline2.decr = MagicMock()
    mock_pipeline2.execute = AsyncMock(return_value=[60, 0])
    mock_redis.pipeline = MagicMock(side_effect=[mock_pipeline, mock_pipeline2])

    limiter = AccountRateLimiter(redis_client=mock_redis)

    result = await limiter.check_and_increment("acc-123", "instagram", "likes")
    assert result is False
