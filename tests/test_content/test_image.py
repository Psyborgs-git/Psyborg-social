from __future__ import annotations

import io

import pytest
from PIL import Image

from socialmind.content.image_processor import ImageProcessor


def _make_image_bytes(width: int = 500, height: int = 500, color=(255, 0, 0)) -> bytes:
    """Create a simple solid-colour JPEG for testing."""
    img = Image.new("RGB", (width, height), color)
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    return buf.getvalue()


def test_resize_for_platform_instagram_feed_square():
    original = _make_image_bytes(500, 500)
    result = ImageProcessor.resize_for_platform(original, "instagram", "feed_square")
    out = Image.open(io.BytesIO(result))
    assert out.size == (1080, 1080)


def test_resize_for_platform_twitter_post():
    original = _make_image_bytes(800, 600)
    result = ImageProcessor.resize_for_platform(original, "twitter", "post")
    out = Image.open(io.BytesIO(result))
    assert out.size == (1200, 675)


def test_resize_for_platform_defaults_to_square_for_unknown_format():
    original = _make_image_bytes(400, 400)
    # "unknown_format" is not defined for instagram — should fall back to 1080x1080
    result = ImageProcessor.resize_for_platform(original, "instagram", "unknown_format")
    out = Image.open(io.BytesIO(result))
    assert out.size == (1080, 1080)


def test_resize_for_platform_unknown_platform_defaults_to_1080():
    original = _make_image_bytes(300, 300)
    result = ImageProcessor.resize_for_platform(original, "mastodon", "post")
    out = Image.open(io.BytesIO(result))
    assert out.size == (1080, 1080)


def test_platform_specs_cover_all_major_platforms():
    expected_platforms = {"instagram", "tiktok", "twitter", "threads", "facebook", "linkedin"}
    assert expected_platforms <= set(ImageProcessor.PLATFORM_SPECS.keys())


def test_resize_returns_jpeg_bytes():
    original = _make_image_bytes(200, 200)
    result = ImageProcessor.resize_for_platform(original, "instagram", "story")
    assert isinstance(result, bytes)
    # JPEG magic bytes
    assert result[:2] == b"\xff\xd8"


def test_get_image_generator_returns_dalle_by_default(monkeypatch):
    from socialmind.content import image as image_mod

    monkeypatch.setattr(image_mod.settings, "IMAGE_PROVIDER", "dalle")
    gen = image_mod.get_image_generator()
    assert isinstance(gen, image_mod.DalleImageGenerator)


def test_get_image_generator_returns_sd_when_configured(monkeypatch):
    from socialmind.content import image as image_mod

    monkeypatch.setattr(image_mod.settings, "IMAGE_PROVIDER", "stable_diffusion")
    gen = image_mod.get_image_generator()
    assert isinstance(gen, image_mod.StableDiffusionGenerator)
