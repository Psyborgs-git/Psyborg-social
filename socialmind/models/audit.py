from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, String, text
from sqlalchemy.orm import Mapped, mapped_column

from socialmind.models.base import Base, uuid_pk


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = uuid_pk()
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()")
    )
    event: Mapped[str] = mapped_column(String(128), nullable=False)
    actor_id: Mapped[str | None] = mapped_column(String(256))
    account_id: Mapped[str | None] = mapped_column(String(256))
    ip_address: Mapped[str | None] = mapped_column(String(64))
    log_metadata: Mapped[dict] = mapped_column(JSON, default=dict, name="metadata")


AUDIT_EVENTS: dict[str, str] = {
    "credential_access": "Account credentials were decrypted and accessed",
    "credential_update": "Account credentials were changed",
    "account_delete": "Account was deleted",
    "key_rotation": "Encryption key rotation was performed",
    "mcp_auth_failure": "Failed MCP authentication attempt",
    "user_login": "User logged in to dashboard",
    "user_login_failure": "Failed dashboard login attempt",
    "account_suspended": "Account status set to suspended",
    "bulk_export": "Data export was triggered",
}
