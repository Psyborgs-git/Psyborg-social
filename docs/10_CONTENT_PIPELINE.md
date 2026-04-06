# Content Pipeline

The content pipeline handles everything related to generating, processing, transforming, and storing media assets — images, videos, text, and audio — before they're handed to platform adapters for publishing.

---

## Overview

```
Content Request
    │
    ├── Text Generation ──── DSPy Pipeline ──────────────────────────────┐
    │                                                                     │
    ├── Image Generation ─── AI Generator ──► Image Processor ───────────┤
    │                        (DALL-E / SD)     (Pillow/resize/watermark)  │
    │                                                                     │
    ├── Video Processing ─── FFmpeg / MoviePy ────────────────────────────┤
    │                        (trim, transcode, overlay, audio)            │
    │                                                                     │
    └── Downloaded Media ─── yt-dlp / httpx ──► Media Store (MinIO) ─────┘
                                                                          │
                                                                     PostContent
                                                                    (with media_urls)
                                                                          │
                                                               Platform Adapter → Publish
```

---

## Media Storage (MinIO)

All media assets are stored in MinIO (S3-compatible, self-hosted) before being uploaded to platforms. This decouples media generation from publishing and allows retry without re-generating.

```python
# socialmind/content/media_store.py
from miniopy_async import Minio
import aiofiles
import tempfile

class MediaStore:
    BUCKET = "socialmind"

    def __init__(self):
        self._client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )

    async def upload(
        self,
        data: bytes,
        filename: str,
        content_type: str,
        account_id: str,
    ) -> str:
        """Upload media and return the internal URL."""
        key = f"accounts/{account_id}/media/{uuid4()}/{filename}"
        await self._client.put_object(
            self.BUCKET, key, io.BytesIO(data), len(data),
            content_type=content_type,
        )
        return f"minio://{self.BUCKET}/{key}"

    async def download_to_temp(self, minio_url: str) -> str:
        """Download to a temp file and return the local path."""
        bucket, key = self._parse_url(minio_url)
        suffix = Path(key).suffix
        tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        response = await self._client.get_object(bucket, key)
        async with aiofiles.open(tmp.name, "wb") as f:
            async for chunk in response.content.iter_chunked(8192):
                await f.write(chunk)
        return tmp.name

    async def get_public_url(self, minio_url: str, expires: int = 3600) -> str:
        """Generate a presigned URL for temporary public access."""
        bucket, key = self._parse_url(minio_url)
        return await self._client.presigned_get_object(bucket, key, expires=timedelta(seconds=expires))
```

---

## Image Generation

### Provider Abstraction

```python
# socialmind/content/image.py
from abc import ABC, abstractmethod

class ImageGenerator(ABC):
    @abstractmethod
    async def generate(self, prompt: str, size: str = "1024x1024") -> bytes:
        """Returns raw image bytes."""
        ...

class DalleImageGenerator(ImageGenerator):
    """DALL-E 3 via OpenAI API — best quality, cloud-based."""
    async def generate(self, prompt: str, size: str = "1024x1024") -> bytes:
        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        enhanced = f"{prompt}, high quality, social media ready, professional photography style"
        response = await client.images.generate(
            model="dall-e-3",
            prompt=enhanced,
            size=size,
            quality="standard",
            n=1,
        )
        image_url = response.data[0].url
        async with httpx.AsyncClient() as client:
            resp = await client.get(image_url)
            return resp.content

class StableDiffusionGenerator(ImageGenerator):
    """Local Stable Diffusion via ComfyUI or automatic1111 API — free, GPU required."""
    async def generate(self, prompt: str, size: str = "1024x1024") -> bytes:
        w, h = map(int, size.split("x"))
        payload = {
            "prompt": prompt,
            "negative_prompt": "blurry, low quality, watermark, text, logo",
            "width": w,
            "height": h,
            "steps": 25,
            "cfg_scale": 7,
            "sampler_name": "DPM++ 2M Karras",
        }
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(f"{settings.SD_API_URL}/sdapi/v1/txt2img", json=payload)
            data = resp.json()
            return base64.b64decode(data["images"][0])

class OllamaVisionGenerator(ImageGenerator):
    """Use Ollama with a multimodal model for image understanding (not generation)."""
    # Ollama doesn't generate images — use DALL-E or SD for generation
    pass


def get_image_generator() -> ImageGenerator:
    if settings.IMAGE_PROVIDER == "dalle":
        return DalleImageGenerator()
    elif settings.IMAGE_PROVIDER == "stable_diffusion":
        return StableDiffusionGenerator()
    else:
        return DalleImageGenerator()  # Default
```

