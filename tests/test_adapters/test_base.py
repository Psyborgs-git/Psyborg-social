from __future__ import annotations

import pytest

from socialmind.adapters.base import BasePlatformAdapter, PostContent, PostResult
from socialmind.adapters.registry import ADAPTER_REGISTRY, get_adapter


def test_adapter_registry_has_all_platforms():
    expected = {
        "instagram",
        "tiktok",
        "reddit",
        "youtube",
        "facebook",
        "twitter",
        "threads",
        "linkedin",
    }
    assert set(ADAPTER_REGISTRY.keys()) == expected


def test_all_registry_values_are_adapter_subclasses():
    for name, cls in ADAPTER_REGISTRY.items():
        assert issubclass(cls, BasePlatformAdapter), f"{name} is not a BasePlatformAdapter subclass"


def test_get_adapter_raises_for_unknown_platform():
    class MockPlatform:
        slug = "unknown_platform"

    class MockAccount:
        platform = MockPlatform()

    with pytest.raises(ValueError, match="No adapter registered"):
        get_adapter(MockAccount(), None, None)


def test_post_content_defaults():
    pc = PostContent(text="Hello world")
    assert pc.media_urls == []
    assert pc.hashtags == []
    assert pc.post_type == "feed"


def test_post_result_defaults():
    pr = PostResult(success=True)
    assert pr.platform_post_id is None
    assert pr.adapter_used == "api"
