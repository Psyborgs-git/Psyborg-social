from __future__ import annotations

import asyncio
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

# ---------------------------------------------------------------------------
# Event constants
# ---------------------------------------------------------------------------

ACCOUNT_SUSPENDED = "account.suspended"
PROXY_FAILED = "proxy.failed"
TASK_COMPLETED = "task.completed"
DETECTION_TRIGGERED = "detection.triggered"
TASK_STARTED = "task.started"
TASK_FAILED = "task.failed"
RATE_LIMIT_HIT = "rate_limit.hit"
DM_RECEIVED = "dm.received"
POST_PUBLISHED = "post.published"


class EventType(StrEnum):
    TASK_STARTED = "task.started"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    ACCOUNT_SUSPENDED = "account.suspended"
    PROXY_FAILED = "proxy.failed"
    RATE_LIMIT_HIT = "rate_limit.hit"
    DM_RECEIVED = "dm.received"
    POST_PUBLISHED = "post.published"
    DETECTION_TRIGGERED = "detection.triggered"


@dataclass
class SocialMindEvent:
    event_type: EventType
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
    account_id: str | None = None
    task_id: str | None = None


# ---------------------------------------------------------------------------
# Async event bus
# ---------------------------------------------------------------------------

_Handler = Callable[..., Coroutine[Any, Any, None]]


class EventBus:
    """Lightweight in-process async event bus."""

    _subscribers: dict[str, list[_Handler]] = {}

    @classmethod
    def subscribe(cls, event: str, handler: _Handler) -> None:
        """Register an async handler for an event."""
        cls._subscribers.setdefault(event, []).append(handler)

    @classmethod
    async def emit(cls, event: str, **kwargs: Any) -> None:
        """Fire an event; all handlers are scheduled as background tasks."""
        for handler in cls._subscribers.get(event, []):
            asyncio.create_task(handler(**kwargs))

    @classmethod
    def clear(cls) -> None:
        """Remove all subscriptions (useful in tests)."""
        cls._subscribers.clear()

