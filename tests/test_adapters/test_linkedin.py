from __future__ import annotations

import pytest

from socialmind.adapters.linkedin.adapter import LinkedInAdapter


class MockAccount:
    id = "acc-linkedin"
    username = "person@example.com"
    email = "person@example.com"

    def decrypt_credentials(self):
        return {"password": "testpass"}

    class Platform:
        slug = "linkedin"

    platform = Platform()


class MockSession:
    cookies = None


@pytest.fixture
def adapter():
    return LinkedInAdapter(
        account=MockAccount(),
        session=MockSession(),
        proxy=None,
    )


def test_adapter_instantiation(adapter):
    assert adapter is not None
    assert adapter.platform_slug == "linkedin"


def test_adapter_has_required_methods(adapter):
    for method_name in (
        "authenticate",
        "post",
        "comment",
        "reply_dm",
        "like",
        "follow",
        "unfollow",
        "search",
        "get_trending",
    ):
        assert hasattr(adapter, method_name)
