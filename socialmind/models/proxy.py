from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from socialmind.models.base import Base, TimestampMixin, uuid_pk


class ProxyProtocol(StrEnum):
    SOCKS5 = "socks5"
    SOCKS4 = "socks4"
    HTTP = "http"
    HTTPS = "https"


class Proxy(Base, TimestampMixin):
    __tablename__ = "proxies"

    id: Mapped[str] = uuid_pk()
    protocol: Mapped[str] = mapped_column(String(16), nullable=False)
    host: Mapped[str] = mapped_column(String(256), nullable=False)
    port: Mapped[int] = mapped_column(Integer, nullable=False)
    username: Mapped[str | None] = mapped_column(String(256))
    password_encrypted: Mapped[bytes | None] = mapped_column()

    # Health tracking
    is_healthy: Mapped[bool] = mapped_column(Boolean, default=True)
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    failure_count: Mapped[int] = mapped_column(Integer, default=0)
    country_code: Mapped[str | None] = mapped_column(String(8))
    provider: Mapped[str | None] = mapped_column(String(64))

    accounts: Mapped[list[Account]] = relationship(back_populates="proxy")  # noqa: F821

    def as_url(self) -> str:
        """Return proxy URL string for use in HTTP clients."""
        auth = ""
        if self.username:
            auth = f"{self.username}@"
        return f"{self.protocol}://{auth}{self.host}:{self.port}"

    def as_httpx_url(self) -> str:
        """Return proxy URL for httpx."""
        return self.as_url()

    def as_httpx_proxies(self) -> dict[str, str] | None:
        """Return proxies dict for httpx."""
        url = self.as_url()
        return {"http://": url, "https://": url}
