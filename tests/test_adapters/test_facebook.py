from __future__ import annotations

import pytest

from socialmind.adapters.facebook.adapter import FacebookAdapter


class MockAccount:
    id = "acc-facebook"
    username = "fb_user"
    email = "fb_user@example.com"

    def decrypt_credentials(self):
        return {"email": "fb_user@example.com", "password": "test_pass"}

    class Platform:
        slug = "facebook"

    platform = Platform()


class MockSession:
    cookies = None
    local_storage = None


@pytest.fixture
def adapter():
    return FacebookAdapter(
        account=MockAccount(),
        session=MockSession(),
        proxy=None,
    )


def test_adapter_instantiation(adapter):
    assert adapter is not None
    assert adapter.platform_slug == "facebook"


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
async def test_get_feed_returns_empty_list(adapter):
    # Facebook get_feed is a stub (browser scraping complexity)
    result = await adapter.get_feed()
    assert result == []


@pytest.mark.asyncio
async def test_get_dms_returns_empty_list(adapter):
    result = await adapter.get_dms()
    assert result == []


@pytest.mark.asyncio
async def test_get_dm_history_returns_empty_list(adapter):
    result = await adapter.get_dm_history("thread123")
    assert result == []


@pytest.mark.asyncio
async def test_get_trending_returns_empty_list(adapter):
    result = await adapter.get_trending("tech")
    assert result == []


def test_build_caption_combines_text_hashtags_mentions(adapter):
    from socialmind.adapters.base import PostContent

    content = PostContent(
        text="Hello world",
        hashtags=["python", "coding"],
        mentions=["alice"],
    )
    caption = adapter._build_caption(content)
    assert "Hello world" in caption
    assert "#python" in caption
    assert "#coding" in caption
    assert "@alice" in caption
