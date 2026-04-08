from __future__ import annotations

import io

from PIL import Image, ImageDraw, ImageFont


class ImageProcessor:
    PLATFORM_SPECS: dict[str, dict[str, tuple[int, int]]] = {
        "instagram": {
            "feed_square": (1080, 1080),
            "feed_portrait": (1080, 1350),
            "feed_landscape": (1080, 566),
            "story": (1080, 1920),
            "reel": (1080, 1920),
        },
        "tiktok": {
            "video_cover": (1080, 1920),
        },
        "twitter": {
            "post": (1200, 675),
        },
        "threads": {
            "post": (1080, 1080),
        },
        "facebook": {
            "post": (1200, 630),
            "story": (1080, 1920),
        },
        "linkedin": {
            "post": (1200, 627),
        },
    }

    @staticmethod
    def resize_for_platform(
        image_bytes: bytes,
        platform: str,
        format: str = "feed_square",
    ) -> bytes:
        """Resize and crop an image to the platform's required dimensions."""
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        specs = ImageProcessor.PLATFORM_SPECS.get(platform, {})
        target = specs.get(format, (1080, 1080))
        resized = ImageProcessor._smart_crop(img, target)
        output = io.BytesIO()
        resized.save(output, format="JPEG", quality=92, optimize=True)
        return output.getvalue()

    @staticmethod
    def _smart_crop(img: Image.Image, target: tuple[int, int]) -> Image.Image:
        """Crop from center then resize — preserves the subject."""
        tw, th = target
        iw, ih = img.size
        scale = max(tw / iw, th / ih)
        new_size = (int(iw * scale), int(ih * scale))
        img = img.resize(new_size, Image.LANCZOS)
        left = (img.width - tw) // 2
        top = (img.height - th) // 2
        return img.crop((left, top, left + tw, top + th))

    @staticmethod
    def add_text_overlay(
        image_bytes: bytes,
        text: str,
        position: str = "bottom",
        font_size: int = 48,
    ) -> bytes:
        """Overlay a semi-transparent text bar on the image."""
        img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        bar_height = font_size + 40
        if position == "bottom":
            bar_y = img.height - bar_height
        else:
            bar_y = 0

        for y in range(bar_height):
            if position == "bottom":
                alpha = int(180 * (y / bar_height))
            else:
                alpha = int(180 * (1 - y / bar_height))
            draw.rectangle(
                [(0, bar_y + y), (img.width, bar_y + y + 1)],
                fill=(0, 0, 0, alpha),
            )

        try:
            font = ImageFont.truetype(
                "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size
            )
        except OSError:
            font = ImageFont.load_default()

        text_y = bar_y + 20
        draw.text((40, text_y), text, font=font, fill=(255, 255, 255, 255))

        combined = Image.alpha_composite(img, overlay)
        output = io.BytesIO()
        combined.convert("RGB").save(output, format="JPEG", quality=92)
        return output.getvalue()

    @staticmethod
    def add_watermark(image_bytes: bytes, watermark_text: str) -> bytes:
        """Add a subtle watermark in the lower-right corner."""
        img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        font = ImageFont.load_default()
        draw.text(
            (img.width - 120, img.height - 30),
            watermark_text,
            fill=(255, 255, 255, 100),
            font=font,
        )
        combined = Image.alpha_composite(img, overlay)
        output = io.BytesIO()
        combined.convert("RGB").save(output, format="JPEG", quality=90)
        return output.getvalue()
