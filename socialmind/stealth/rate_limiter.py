from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    import redis.asyncio as redis


def _hour_bucket() -> str:
    now = datetime.now(UTC)
    return now.strftime("%Y-%m-%dT%H")


def _day_bucket() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d")


class AccountRateLimiter:
    """
    Per-account rate limits backed by Redis counters.
    Uses separate keys for hourly and daily windows.
    """

    LIMITS: dict[str, dict[str, tuple[int, int]]] = {
        # (hourly_max, daily_max)
        "instagram": {
            "likes": (60, 500),
            "follows": (60, 200),
            "comments": (30, 150),
            "posts": (3, 10),
            "dms": (20, 80),
            "unfollows": (60, 200),
        },
        "twitter": {
            "likes": (100, 1000),
            "follows": (100, 400),
            "posts": (50, 300),
            "dms": (50, 200),
            "comments": (50, 300),
            "unfollows": (100, 400),
        },
        "tiktok": {
            "likes": (80, 600),
            "follows": (50, 200),
            "comments": (30, 150),
            "posts": (5, 20),
            "dms": (20, 80),
            "unfollows": (50, 200),
        },
        "reddit": {
            "likes": (100, 1000),
            "follows": (50, 200),
            "comments": (30, 150),
            "posts": (10, 50),
            "dms": (30, 100),
            "unfollows": (50, 200),
        },
        "youtube": {
            "likes": (100, 500),
            "follows": (50, 200),
            "comments": (20, 100),
            "posts": (5, 20),
            "dms": (0, 0),
            "unfollows": (50, 200),
        },
        "facebook": {
            "likes": (60, 400),
            "follows": (30, 100),
            "comments": (20, 80),
            "posts": (5, 20),
            "dms": (20, 80),
            "unfollows": (30, 100),
        },
        "threads": {
            "likes": (60, 400),
            "follows": (60, 200),
            "comments": (30, 100),
            "posts": (5, 20),
            "dms": (20, 80),
            "unfollows": (60, 200),
        },
        "linkedin": {
            "likes": (60, 300),
            "follows": (30, 120),
            "comments": (20, 80),
            "posts": (5, 20),
            "dms": (20, 80),
            "unfollows": (30, 120),
        },
    }

    def __init__(self, redis_client: redis.Redis) -> None:
        self._redis = redis_client

    async def check_and_increment(
        self,
        account_id: str,
        platform: str,
        action: str,
    ) -> bool:
        """
        Check whether the action is within rate limits and increment the counters.

        Returns True if action is allowed, False if rate limited.
        """
        platform_limits = self.LIMITS.get(platform, {})
        limits = platform_limits.get(action)
        if limits is None:
            return True  # No limit configured → allow

        hourly_max, daily_max = limits

        hourly_key = f"sm:rl:{account_id}:{action}:{_hour_bucket()}"
        daily_key = f"sm:rl:{account_id}:{action}:{_day_bucket()}"

        pipe = self._redis.pipeline()
        pipe.incr(hourly_key)
        pipe.expire(hourly_key, 3600)
        pipe.incr(daily_key)
        pipe.expire(daily_key, 86400)
        results = await pipe.execute()
        hourly_count: int = results[0]
        daily_count: int = results[2]

        if hourly_count > hourly_max or daily_count > daily_max:
            # Roll back the increment since the action is not allowed
            pipe2 = self._redis.pipeline()
            pipe2.decr(hourly_key)
            pipe2.decr(daily_key)
            await pipe2.execute()
            return False

        return True

    async def get_counts(self, account_id: str, platform: str, action: str) -> dict[str, int]:
        """Return current hourly and daily counts for an account/action pair."""
        hourly_key = f"sm:rl:{account_id}:{action}:{_hour_bucket()}"
        daily_key = f"sm:rl:{account_id}:{action}:{_day_bucket()}"
        hourly_val, daily_val = await self._redis.mget(hourly_key, daily_key)
        return {
            "hourly": int(hourly_val or 0),
            "daily": int(daily_val or 0),
        }


def rate_limited(platform: str, action: str):
    """Decorator that checks rate limits before executing an adapter method."""
    import functools

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(self, *args, **kwargs):
            limiter: AccountRateLimiter | None = getattr(self, "_rate_limiter", None)
            if limiter is not None:
                allowed = await limiter.check_and_increment(self.account.id, platform, action)
                if not allowed:
                    logger.warning(
                        "Rate limit hit for account=%s platform=%s action=%s",
                        self.account.id,
                        platform,
                        action,
                    )
                    return None
            return await func(self, *args, **kwargs)

        return wrapper

    return decorator
