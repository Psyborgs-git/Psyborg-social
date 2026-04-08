from __future__ import annotations

import pytest

from socialmind.adapters.instagram.adapter import InstagramAdapter


class MockAccount:
    id = "acc-123"
    username = "test_user"
    credentials_encrypted = b"encrypted"

    def decrypt_credentials(self):
        return {"password": "testpass", "totp_secret": None}

    class Platform:
        slug = "instagram"

    platform = Platform()


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
    for method_name in (
        "authenticate",
        "post",
        "comment",
        "reply_dm",
        "like",
        "follow",
        "unfollow",
        "get_feed",
        "get_trending",
    ):
        assert hasattr(adapter, method_name)
