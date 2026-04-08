from __future__ import annotations

import pytest
from sqlalchemy import select

from socialmind.models.account import AccountSession
from socialmind.models.platform import Platform
from socialmind.services.account_service import AccountService


@pytest.mark.asyncio
async def test_create_account_creates_default_session(db_session):
    platform_slug = "account-service-linkedin"
    platform = Platform(
        slug=platform_slug,
        display_name="LinkedIn",
        is_active=True,
        supports_dm=True,
        supports_stories=False,
        supports_reels=False,
        supports_video=True,
        supports_polls=True,
    )
    db_session.add(platform)
    await db_session.flush()

    service = AccountService(db_session)
    account = await service.create_account(
        platform=platform_slug,
        username="person@example.com",
        credentials={"password": "super-secret"},
    )

    result = await db_session.execute(
        select(AccountSession).where(AccountSession.account_id == account.id)
    )
    account_session = result.scalar_one()

    assert account.platform_id == platform.id
    assert account.platform is not None
    assert account.platform.slug == platform_slug
    assert account_session.account_id == account.id
