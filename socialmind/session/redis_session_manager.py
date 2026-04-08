from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any

import redis.asyncio as aioredis

from socialmind.config.settings import settings


def _dt_to_iso(value: datetime | None) -> str | None:
    if value is None:
        return None
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.isoformat()


def _iso_to_dt(value: str | None) -> datetime | None:
    if value is None:
        return None
    return datetime.fromisoformat(value)


@dataclass(slots=True)
class SessionState:
    cookies: list[dict[str, Any]]
    local_storage: list[dict[str, Any]]
    session_storage: list[dict[str, Any]]
    api_tokens: dict[str, Any] | None = None
    expires_at: datetime | None = None
    is_valid: bool = True

    def to_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["expires_at"] = _dt_to_iso(self.expires_at)
        return payload

    @classmethod
    def from_payload(cls, payload: dict[str, Any]) -> SessionState:
        return cls(
            cookies=list(payload.get("cookies") or []),
            local_storage=list(payload.get("local_storage") or []),
            session_storage=list(payload.get("session_storage") or []),
            api_tokens=payload.get("api_tokens"),
            expires_at=_iso_to_dt(payload.get("expires_at")),
            is_valid=bool(payload.get("is_valid", True)),
        )

    @classmethod
    def from_account_session(cls, account_session) -> SessionState:
        return cls(
            cookies=list(account_session.cookies or []),
            local_storage=list(account_session.local_storage or []),
            session_storage=list(account_session.session_storage or []),
            api_tokens=account_session.api_tokens,
            expires_at=account_session.expires_at,
            is_valid=account_session.is_valid,
        )

    @property
    def browser_storage_state(self) -> dict[str, Any] | None:
        if self.cookies or self.local_storage:
            return {
                "cookies": self.cookies,
                "origins": self.local_storage,
            }
        return None


class RedisSessionManager:
    def __init__(self, redis_client: aioredis.Redis | None = None) -> None:
        self._redis = redis_client

    async def get_session(self, account_id: str) -> SessionState | None:
        redis_client, should_close = await self._get_client()
        try:
            raw = await redis_client.get(self._key(account_id))
            if not raw:
                return None
            return SessionState.from_payload(json.loads(raw))
        finally:
            if should_close:
                await redis_client.aclose()

    async def save_session(
        self,
        account_id: str,
        state: SessionState,
        ttl_seconds: int | None = None,
    ) -> None:
        redis_client, should_close = await self._get_client()
        try:
            ttl = ttl_seconds or settings.REDIS_SESSION_TTL
            await redis_client.set(
                self._key(account_id),
                json.dumps(state.to_payload()),
                ex=ttl,
            )
        finally:
            if should_close:
                await redis_client.aclose()

    async def refresh_session(
        self, account_id: str, ttl_seconds: int | None = None
    ) -> None:
        redis_client, should_close = await self._get_client()
        try:
            ttl = ttl_seconds or settings.REDIS_SESSION_TTL
            await redis_client.expire(self._key(account_id), ttl)
        finally:
            if should_close:
                await redis_client.aclose()

    async def invalidate_session(self, account_id: str) -> None:
        redis_client, should_close = await self._get_client()
        try:
            await redis_client.delete(self._key(account_id))
        finally:
            if should_close:
                await redis_client.aclose()

    async def sync_from_account(self, account) -> SessionState | None:
        if not getattr(account, "sessions", None):
            return None
        state = SessionState.from_account_session(account.sessions[0])
        await self.save_session(account.id, state)
        return state

    async def hydrate_account(self, account) -> SessionState | None:
        state = await self.get_session(account.id)
        if state is None:
            if getattr(account, "sessions", None):
                return await self.sync_from_account(account)
            return None

        if not getattr(account, "sessions", None):
            from socialmind.models.account import AccountSession

            account.sessions.append(AccountSession(account_id=account.id))

        session = account.sessions[0]
        session.cookies = state.cookies
        session.local_storage = state.local_storage
        session.session_storage = state.session_storage
        session.api_tokens = state.api_tokens
        session.expires_at = state.expires_at
        session.is_valid = state.is_valid
        return state

    async def persist_account_session(self, account) -> SessionState | None:
        if not getattr(account, "sessions", None):
            return None
        state = SessionState.from_account_session(account.sessions[0])
        await self.save_session(account.id, state)
        return state

    async def _get_client(self) -> tuple[aioredis.Redis, bool]:
        if self._redis is not None:
            return self._redis, False
        return aioredis.from_url(settings.REDIS_URL, decode_responses=True), True

    def _key(self, account_id: str) -> str:
        return f"sm:session:{account_id}"
