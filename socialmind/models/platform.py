from __future__ import annotations

from enum import StrEnum

from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from socialmind.models.base import Base, TimestampMixin, uuid_pk


class PlatformSlug(StrEnum):
    INSTAGRAM = "instagram"
    TIKTOK = "tiktok"
    REDDIT = "reddit"
    YOUTUBE = "youtube"
    FACEBOOK = "facebook"
    TWITTER = "twitter"
    THREADS = "threads"
    LINKEDIN = "linkedin"


class Platform(Base, TimestampMixin):
    __tablename__ = "platforms"

    id: Mapped[str] = uuid_pk()
    slug: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(64), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Capabilities flags
    supports_dm: Mapped[bool] = mapped_column(Boolean, default=True)
    supports_stories: Mapped[bool] = mapped_column(Boolean, default=False)
    supports_reels: Mapped[bool] = mapped_column(Boolean, default=False)
    supports_video: Mapped[bool] = mapped_column(Boolean, default=False)
    supports_polls: Mapped[bool] = mapped_column(Boolean, default=False)

    accounts: Mapped[list[Account]] = relationship(back_populates="platform")  # noqa: F821
