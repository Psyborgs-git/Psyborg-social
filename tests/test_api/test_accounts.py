from __future__ import annotations

import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, MagicMock

from socialmind.api.main import app


@pytest.mark.asyncio
async def test_health_check():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_list_accounts_requires_auth():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/accounts/")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_list_accounts_with_mock_auth():
    from socialmind.api.dependencies import get_current_user, get_account_service
    from socialmind.models.account import Account, AccountStatus

    mock_account = MagicMock(spec=Account)
    mock_account.id = "acc-1"
    mock_account.username = "testuser"
    mock_account.platform_id = "instagram"
    mock_account.status = AccountStatus.ACTIVE
    mock_account.display_name = None
    mock_account.daily_action_limit = 100
    mock_account.warmup_phase = False

    from datetime import datetime, timezone
    mock_account.created_at = datetime.now(timezone.utc)

    mock_service = AsyncMock()
    mock_service.list_accounts = AsyncMock(return_value=[mock_account])

    app.dependency_overrides[get_current_user] = lambda: "user-123"
    app.dependency_overrides[get_account_service] = lambda: mock_service

    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/api/v1/accounts/")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    finally:
        app.dependency_overrides.clear()
