from __future__ import annotations

import builtins

import pytest
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from socialmind.adapters.twitter.adapter import TwitterAdapter


class MockAccount:
    id = "acc-twitter"
    username = "parodyofgod"
    email = "parodyofgod@example.com"

    def decrypt_credentials(self):
        return {
            "username": "parodyofgod",
            "password": "super-secret",
        }

    class Platform:
        slug = "twitter"

    platform = Platform()


class MockSession:
    cookies = None
    local_storage = None


@pytest.fixture
def adapter():
    return TwitterAdapter(
        account=MockAccount(),
        session=MockSession(),
        proxy=None,
    )


@pytest.mark.asyncio
async def test_authenticate_api_returns_false_when_async_tweepy_extras_missing(
    adapter, monkeypatch
):
    real_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "tweepy.asynchronous":
            raise RuntimeError("missing async extras")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    assert await adapter._authenticate_api() is False


@pytest.mark.asyncio
async def test_wait_for_page_ready_ignores_networkidle_timeout(adapter):
    class FakePage:
        async def wait_for_load_state(self, state: str, timeout: int):
            raise PlaywrightTimeoutError("still busy")

    await adapter._wait_for_page_ready(FakePage(), timeout=1234)
