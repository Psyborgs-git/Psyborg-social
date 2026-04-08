from __future__ import annotations

from types import SimpleNamespace

import pytest

from socialmind.mcp.tools.research_tools import _normalize_platform, _resolve_account


def _account(
    *, account_id: str, username: str, status: str = "active", platform: str = "twitter"
):
    return SimpleNamespace(
        id=account_id,
        username=username,
        status=status,
        platform=SimpleNamespace(slug=platform),
    )


class FakeAccountService:
    def __init__(self, *, accounts=None, account_by_id=None):
        self.accounts = accounts or []
        self.account_by_id = account_by_id or {}
        self.list_calls: list[tuple[str | None, str | None]] = []

    async def list_accounts(
        self, platform: str | None = None, status: str | None = None
    ):
        self.list_calls.append((platform, status))
        return self.accounts

    async def get_account(self, account_id: str):
        if account_id not in self.account_by_id:
            raise ValueError(f"Account {account_id} not found")
        return self.account_by_id[account_id]


def test_normalize_platform_maps_x_aliases():
    assert _normalize_platform("x") == "twitter"
    assert _normalize_platform("X.com") == "twitter"
    assert _normalize_platform("twitter") == "twitter"
    assert _normalize_platform(None) is None


@pytest.mark.asyncio
async def test_resolve_account_matches_username_on_normalized_platform():
    service = FakeAccountService(
        accounts=[
            _account(account_id="1", username="someoneelse"),
            _account(account_id="2", username="parodyofgod"),
        ]
    )

    account, normalized_platform, resolve_error = await _resolve_account(
        service,
        platform="x",
        username="ParodyOfGod",
    )

    assert account is not None
    assert account.id == "2"
    assert normalized_platform == "twitter"
    assert resolve_error is None
    assert service.list_calls == [("twitter", "active")]


@pytest.mark.asyncio
async def test_resolve_account_returns_error_for_missing_username():
    service = FakeAccountService(
        accounts=[_account(account_id="1", username="someoneelse")]
    )

    account, normalized_platform, resolve_error = await _resolve_account(
        service,
        platform="twitter",
        username="parodyofgod",
    )

    assert account is None
    assert normalized_platform == "twitter"
    assert resolve_error == "No active account found for username parodyofgod"


@pytest.mark.asyncio
async def test_resolve_account_validates_selected_account_id():
    service = FakeAccountService(
        account_by_id={
            "acct-1": _account(
                account_id="acct-1", username="parodyofgod", status="paused"
            ),
        }
    )

    account, normalized_platform, resolve_error = await _resolve_account(
        service,
        platform="x",
        account_id="acct-1",
        username="parodyofgod",
    )

    assert account is None
    assert normalized_platform == "twitter"
    assert resolve_error == "Account acct-1 is not active"
