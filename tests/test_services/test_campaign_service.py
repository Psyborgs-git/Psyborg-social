from __future__ import annotations

import pytest

from socialmind.models.platform import Platform
from socialmind.services.account_service import AccountService
from socialmind.services.campaign_service import CampaignService


@pytest.mark.asyncio
async def test_add_account_to_campaign_returns_loaded_account(db_session):
    platform_slug = "campaign-service-linkedin"
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

    account_service = AccountService(db_session)
    account = await account_service.create_account(
        platform=platform_slug,
        username="campaign-account@example.com",
        credentials={"password": "super-secret"},
    )

    campaign_service = CampaignService(db_session)
    campaign = await campaign_service.create_campaign(
        name="LinkedIn Thought Leadership",
        description="Test campaign",
        cron_expression="0 9 * * 1-5",
    )

    updated_campaign = await campaign_service.add_account(campaign.id, account.id)

    assert len(updated_campaign.accounts) == 1
    assert updated_campaign.accounts[0].id == account.id
    assert updated_campaign.accounts[0].platform is not None
    assert updated_campaign.accounts[0].platform.display_name == "LinkedIn"
