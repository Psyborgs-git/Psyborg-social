#!/usr/bin/env python
"""Quick script to seed an admin user."""
import asyncio
import sys
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from socialmind.config.settings import settings
from socialmind.models.user import User


async def seed_admin():
    """Create the admin superuser."""
    pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
    engine = create_async_engine(settings.DATABASE_URL)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    try:
        async with session_factory() as db:
            user = User(
                username="admin",
                hashed_password=pwd_ctx.hash("password"),
                is_admin=True,
            )
            db.add(user)
            await db.commit()
        print("✓ Superuser 'admin' created successfully!")
    except Exception as e:
        print(f"✗ Error creating superuser: {e}", file=sys.stderr)
        return False
    finally:
        await engine.dispose()

    return True


if __name__ == "__main__":
    success = asyncio.run(seed_admin())
    sys.exit(0 if success else 1)
