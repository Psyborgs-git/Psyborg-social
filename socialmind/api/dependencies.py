from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from socialmind.config.settings import settings

_engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG)
_session_factory = async_sessionmaker(_engine, expire_on_commit=False)


async def get_db() -> AsyncSession:
    async with _session_factory() as session:
        yield session
