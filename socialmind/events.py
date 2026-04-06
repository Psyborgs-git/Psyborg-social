from __future__ import annotations

from enum import StrEnum
from dataclasses import dataclass, field
from datetime import datetime, timezone


class EventType(StrEnum):
    TASK_STARTED = "task.started"
    TASK_COMPLETED = "task.completed"
    TASK_FAILED = "task.failed"
    ACCOUNT_SUSPENDED = "account.suspended"
    PROXY_FAILED = "proxy.failed"
    RATE_LIMIT_HIT = "rate_limit.hit"
    DM_RECEIVED = "dm.received"
    POST_PUBLISHED = "post.published"


@dataclass
class SocialMindEvent:
    event_type: EventType
    payload: dict = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    account_id: str | None = None
    task_id: str | None = None
