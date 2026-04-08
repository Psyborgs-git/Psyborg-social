from __future__ import annotations

import builtins

import pytest

from socialmind.adapters.youtube.adapter import YouTubeAdapter


class MockAccount:
    id = "acc-youtube"
    username = "yt_channel"
    email = "yt_channel@example.com"

    def decrypt_credentials(self):
        return {}

    class Platform:
        slug = "youtube"

    platform = Platform()


class MockSession:
    cookies = None
    local_storage = None
    api_tokens = None


@pytest.fixture
def adapter():
    return YouTubeAdapter(
        account=MockAccount(),
        session=MockSession(),
        proxy=None,
    )


def test_adapter_instantiation(adapter):
    assert adapter is not None
    assert adapter.platform_slug == "youtube"


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
async def test_authenticate_returns_false_when_google_api_missing(adapter, monkeypatch):
    real_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name.startswith("google"):
            raise ImportError("google-api-python-client not installed")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    result = await adapter.authenticate()
    assert result is False


@pytest.mark.asyncio
async def test_authenticate_returns_false_with_no_tokens(adapter):
    # No session tokens and no google library installed in test environment
    result = await adapter.authenticate()
    assert result is False


@pytest.mark.asyncio
async def test_post_returns_error_when_not_authenticated(adapter):
    from socialmind.adapters.base import PostContent

    content = PostContent(text="Test video description", post_type="short")
    result = await adapter.post(content)
    assert result.success is False


@pytest.mark.asyncio
async def test_get_dms_returns_empty_list(adapter):
    result = await adapter.get_dms()
    assert result == []


@pytest.mark.asyncio
async def test_get_dm_history_returns_empty_list(adapter):
    result = await adapter.get_dm_history("thread123")
    assert result == []


@pytest.mark.asyncio
async def test_reply_dm_returns_false(adapter):
    result = await adapter.reply_dm("conv123", "Hello")
    assert result is False
