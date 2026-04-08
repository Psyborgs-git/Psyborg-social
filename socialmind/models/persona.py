from __future__ import annotations

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from socialmind.models.base import Base, TimestampMixin, uuid_pk


class Persona(Base, TimestampMixin):
    """AI persona configuration that controls how the LLM generates content."""

    __tablename__ = "personas"

    id: Mapped[str] = uuid_pk()
    name: Mapped[str] = mapped_column(String(128), nullable=False)

    # AI generation instructions
    system_prompt: Mapped[str] = mapped_column(String(4096), nullable=False)
    tone: Mapped[str] = mapped_column(String(64), default="casual")
    niche: Mapped[str] = mapped_column(String(128), default="general")
    language: Mapped[str] = mapped_column(String(16), default="en")
    vocab_level: Mapped[str] = mapped_column(String(32), default="conversational")
    emoji_usage: Mapped[str] = mapped_column(String(16), default="moderate")
    hashtag_strategy: Mapped[str] = mapped_column(String(32), default="relevant")

    # Behavioral config
    reply_probability: Mapped[float] = mapped_column(default=0.7)
    like_probability: Mapped[float] = mapped_column(default=0.8)
    follow_back_probability: Mapped[float] = mapped_column(default=0.5)

    accounts: Mapped[list[Account]] = relationship(back_populates="persona")  # noqa: F821
