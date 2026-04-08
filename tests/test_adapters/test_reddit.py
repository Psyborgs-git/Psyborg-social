from __future__ import annotations

import builtins

import pytest

from socialmind.adapters.reddit.adapter import RedditAdapter


class MockAccount:
    id = "acc-reddit"
    username = "reddit_user"
    email = "reddit_user@example.com"
    platform_user_id = None

    def decrypt_credentials(self):
        return {
            "client_id": "test_client_id",
            "client_secret": "test_client_secret",
            "username": "reddit_user",
            "password": "test_pass",
        }

    class Platform:
        slug = "reddit"

    platform = Platform()


class MockSession:
    cookies = None
    local_storage = None


@pytest.fixture
def adapter():
    return RedditAdapter(
        account=MockAccount(),
        session=MockSession(),
        proxy=None,
    )


def test_adapter_instantiation(adapter):
    assert adapter is not None
    assert adapter.platform_slug == "reddit"


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
async def test_authenticate_returns_false_when_asyncpraw_missing(adapter, monkeypatch):
    real_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "asyncpraw":
            raise ImportError("asyncpraw not installed")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    result = await adapter.authenticate()
    assert result is False


@pytest.mark.asyncio
async def test_post_returns_error_when_not_authenticated(adapter):
    from socialmind.adapters.base import PostContent

    content = PostContent(text="Test post")
    result = await adapter.post(content)
    assert result.success is False
    assert result.error == "Not authenticated"


@pytest.mark.asyncio
async def test_comment_returns_error_when_not_authenticated(adapter):
    result = await adapter.comment("abc123", "Test comment")
    assert result.success is False


@pytest.mark.asyncio
async def test_like_returns_false_when_not_authenticated(adapter):
    result = await adapter.like("abc123")
    assert result is False


@pytest.mark.asyncio
async def test_follow_returns_false_when_not_authenticated(adapter):
    result = await adapter.follow("python")
    assert result is False


@pytest.mark.asyncio
async def test_unfollow_returns_false_when_not_authenticated(adapter):
    result = await adapter.unfollow("python")
    assert result is False


@pytest.mark.asyncio
async def test_reply_dm_returns_false_when_not_authenticated(adapter):
    result = await adapter.reply_dm("dm123", "Hello")
    assert result is False


@pytest.mark.asyncio
async def test_get_feed_returns_empty_when_not_authenticated(adapter):
    result = await adapter.get_feed()
    assert result == []


@pytest.mark.asyncio
async def test_get_dms_returns_empty_when_not_authenticated(adapter):
    result = await adapter.get_dms()
    assert result == []


@pytest.mark.asyncio
async def test_get_dm_history_returns_empty_when_not_authenticated(adapter):
    result = await adapter.get_dm_history("thread123")
    assert result == []


@pytest.mark.asyncio
async def test_search_returns_empty_when_not_authenticated(adapter):
    result = await adapter.search("python")
    assert result == []


@pytest.mark.asyncio
async def test_get_trending_returns_empty_when_not_authenticated(adapter):
    result = await adapter.get_trending("python")
    assert result == []
