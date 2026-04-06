from __future__ import annotations

import base64
from abc import ABC, abstractmethod

import httpx

from socialmind.config.settings import settings


class ImageGenerator(ABC):
    @abstractmethod
    async def generate(self, prompt: str, size: str = "1024x1024") -> bytes:
        """Return raw image bytes for the given prompt."""
        ...


class DalleImageGenerator(ImageGenerator):
    """DALL-E 3 via OpenAI API — best quality, cloud-based."""

    async def generate(self, prompt: str, size: str = "1024x1024") -> bytes:
        from openai import AsyncOpenAI

        client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        enhanced = (
            f"{prompt}, high quality, social media ready, professional photography style"
        )
        response = await client.images.generate(
            model="dall-e-3",
            prompt=enhanced,
            size=size,  # type: ignore[arg-type]
            quality="standard",
            n=1,
        )
        image_url = response.data[0].url
        if not image_url:
            raise ValueError("DALL-E returned no image URL")
        async with httpx.AsyncClient(timeout=60.0) as http_client:
            resp = await http_client.get(image_url)
            resp.raise_for_status()
            return resp.content


class StableDiffusionGenerator(ImageGenerator):
    """Local Stable Diffusion via ComfyUI or automatic1111 API."""

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
        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{settings.SD_API_URL}/sdapi/v1/txt2img", json=payload
            )
            resp.raise_for_status()
            data = resp.json()
            return base64.b64decode(data["images"][0])


def get_image_generator() -> ImageGenerator:
    """Return the configured image generator."""
    if settings.IMAGE_PROVIDER == "stable_diffusion":
        return StableDiffusionGenerator()
    return DalleImageGenerator()