### Image Processing

After generation, images are processed to meet platform specifications:

```python
# socialmind/content/image_processor.py
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import io

class ImageProcessor:

    PLATFORM_SPECS = {
        "instagram": {
            "feed_square":    (1080, 1080),
            "feed_portrait":  (1080, 1350),
            "feed_landscape": (1080, 566),
            "story":          (1080, 1920),
            "reel":           (1080, 1920),
        },
        "tiktok": {
            "video_cover":    (1080, 1920),
        },
        "twitter": {
            "post":           (1200, 675),
        },
        "threads": {
            "post":           (1080, 1080),
        },
        "facebook": {
            "post":           (1200, 630),
            "story":          (1080, 1920),
        },
    }

    @staticmethod
    def resize_for_platform(image_bytes: bytes, platform: str, format: str = "feed_square") -> bytes:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        target = ImageProcessor.PLATFORM_SPECS[platform][format]
        resized = ImageProcessor._smart_crop(img, target)
        output = io.BytesIO()
        resized.save(output, format="JPEG", quality=92, optimize=True)
        return output.getvalue()

    @staticmethod
    def _smart_crop(img: Image.Image, target: tuple[int, int]) -> Image.Image:
        """Crop from center, then resize — preserves subject."""
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
        img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)

        # Semi-transparent gradient bar
        bar_height = font_size + 40
        if position == "bottom":
            bar_y = img.height - bar_height
        else:
            bar_y = 0

        for y in range(bar_height):
            alpha = int(180 * (y / bar_height)) if position == "bottom" else int(180 * (1 - y / bar_height))
            draw.rectangle([(0, bar_y + y), (img.width, bar_y + y + 1)], fill=(0, 0, 0, alpha))

        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
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
        img = Image.open(io.BytesIO(image_bytes)).convert("RGBA")
        overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        font = ImageFont.load_default()
        draw.text((img.width - 120, img.height - 30), watermark_text, fill=(255, 255, 255, 100), font=font)
        combined = Image.alpha_composite(img, overlay)
        output = io.BytesIO()
        combined.convert("RGB").save(output, format="JPEG", quality=90)
        return output.getvalue()
```

---

## Video Processing

```python
# socialmind/content/video.py
import ffmpeg
import subprocess
from moviepy.editor import VideoFileClip, TextClip, CompositeVideoClip, AudioFileClip

class VideoProcessor:

    @staticmethod
    async def transcode_for_platform(input_path: str, platform: str) -> str:
        """Transcode video to platform-required specs."""
        specs = {
            "instagram_reel": {"width": 1080, "height": 1920, "fps": 30, "bitrate": "4M", "max_seconds": 90},
            "tiktok":         {"width": 1080, "height": 1920, "fps": 30, "bitrate": "4M", "max_seconds": 180},
            "youtube_short":  {"width": 1080, "height": 1920, "fps": 60, "bitrate": "8M", "max_seconds": 60},
            "twitter":        {"width": 1280, "height": 720,  "fps": 30, "bitrate": "2M", "max_seconds": 140},
        }
        spec = specs[platform]
        output_path = f"{input_path}_transcoded.mp4"

        (
            ffmpeg
            .input(input_path, ss=0, t=spec["max_seconds"])
            .filter("scale", spec["width"], spec["height"], force_original_aspect_ratio="decrease")
            .filter("pad", spec["width"], spec["height"], "(ow-iw)/2", "(oh-ih)/2")
            .output(
                output_path,
                vcodec="libx264",
                acodec="aac",
                video_bitrate=spec["bitrate"],
                r=spec["fps"],
                preset="fast",
                movflags="+faststart",  # Web-optimized
            )
            .overwrite_output()
            .run(quiet=True)
        )
        return output_path

    @staticmethod
    async def add_captions(video_path: str, captions: list[dict]) -> str:
        """Add timed text captions to a video."""
        clip = VideoFileClip(video_path)
        text_clips = []
        for caption in captions:
            txt = (
                TextClip(caption["text"], fontsize=50, color="white", stroke_color="black", stroke_width=2)
                .set_position(("center", "bottom"))
                .set_start(caption["start"])
                .set_end(caption["end"])
            )
            text_clips.append(txt)

        final = CompositeVideoClip([clip] + text_clips)
        output_path = video_path.replace(".mp4", "_captioned.mp4")
        final.write_videofile(output_path, codec="libx264", audio_codec="aac", logger=None)
        return output_path

    @staticmethod
    async def create_slideshow(image_paths: list[str], duration_per_image: float = 3.0, audio_path: str | None = None) -> str:
        """Create a video slideshow from multiple images — useful for carousels as reels."""
        # Build ffmpeg filter complex for slideshow
        inputs = [ffmpeg.input(img, loop=1, t=duration_per_image) for img in image_paths]
        total_duration = len(image_paths) * duration_per_image
        output_path = f"/tmp/slideshow_{uuid4()}.mp4"

        joined = ffmpeg.concat(*inputs, v=1, a=0).node
        stream = joined[0]

        if audio_path:
            audio = ffmpeg.input(audio_path, t=total_duration)
            out = ffmpeg.output(stream, audio.audio, output_path, vcodec="libx264", acodec="aac")
        else:
            out = ffmpeg.output(stream, output_path, vcodec="libx264")

        out.overwrite_output().run(quiet=True)
        return output_path
```

