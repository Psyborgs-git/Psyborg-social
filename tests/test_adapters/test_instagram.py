from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from socialmind.adapters.instagram.adapter import InstagramAdapter
from socialmind.adapters.base import PostContent, PostResult


class MockAccount:
    id = "acc-123"
    username = "test_user"
    credentials_encrypted = b"encrypted"

    def decrypt_credentials(self):
        return {"password": "testpass", "totp_secret": None}

    class platform:
        slug = "instagram"


class MockSession:
    cookies = None
    local_storage = None


class MockProxy:
    url = "socks5://proxy:1080"


@pytest.fixture
def adapter():
    return InstagramAdapter(
        account=MockAccount(),
        session=MockSession(),
        proxy=None,
    )


def test_adapter_instantiation(adapter):
    assert adapter is not None


def test_adapter_has_required_methods(adapter):
    assert hasattr(adapter, "post")
    assert hasattr(adapter, "engage_feed")
    assert hasattr(adapter, "get_trending")
