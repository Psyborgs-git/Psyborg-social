from __future__ import annotations

from datetime import UTC, datetime

import pytest

from socialmind.session import RedisSessionManager, SessionState


class FakeRedis:
    def __init__(self) -> None:
        self.data: dict[str, str] = {}
        self.expiry: dict[str, int] = {}

    async def get(self, key: str) -> str | None:
        return self.data.get(key)

    async def set(self, key: str, value: str, ex: int | None = None) -> None:
        self.data[key] = value
        if ex is not None:
            self.expiry[key] = ex

    async def expire(self, key: str, ttl: int) -> None:
        if key in self.data:
            self.expiry[key] = ttl

    async def delete(self, key: str) -> None:
        self.data.pop(key, None)
        self.expiry.pop(key, None)


@pytest.mark.asyncio
async def test_save_and_get_session_round_trip():
    redis = FakeRedis()
    manager = RedisSessionManager(redis)
    expires_at = datetime(2026, 4, 9, tzinfo=UTC)

    await manager.save_session(
        "acct-123",
        SessionState(
            cookies=[{"name": "auth_token", "value": "secret"}],
            local_storage=[{"origin": "https://x.com", "localStorage": []}],
            session_storage=[],
            api_tokens={"bearer": "abc"},
            expires_at=expires_at,
        ),
        ttl_seconds=120,
    )

    restored = await manager.get_session("acct-123")

    assert restored is not None
    assert restored.cookies[0]["name"] == "auth_token"
    assert restored.local_storage[0]["origin"] == "https://x.com"
    assert restored.api_tokens == {"bearer": "abc"}
    assert restored.expires_at == expires_at
    assert redis.expiry["sm:session:acct-123"] == 120


@pytest.mark.asyncio
async def test_invalidate_session_removes_key():
    redis = FakeRedis()
    manager = RedisSessionManager(redis)
    await manager.save_session(
        "acct-456",
        SessionState(cookies=[], local_storage=[], session_storage=[]),
    )

    await manager.invalidate_session("acct-456")

    assert await manager.get_session("acct-456") is None
