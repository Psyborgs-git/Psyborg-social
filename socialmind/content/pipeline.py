from __future__ import annotations

from typing import TYPE_CHECKING

from socialmind.adapters.base import PostContent, TrendingItem
from socialmind.ai.modules.content import PostGenerator
from socialmind.config.settings import settings
from socialmind.content.image import get_image_generator
from socialmind.content.image_processor import ImageProcessor
from socialmind.content.media_store import MediaStore

if TYPE_CHECKING:
    from socialmind.models.account import Account
    from socialmind.models.task import Task


async def generate_full_post_content(
    account: Account,
    task: Task,
    trends: list[TrendingItem],
) -> PostContent:
    """Orchestrate the full content generation pipeline."""
    if account.persona is None:
        return PostContent(text="")

    generator = PostGenerator()
    post_content = generator(
        platform=account.platform.slug,
        persona=account.persona,
        topic=task.config.get("prompt", ""),
        trends=trends,
    )

    image_prompt = post_content.metadata.get("image_prompt", "")
    if task.config.get("include_image", True) and image_prompt:
        generator_engine = get_image_generator()
        raw_image = await generator_engine.generate(image_prompt)

        image_format = task.config.get("image_format", "feed_square")
        processed = ImageProcessor.resize_for_platform(
            raw_image,
            platform=account.platform.slug,
            format=image_format,
        )

        store = MediaStore()
        media_url = await store.upload(
            data=processed,
            filename="post_image.jpg",
            content_type="image/jpeg",
            account_id=account.id,
        )

        from socialmind.models.media import MediaAsset, MediaType

        asset = MediaAsset(
            media_type=MediaType.IMAGE,
            filename="post_image.jpg",
            storage_key=media_url,
            generated_by=settings.IMAGE_PROVIDER,
            generation_prompt=image_prompt,
        )
        _ = asset  # caller can persist if needed
        post_content.media_urls = [media_url]

    return post_content

