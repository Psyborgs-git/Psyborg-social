from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from socialmind.api.main import app


@pytest.mark.asyncio
async def test_get_campaign_includes_accounts_with_mock_auth():
    from socialmind.api.dependencies import get_campaign_service, get_current_user
    from socialmind.models.account import Account, AccountStatus
    from socialmind.models.platform import Platform
    from socialmind.models.task import Campaign

    mock_platform = MagicMock(spec=Platform)
    mock_platform.id = "platform-1"
    mock_platform.slug = "linkedin"
    mock_platform.display_name = "LinkedIn"

    mock_account = MagicMock(spec=Account)
    mock_account.id = "account-1"
    mock_account.username = "demo-linkedin"
    mock_account.display_name = "Demo LinkedIn Account"
    mock_account.platform_id = "platform-1"
    mock_account.platform = mock_platform
    mock_account.status = AccountStatus.ACTIVE

    mock_campaign = MagicMock(spec=Campaign)
    mock_campaign.id = "campaign-1"
    mock_campaign.name = "LinkedIn Thought Leadership"
    mock_campaign.description = "Test campaign"
    mock_campaign.is_active = True
    mock_campaign.cron_expression = "0 9 * * 1-5"
    mock_campaign.accounts = [mock_account]
    mock_campaign.created_at = datetime.now(timezone.utc)

    mock_service = AsyncMock()
    mock_service.get_campaign = AsyncMock(return_value=mock_campaign)

    app.dependency_overrides[get_current_user] = lambda: "user-123"
    app.dependency_overrides[get_campaign_service] = lambda: mock_service

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.get("/api/v1/campaigns/campaign-1")

        assert response.status_code == 200
        data = response.json()
        assert data["accounts"][0]["username"] == "demo-linkedin"
        assert data["accounts"][0]["platform"]["display_name"] == "LinkedIn"
    finally:
        app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_add_account_to_campaign_dispatches_to_service():
    from socialmind.api.dependencies import get_campaign_service, get_current_user
    from socialmind.models.task import Campaign

    mock_campaign = MagicMock(spec=Campaign)
    mock_campaign.id = "campaign-1"
    mock_campaign.name = "LinkedIn Thought Leadership"
    mock_campaign.description = "Test campaign"
    mock_campaign.is_active = True
    mock_campaign.cron_expression = "0 9 * * 1-5"
    mock_campaign.accounts = []
    mock_campaign.created_at = datetime.now(timezone.utc)

    mock_service = AsyncMock()
    mock_service.add_account = AsyncMock(return_value=mock_campaign)

    app.dependency_overrides[get_current_user] = lambda: "user-123"
    app.dependency_overrides[get_campaign_service] = lambda: mock_service

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            response = await client.post(
                "/api/v1/campaigns/campaign-1/accounts/account-1"
            )

        assert response.status_code == 200
        mock_service.add_account.assert_awaited_once_with("campaign-1", "account-1")
    finally:
        app.dependency_overrides.clear()
