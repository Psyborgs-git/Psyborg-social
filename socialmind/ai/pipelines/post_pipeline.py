from __future__ import annotations

import asyncio
import random
from typing import TYPE_CHECKING

from socialmind.adapters.base import PostResult
from socialmind.ai.modules.content import DMResponder, PostGenerator, TrendResearcher

if TYPE_CHECKING:
    from socialmind.adapters.base import BasePlatformAdapter
    from socialmind.models.account import Account
    from socialmind.models.task import Task


class PostCampaignPipeline:
    """
    Full pipeline: research trends → generate content → generate image → publish.
    Used by Celery tasks for scheduled posts.
    """

    def __init__(self) -> None:
        self.researcher = TrendResearcher()
        self.generator = PostGenerator()
        self.dm_responder = DMResponder()

    async def run_post(
        self,
        account: Account,
        task: Task,
        adapter: BasePlatformAdapter,
    ) -> PostResult:
        """Research trends, generate content, optionally generate image, then publish."""
        if account.persona is None:
            return PostResult(success=False, error="Account has no persona configured")

        trending = await adapter.get_trending(
            niche=account.persona.niche,
            limit=20,
        )

        trend_report = self.researcher(
            platform=account.platform.slug,
            niche=account.persona.niche,
            trending_items=trending,
        )

        topic = task.config.get("prompt") or (
            trend_report.content_ideas[0] if trend_report.content_ideas else ""
        )

        post_content = self.generator(
            platform=account.platform.slug,
            persona=account.persona,
            topic=topic,
            trends=trending,
        )

        if post_content.metadata.get("image_prompt") and task.config.get(
            "include_image", True
        ):
            from socialmind.content.image import get_image_generator
            from socialmind.content.media_store import MediaStore

            image_prompt = post_content.metadata["image_prompt"]
            generator_engine = get_image_generator()
            raw_image = await generator_engine.generate(image_prompt)

            store = MediaStore()
            media_url = await store.upload(
                data=raw_image,
                filename="post_image.jpg",
                content_type="image/jpeg",
                account_id=account.id,
            )
            post_content.media_urls = [media_url]

        return await adapter.post(post_content)

    async def run_dm_responses(
        self,
        account: Account,
        adapter: BasePlatformAdapter,
    ) -> list[bool]:
        """Check unread DMs, generate replies, and send them."""
        if account.persona is None:
            return []

        dms = await adapter.get_dms(unread_only=True)
        results: list[bool] = []

        for dm in dms:
            history = await adapter.get_dm_history(dm.thread_id, limit=10)
            reply = self.dm_responder(
                dm=dm,
                persona=account.persona,
                platform=account.platform.slug,
                history=history,
            )
            if reply:
                await asyncio.sleep(random.uniform(30, 120))
                result = await adapter.reply_dm(dm.dm_id, reply)
                results.append(result)

        return results