---

## Content Download (Research Pipeline)

```python
# socialmind/content/downloader.py
import yt_dlp

class ContentDownloader:
    """Download reference content for research or remixing."""

    @staticmethod
    async def download_youtube(url: str, format: str = "mp4") -> str:
        """Download a YouTube video for research or as B-roll."""
        output_template = f"/tmp/yt_%(id)s.%(ext)s"
        ydl_opts = {
            "format": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
            "outtmpl": output_template,
            "quiet": True,
            "no_warnings": True,
            "cookiefile": None,  # Add cookie file for age-restricted content
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            return ydl.prepare_filename(info)

    @staticmethod
    async def extract_audio(video_path: str) -> str:
        """Extract audio from a video for repurposing."""
        audio_path = video_path.replace(".mp4", ".mp3")
        (
            ffmpeg
            .input(video_path)
            .output(audio_path, acodec="libmp3lame", ab="192k")
            .overwrite_output()
            .run(quiet=True)
        )
        return audio_path
```

---

## Content Variation Engine

To avoid repetitive content patterns that trigger platform detection, the pipeline deliberately varies output:

```python
# socialmind/content/variation.py
import random

HOOKS = [
    "Did you know that",
    "The truth about",
    "Stop doing this if you want",
    "Why most people fail at",
    "This changed everything for me:",
    "Unpopular opinion:",
    "What nobody tells you about",
]

CTAS = [
    "Drop a 🔥 if you agree",
    "What do you think? Comment below",
    "Tag someone who needs to see this",
    "Save this for later",
    "Follow for more tips like this",
    "Share with a friend who needs this",
]

class ContentVariationEngine:
    """Adds variation signals to DSPy prompts to prevent repetitive output."""

    @staticmethod
    def get_variation_context(account_id: str, post_number: int) -> dict:
        """Return variation hints for the DSPy post generator."""
        rng = random.Random(f"{account_id}-{post_number}")
        return {
            "suggested_hook": rng.choice(HOOKS),
            "suggested_cta": rng.choice(CTAS),
            "format": rng.choice(["list", "story", "opinion", "question", "tip"]),
            "opening_style": rng.choice(["question", "statement", "stat", "anecdote"]),
        }

    @staticmethod
    def get_post_number(account_id: str, db_session) -> int:
        """Count how many posts this account has made (for seeding variation)."""
        # Query PostRecord count for this account
        return db_session.execute(
            select(func.count()).where(PostRecord.account_id == account_id)
        ).scalar()
```

---

## Full Content Generation Flow

```python
# socialmind/content/pipeline.py

async def generate_full_post_content(
    account: Account,
    task: Task,
    trends: list[TrendingItem],
) -> PostContent:
    """Orchestrate the full content generation pipeline."""

    # 1. Generate text via DSPy
    generator = PostGenerator()
    post_content = generator(
        platform=account.platform.slug,
        persona=account.persona,
        topic=task.config.get("prompt", ""),
        trends=trends,
    )

    # 2. Generate image if requested
    if task.config.get("include_image", True) and post_content.image_prompt:
        generator_engine = get_image_generator()
        raw_image = await generator_engine.generate(post_content.image_prompt)

        # Process for platform specs
        processed = ImageProcessor.resize_for_platform(
            raw_image,
            platform=account.platform.slug,
            format=task.config.get("image_format", "feed_square"),
        )

        # Store in MinIO
        store = MediaStore()
        media_url = await store.upload(
            data=processed,
            filename="post_image.jpg",
            content_type="image/jpeg",
            account_id=account.id,
        )

        # Record in DB
        asset = MediaAsset(
            media_type=MediaType.IMAGE,
            filename="post_image.jpg",
            storage_key=media_url,
            generated_by=settings.IMAGE_PROVIDER,
            generation_prompt=post_content.image_prompt,
        )
        post_content.media_urls = [media_url]

    return post_content
```
