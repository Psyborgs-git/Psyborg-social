from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

import httpx

if TYPE_CHECKING:
    import redis.asyncio as redis
    from sqlalchemy.ext.asyncio import AsyncSession

    from socialmind.models.account import Account
    from socialmind.models.proxy import Proxy


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


class ProxyPoolManager:
    """
    Manages a pool of proxies with health tracking, sticky assignment, and
    automatic rotation on failure.
    """

    def __init__(self, redis_client: "redis.Redis", db_session: "AsyncSession") -> None:
        self._redis = redis_client
        self._db = db_session

    async def get_proxy_for_account(self, account: "Account") -> "Proxy | None":
        """Return the sticky proxy for this account, or assign a new one."""
        from socialmind.models.proxy import Proxy

        if account.proxy_id:
            proxy: Proxy | None = await self._db.get(Proxy, account.proxy_id)
            if proxy and proxy.is_healthy:
                return proxy
        return await self._assign_best_proxy(account)

    async def _assign_best_proxy(self, account: "Account") -> "Proxy | None":
        """Pick the best available proxy for this account."""
        from sqlalchemy import select

        from socialmind.models.proxy import Proxy

        platform_slug = account.platform.slug if account.platform else ""
        mobile_preferred = platform_slug in ("instagram", "tiktok", "threads")

        query = select(Proxy).where(Proxy.is_healthy == True).order_by(Proxy.failure_count.asc())  # noqa: E712
        if mobile_preferred:
            from sqlalchemy import case

            query = select(Proxy).where(Proxy.is_healthy == True).order_by(  # noqa: E712
                case((Proxy.provider == "mobile", 0), else_=1),
                Proxy.failure_count.asc(),
            )

        result = await self._db.execute(query)
        for proxy in result.scalars():
            load = await self._get_proxy_load(proxy.id)
            if load < 3:
                account.proxy_id = proxy.id
                await self._db.commit()
                return proxy
        return None

    async def _get_proxy_load(self, proxy_id: str) -> int:
        """Count how many accounts are currently using this proxy."""
        from sqlalchemy import func, select

        from socialmind.models.account import Account

        result = await self._db.execute(
            select(func.count(Account.id)).where(Account.proxy_id == proxy_id)
        )
        return result.scalar_one_or_none() or 0

    async def mark_proxy_failed(self, proxy_id: str, reason: str) -> None:
        """Increment failure count and mark proxy unhealthy after threshold."""
        from socialmind.models.proxy import Proxy

        proxy: Proxy | None = await self._db.get(Proxy, proxy_id)
        if proxy is None:
            return
        proxy.failure_count += 1
        if proxy.failure_count >= 5:
            proxy.is_healthy = False
        await self._db.commit()
        await self._redis.incr(f"sm:proxy:failures:{proxy_id}:{_today()}")

    async def health_check_all(self) -> None:
        """Run periodically via Celery beat to validate the full proxy pool."""
        from sqlalchemy import select

        from socialmind.models.proxy import Proxy

        result = await self._db.execute(select(Proxy))
        for proxy in result.scalars():
            is_ok = await self._check_proxy_health(proxy)
            proxy.is_healthy = is_ok
            proxy.last_checked_at = datetime.now(timezone.utc)
            if is_ok:
                proxy.failure_count = 0
        await self._db.commit()

    async def _check_proxy_health(self, proxy: "Proxy") -> bool:
        """Verify a proxy is reachable by hitting an external IP echo endpoint."""
        try:
            async with httpx.AsyncClient(
                proxy=proxy.as_httpx_url(), timeout=10.0
            ) as client:
                resp = await client.get("https://api.ipify.org?format=json")
                return resp.status_code == 200
        except (httpx.ProxyError, httpx.ConnectError, httpx.TimeoutException):
            return False
