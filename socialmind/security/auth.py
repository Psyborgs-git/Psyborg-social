from __future__ import annotations

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from socialmind.config.settings import settings

ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

_ALGORITHM = "HS256"


class AuthenticationError(Exception):
    """Raised when a token is invalid or expired."""


def create_access_token(user_id: str) -> str:
    """Create a short-lived JWT access token for the given user."""
    payload = {
        "sub": user_id,
        "type": "access",
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=_ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    """Create a long-lived JWT refresh token for the given user."""
    payload = {
        "sub": user_id,
        "type": "refresh",
        "iat": datetime.now(timezone.utc),
        "exp": datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=_ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and validate a JWT. Raises AuthenticationError on failure."""
    try:
        payload: dict = jwt.decode(token, settings.SECRET_KEY, algorithms=[_ALGORITHM])
        return payload
    except JWTError as exc:
        raise AuthenticationError("Invalid or expired token") from exc


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------

try:
    from fastapi import Depends, HTTPException
    from fastapi.security import OAuth2PasswordBearer
    from sqlalchemy.ext.asyncio import AsyncSession

    oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")

    async def get_current_user(
        token: str = Depends(oauth2_scheme),
    ) -> "User":  # noqa: F821
        """FastAPI dependency that validates the Bearer token and returns the user."""
        from socialmind.models.user import User

        payload = decode_token(token)
        user_id: str | None = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Authentication required")
        # Caller is responsible for providing a DB session; this stub shows the pattern.
        return user_id  # type: ignore[return-value]

except ImportError:
    # FastAPI not installed — skip dependency definition
    pass
