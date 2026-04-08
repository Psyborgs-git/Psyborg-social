from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, String, Table, Text, text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from socialmind.models.base import Base, TimestampMixin, uuid_pk

# Association tables
task_media = Table(
    "task_media",
    Base.metadata,
    Column("task_id", ForeignKey("tasks.id"), primary_key=True),
    Column("media_asset_id", ForeignKey("media_assets.id"), primary_key=True),
)

campaign_accounts = Table(
    "campaign_accounts",
    Base.metadata,
    Column("campaign_id", ForeignKey("campaigns.id"), primary_key=True),
    Column("account_id", ForeignKey("accounts.id"), primary_key=True),
)


class TaskType(StrEnum):
    POST = "post"
    COMMENT = "comment"
    REPLY_DM = "reply_dm"
    LIKE = "like"
    FOLLOW = "follow"
    UNFOLLOW = "unfollow"
    STORY = "story"
    REEL = "reel"
    RESEARCH = "research"
    ENGAGE_FEED = "engage_feed"
    WARMUP = "warmup"


class TaskStatus(StrEnum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    RETRYING = "retrying"
    SKIPPED = "skipped"


class Task(Base, TimestampMixin):
    __tablename__ = "tasks"

    id: Mapped[str] = uuid_pk()
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    campaign_id: Mapped[str | None] = mapped_column(ForeignKey("campaigns.id"))

    task_type: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default=TaskStatus.PENDING)

    # Scheduling
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Task configuration
    config: Mapped[dict] = mapped_column(JSON, default=dict)

    # Retry logic
    max_retries: Mapped[int] = mapped_column(Integer, default=3)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    celery_task_id: Mapped[str | None] = mapped_column(String(256))

    account: Mapped[Account] = relationship(back_populates="tasks")  # noqa: F821
    campaign: Mapped[Campaign | None] = relationship(back_populates="tasks")
    logs: Mapped[list[TaskLog]] = relationship(back_populates="task")
    media: Mapped[list[MediaAsset]] = relationship(secondary=task_media)  # noqa: F821


class TaskLog(Base):
    __tablename__ = "task_logs"

    id: Mapped[str] = uuid_pk()
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id"), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    level: Mapped[str] = mapped_column(String(16))
    message: Mapped[str] = mapped_column(Text)
    log_metadata: Mapped[dict] = mapped_column(JSON, default=dict, name="metadata")

    task: Mapped[Task] = relationship(back_populates="logs")


class Campaign(Base, TimestampMixin):
    """A named collection of tasks that share a goal."""

    __tablename__ = "campaigns"

    id: Mapped[str] = uuid_pk()
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(default=True)

    # Cron schedule for auto-generating tasks
    cron_expression: Mapped[str | None] = mapped_column(String(128))

    accounts: Mapped[list[Account]] = relationship(secondary=campaign_accounts)  # noqa: F821
    tasks: Mapped[list[Task]] = relationship(back_populates="campaign")
