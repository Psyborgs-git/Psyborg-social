from __future__ import annotations

from typing import Annotated, AsyncGenerator

import redis.asyncio as redis
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from socialmind.config.settings import settings
from socialmind.models.user import User
from socialmind.security.auth import decode_token, AuthenticationError
from socialmind.services.account_service import AccountService
from socialmind.services.campaign_service import CampaignService
from socialmind.services.post_service import PostService

_engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG)
_session_factory = async_sessionmaker(_engine, expire_on_commit=False)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/token")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with _session_factory() as session:
        yield session


async def get_redis() -> AsyncGenerator[redis.Redis, None]:
    client = redis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        yield client
    finally:
        await client.aclose()


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    try:
        payload = decode_token(token)
    except AuthenticationError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    user_id: str | None = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Authentication required")

    user = await db.get(User, user_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="User not found or inactive")

    return user


async def get_account_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> AccountService:
    return AccountService(db)


async def get_post_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PostService:
    return PostService(db)


async def get_campaign_service(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> CampaignService:
    return CampaignService(db)
