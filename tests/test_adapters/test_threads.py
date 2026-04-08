from __future__ import annotations

import builtins

import pytest

from socialmind.adapters.threads.adapter import ThreadsAdapter


class MockAccount:
    id = "acc-threads"
    username = "threads_user"
    email = "threads_user@example.com"

    def decrypt_credentials(self):
        return {"username": "threads_user", "password": "test_pass"}

    class Platform:
        slug = "threads"

    platform = Platform()


class MockSession:
    cookies = None
    local_storage = None
    api_tokens = None


@pytest.fixture
def adapter():
    return ThreadsAdapter(
        account=MockAccount(),
        session=MockSession(),
        proxy=None,
    )


def test_adapter_instantiation(adapter):
    assert adapter is not None
    assert adapter.platform_slug == "threads"


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
async def test_authenticate_returns_false_when_instagrapi_missing(adapter, monkeypatch):
    real_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "instagrapi":
            raise ImportError("instagrapi not installed")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    result = await adapter.authenticate()
    assert result is False


@pytest.mark.asyncio
async def test_post_returns_error_when_not_authenticated(adapter):
    from socialmind.adapters.base import PostContent

    content = PostContent(text="Hello from Threads!")
    result = await adapter.post(content)
    assert result.success is False
    assert result.error == "Not authenticated"


@pytest.mark.asyncio
async def test_comment_returns_error_when_not_authenticated(adapter):
    result = await adapter.comment("media123", "Great post!")
    assert result.success is False


@pytest.mark.asyncio
async def test_like_returns_false_when_not_authenticated(adapter):
    result = await adapter.like("media123")
    assert result is False


@pytest.mark.asyncio
async def test_follow_returns_false_when_not_authenticated(adapter):
    result = await adapter.follow("user123")
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
async def test_search_returns_empty_when_not_authenticated(adapter):
    result = await adapter.search("python")
    assert result == []
