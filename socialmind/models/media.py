from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from socialmind.models.base import Base, TimestampMixin, uuid_pk


class MediaType(StrEnum):
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    GIF = "gif"


class MediaAsset(Base, TimestampMixin):
    __tablename__ = "media_assets"

    id: Mapped[str] = uuid_pk()
    media_type: Mapped[str] = mapped_column(String(16), nullable=False)
    filename: Mapped[str] = mapped_column(String(512), nullable=False)

    # Storage
    storage_bucket: Mapped[str] = mapped_column(String(256), default="socialmind")
    storage_key: Mapped[str] = mapped_column(String(512), nullable=False)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer)
    mime_type: Mapped[str | None] = mapped_column(String(64))

    # Generation metadata
    generated_by: Mapped[str | None] = mapped_column(String(64))
    generation_prompt: Mapped[str | None] = mapped_column(Text)

    # Dimensions
    width: Mapped[int | None] = mapped_column(Integer)
    height: Mapped[int | None] = mapped_column(Integer)
    duration_seconds: Mapped[float | None] = mapped_column()


class PostRecord(Base, TimestampMixin):
    """Record of a successfully published post."""

    __tablename__ = "post_records"

    id: Mapped[str] = uuid_pk()
    task_id: Mapped[str] = mapped_column(ForeignKey("tasks.id"), nullable=False)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), nullable=False)

    platform_post_id: Mapped[str] = mapped_column(String(256))
    platform_url: Mapped[str | None] = mapped_column(String(512))
    content_text: Mapped[str | None] = mapped_column(Text)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    # Engagement snapshot
    likes_count: Mapped[int] = mapped_column(Integer, default=0)
    comments_count: Mapped[int] = mapped_column(Integer, default=0)
    shares_count: Mapped[int] = mapped_column(Integer, default=0)
    views_count: Mapped[int] = mapped_column(Integer, default=0)
    engagement_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
