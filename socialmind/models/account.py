from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from socialmind.models.base import Base, TimestampMixin, uuid_pk

if TYPE_CHECKING:
    from socialmind.models.persona import Persona
    from socialmind.models.platform import Platform
    from socialmind.models.proxy import Proxy
    from socialmind.models.task import Task


class AccountStatus(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    SUSPENDED = "suspended"
    CREDENTIAL_ERROR = "credential_error"
    WARMING_UP = "warming_up"


class Account(Base, TimestampMixin):
    __tablename__ = "accounts"

    id: Mapped[str] = uuid_pk()
    platform_id: Mapped[str] = mapped_column(ForeignKey("platforms.id"), nullable=False)
    persona_id: Mapped[str | None] = mapped_column(ForeignKey("personas.id"))

    # Identity
    username: Mapped[str] = mapped_column(String(128), nullable=False)
    display_name: Mapped[str | None] = mapped_column(String(128))
    email: Mapped[str | None] = mapped_column(String(256))
    phone: Mapped[str | None] = mapped_column(String(32))

    # Credentials (encrypted at rest)
    credentials_encrypted: Mapped[bytes] = mapped_column(nullable=False)

    # Platform-specific metadata
    platform_user_id: Mapped[str | None] = mapped_column(String(256))
    platform_metadata: Mapped[dict] = mapped_column(JSON, default=dict)

    # Status
    status: Mapped[str] = mapped_column(String(32), default=AccountStatus.ACTIVE)
    suspension_reason: Mapped[str | None] = mapped_column(Text)
    last_active_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Rate limiting & warmup
    daily_action_limit: Mapped[int] = mapped_column(Integer, default=100)
    warmup_phase: Mapped[bool] = mapped_column(Boolean, default=False)
    warmup_day: Mapped[int] = mapped_column(Integer, default=0)

    # Proxy assignment (sticky)
    proxy_id: Mapped[str | None] = mapped_column(ForeignKey("proxies.id"))

    # Relationships
    platform: Mapped[Platform] = relationship(back_populates="accounts")
    persona: Mapped[Persona | None] = relationship(
        back_populates="accounts"
    )
    proxy: Mapped[Proxy | None] = relationship(
        back_populates="accounts"
    )
    sessions: Mapped[list[AccountSession]] = relationship(  # noqa: F821
        back_populates="account", cascade="all, delete"
    )
    tasks: Mapped[list[Task]] = relationship(  # noqa: F821
        back_populates="account", cascade="all, delete"
    )

    def set_credentials(self, credentials: dict) -> None:
        """Encrypt and store credentials."""
        from socialmind.security.encryption import get_vault

        self.credentials_encrypted = get_vault().encrypt(credentials)

    def decrypt_credentials(self) -> dict:
        """Decrypt credentials."""
        from socialmind.security.encryption import get_vault

        return get_vault().decrypt(self.credentials_encrypted)


class AccountSession(Base, TimestampMixin):
    """Persisted browser/API session state for an account."""

    __tablename__ = "account_sessions"

    id: Mapped[str] = uuid_pk()
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.id"), nullable=False)

    # Browser session state
    cookies: Mapped[dict | None] = mapped_column(JSON)
    local_storage: Mapped[dict | None] = mapped_column(JSON)
    session_storage: Mapped[dict | None] = mapped_column(JSON)

    # API session tokens (encrypted)
    api_tokens_encrypted: Mapped[bytes | None] = mapped_column()

    # Session health
    is_valid: Mapped[bool] = mapped_column(Boolean, default=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    invalidation_reason: Mapped[str | None] = mapped_column(String(256))

    account: Mapped[Account] = relationship(back_populates="sessions")

    @property
    def api_tokens(self) -> dict | None:
        if self.api_tokens_encrypted:
            from socialmind.security.encryption import get_vault

            return get_vault().decrypt(self.api_tokens_encrypted)
        return None

    @api_tokens.setter
    def api_tokens(self, value: dict | None) -> None:
        if value is None:
            self.api_tokens_encrypted = None
        else:
            from socialmind.security.encryption import get_vault

            self.api_tokens_encrypted = get_vault().encrypt(value)

    @property
    def browser_storage_state(self) -> dict | None:
        """Return combined browser storage state for Playwright."""
        if self.cookies or self.local_storage:
            return {
                "cookies": self.cookies or [],
                "origins": self.local_storage or [],
            }
        return None
