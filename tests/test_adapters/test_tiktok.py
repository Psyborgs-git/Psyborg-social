from __future__ import annotations

import pytest

from socialmind.adapters.tiktok.adapter import TikTokAdapter


class MockAccount:
    id = "acc-tiktok"
    username = "tiktok_user"
    email = "tiktok_user@example.com"

    def decrypt_credentials(self):
        return {"username": "tiktok_user", "password": "test_pass"}

    class Platform:
        slug = "tiktok"

    platform = Platform()


class MockSession:
    cookies = None
    local_storage = None


@pytest.fixture
def adapter():
    return TikTokAdapter(
        account=MockAccount(),
        session=MockSession(),
        proxy=None,
    )


def test_adapter_instantiation(adapter):
    assert adapter is not None
    assert adapter.platform_slug == "tiktok"


def test_adapter_has_required_methods(adapter):
    for method_name in (
        "authenticate",
        "post",
        "comment",
        "reply_dm",
        "like",
        "follow",
        "unfollow",
        "get_feed",
        "get_dms",
        "get_dm_history",
        "search",
        "get_trending",
    ):
        assert hasattr(adapter, method_name)


@pytest.mark.asyncio
async def test_post_requires_media_url(adapter):
    from socialmind.adapters.base import PostContent

    content = PostContent(text="No video here")
    result = await adapter.post(content)
    assert result.success is False
    assert "video" in result.error.lower()


@pytest.mark.asyncio
async def test_get_dms_returns_empty_list(adapter):
    result = await adapter.get_dms()
    assert result == []


@pytest.mark.asyncio
async def test_get_dm_history_returns_empty_list(adapter):
    result = await adapter.get_dm_history("thread123")
    assert result == []


def test_tiktok_headers_are_valid(adapter):
    headers = adapter._get_tiktok_headers()
    assert "User-Agent" in headers
    assert "Referer" in headers
    assert headers["Referer"] == "https://www.tiktok.com/"
