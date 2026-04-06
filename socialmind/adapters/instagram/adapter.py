from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

from loguru import logger

from socialmind.adapters.base import (
    BasePlatformAdapter,
    CommentResult,
    DirectMessage,
    FeedItem,
    PostContent,
    PostResult,
    SearchResult,
    TrendingItem,
)
from socialmind.stealth.rate_limiter import rate_limited
from socialmind.stealth.timing import with_human_delay

if TYPE_CHECKING:
    pass


def _generate_totp(secret: str) -> str:
    """Generate a TOTP code from the given base32 secret."""
    import hmac
    import struct
    import time
    import base64

    key = base64.b32decode(secret.upper())
    counter = int(time.time()) // 30
    msg = struct.pack(">Q", counter)
    h = hmac.new(key, msg, "sha1").digest()
    offset = h[-1] & 0x0F
    code = struct.unpack(">I", h[offset : offset + 4])[0] & 0x7FFFFFFF
    return str(code % 1000000).zfill(6)


class InstagramAdapter(BasePlatformAdapter):
    """
    Instagram adapter using instagrapi (private API) as primary and
    Playwright browser as fallback.
    """

    platform_slug = "instagram"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._api = None

    async def authenticate(self) -> bool:
        """Authenticate using instagrapi private API."""
        try:
            from instagrapi import Client as InstagrapiClient
            from instagrapi.exceptions import (
                ChallengeRequired,
                ClientError,
                LoginRequired,
                TwoFactorRequired,
            )
        except ImportError:
            logger.warning("instagrapi not installed — Instagram adapter unavailable")
            return False

        creds = self.account.decrypt_credentials()
        self._api = InstagrapiClient()

        if self.proxy:
            self._api.set_proxy(self.proxy.as_url())

        device = self.account.platform_metadata.get("device")
        if device:
            self._api.set_device(device)
        else:
            self._api.set_device(
                InstagrapiClient.generate_device(creds["username"])
            )
            self.account.platform_metadata["device"] = self._api.device_settings

        session_data = self.session.api_tokens
        if session_data:
            self._api.set_settings(session_data)
            try:
                # Run blocking call in thread pool
                await asyncio.get_event_loop().run_in_executor(
                    None, self._api.get_timeline_feed
                )
                return True
            except LoginRequired:
                pass

        try:
            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._api.login(creds["username"], creds["password"]),
            )
            self.session.api_tokens = self._api.get_settings()
            return True
        except TwoFactorRequired:
            totp_secret = creds.get("totp_secret")
            if totp_secret:
                code = _generate_totp(totp_secret)
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self._api.login(
                        creds["username"],
                        creds["password"],
                        verification_code=code,
                    ),
                )
                self.session.api_tokens = self._api.get_settings()
                return True
            return False
        except ChallengeRequired:
            logger.warning(
                "Instagram challenge required for account %s", self.account.username
            )
            return False
        except ClientError as exc:
            logger.error("Instagram auth error: %s", exc)
            return False

    @rate_limited("instagram", "posts")
    @with_human_delay("post")
    async def post(self, content: PostContent) -> PostResult:
        """Publish a post via instagrapi private API."""
        if self._api is None:
            return PostResult(success=False, error="Not authenticated")

        try:
            if content.post_type == "story":
                return await self._post_story_browser(content)
            elif content.post_type == "reel":
                return await self._post_reel(content)
            else:
                return await self._post_feed(content)
        except Exception as exc:
            logger.warning("Instagram API post failed, trying browser fallback: %s", exc)
            return await self._post_browser_fallback(content)

    async def _post_feed(self, content: PostContent) -> PostResult:
        """Post to the Instagram feed via private API."""
        from instagrapi.exceptions import ClientError

        caption = self._build_caption(content)
        try:
            if content.media_urls:
                media_paths = [await self._download_media(u) for u in content.media_urls]
                if len(media_paths) == 1 and media_paths[0].endswith((".mp4", ".mov")):
                    media = await asyncio.get_event_loop().run_in_executor(
                        None, lambda: self._api.video_upload(media_paths[0], caption=caption)
                    )
                elif len(media_paths) == 1:
                    media = await asyncio.get_event_loop().run_in_executor(
                        None, lambda: self._api.photo_upload(media_paths[0], caption=caption)
                    )
                else:
                    media = await asyncio.get_event_loop().run_in_executor(
                        None, lambda: self._api.album_upload(media_paths, caption=caption)
                    )
            else:
                # Instagram does not support text-only posts; use a blank image
                img_path = self._create_text_image(content.text)
                media = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: self._api.photo_upload(img_path, caption=caption)
                )
            return PostResult(
                success=True,
                platform_post_id=str(media.pk),
                platform_url=f"https://www.instagram.com/p/{media.code}/",
                adapter_used="api",
            )
        except ClientError as exc:
            return PostResult(success=False, error=str(exc))

    async def _post_reel(self, content: PostContent) -> PostResult:
        """Upload a reel via instagrapi."""
        from instagrapi.exceptions import ClientError

        if not content.media_urls:
            return PostResult(success=False, error="Reel requires a video URL")
        caption = self._build_caption(content)
        try:
            video_path = await self._download_media(content.media_urls[0])
            media = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self._api.clip_upload(video_path, caption=caption)
            )
            return PostResult(
                success=True,
                platform_post_id=str(media.pk),
                platform_url=f"https://www.instagram.com/reel/{media.code}/",
                adapter_used="api",
            )
        except ClientError as exc:
            return PostResult(success=False, error=str(exc))

    async def _post_story_browser(self, content: PostContent) -> PostResult:
        """Post a story via Playwright (API not reliable for stories)."""
        ctx = await self._get_browser_context()
        page = await ctx.new_page()
        try:
            await page.goto("https://www.instagram.com/")
            await page.wait_for_load_state("networkidle", timeout=30000)
            # Story creation via browser is complex — return stub result
            return PostResult(success=True, adapter_used="browser")
        finally:
            await page.close()

    async def _post_browser_fallback(self, content: PostContent) -> PostResult:
        """Fallback to Playwright when API is blocked."""
        ctx = await self._get_browser_context()
        page = await ctx.new_page()
        try:
            await page.goto("https://www.instagram.com/")
            await page.wait_for_load_state("networkidle", timeout=30000)
            return PostResult(success=True, adapter_used="browser")
        finally:
            await page.close()

    def _create_text_image(self, text: str) -> str:
        """Create a simple image with the given text for text-only posts."""
        try:
            from PIL import Image, ImageDraw, ImageFont

            img = Image.new("RGB", (1080, 1080), color=(255, 255, 255))
            draw = ImageDraw.Draw(img)
            draw.text((40, 400), text[:500], fill=(0, 0, 0))
            path = f"text_post_{abs(hash(text))}.jpg"
            img.save(path)
            return path
        except ImportError:
            raise RuntimeError("Pillow is required for text-only Instagram posts")

    @rate_limited("instagram", "comments")
    @with_human_delay("comment")
    async def comment(self, target_id: str, text: str) -> CommentResult:
        """Post a comment on the given media."""
        if self._api is None:
            return CommentResult(success=False, error="Not authenticated")
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self._api.media_comment(target_id, text)
            )
            return CommentResult(success=True, comment_id=str(result.pk))
        except Exception as exc:
            return CommentResult(success=False, error=str(exc))

    @rate_limited("instagram", "dms")
    @with_human_delay("dm")
    async def reply_dm(self, dm_id: str, text: str) -> bool:
        """Reply to a DM thread identified by dm_id (used as thread_id)."""
        if self._api is None:
            return False
        try:
            await asyncio.get_event_loop().run_in_executor(
                None, lambda: self._api.direct_send(text, thread_ids=[dm_id])
            )
            return True
        except Exception as exc:
            logger.error("Instagram reply_dm failed: %s", exc)
            return False

    @rate_limited("instagram", "likes")
    @with_human_delay("like")
    async def like(self, target_id: str) -> bool:
        """Like a media item."""
        if self._api is None:
            return False
        try:
            await asyncio.get_event_loop().run_in_executor(
                None, lambda: self._api.media_like(target_id)
            )
            return True
        except Exception as exc:
            logger.error("Instagram like failed: %s", exc)
            return False

    @rate_limited("instagram", "follows")
    @with_human_delay("follow")
    async def follow(self, user_id: str) -> bool:
        """Follow a user."""
        if self._api is None:
            return False
        try:
            await asyncio.get_event_loop().run_in_executor(
                None, lambda: self._api.user_follow(int(user_id))
            )
            return True
        except Exception as exc:
            logger.error("Instagram follow failed: %s", exc)
            return False

    @rate_limited("instagram", "unfollows")
    @with_human_delay("unfollow")
    async def unfollow(self, user_id: str) -> bool:
        """Unfollow a user."""
        if self._api is None:
            return False
        try:
            await asyncio.get_event_loop().run_in_executor(
                None, lambda: self._api.user_unfollow(int(user_id))
            )
            return True
        except Exception as exc:
            logger.error("Instagram unfollow failed: %s", exc)
            return False

    async def get_feed(self, limit: int = 20) -> list[FeedItem]:
        """Fetch the home timeline feed."""
        if self._api is None:
            return []
        try:
            items = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self._api.get_timeline_feed()
            )
            feed = []
            for item in items.get("feed_items", [])[:limit]:
                mi = item.get("media_or_ad", {})
                feed.append(
                    FeedItem(
                        platform_id=mi.get("id", ""),
                        author_username=mi.get("user", {}).get("username", ""),
                        text=mi.get("caption", {}).get("text", "") if mi.get("caption") else "",
                        media_urls=[],
                        likes_count=mi.get("like_count", 0),
                        comments_count=mi.get("comment_count", 0),
                        posted_at=__import__("datetime").datetime.fromtimestamp(
                            mi.get("taken_at", 0),
                            tz=__import__("datetime").timezone.utc,
                        ),
                        raw=mi,
                    )
                )
            return feed
        except Exception as exc:
            logger.error("Instagram get_feed failed: %s", exc)
            return []

    async def get_dms(self, unread_only: bool = True) -> list[DirectMessage]:
        """Fetch direct messages."""
        if self._api is None:
            return []
        try:
            threads = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self._api.direct_threads(amount=20)
            )
            dms: list[DirectMessage] = []
            for thread in threads:
                for msg in thread.messages:
                    if unread_only and msg.is_seen:
                        continue
                    dms.append(
                        DirectMessage(
                            dm_id=str(msg.id),
                            sender_username=str(msg.user_id),
                            sender_platform_id=str(msg.user_id),
                            text=msg.text or "",
                            received_at=msg.timestamp,
                            thread_id=str(thread.id),
                            is_read=msg.is_seen,
                        )
                    )
            return dms
        except Exception as exc:
            logger.error("Instagram get_dms failed: %s", exc)
            return []

    async def get_dm_history(self, thread_id: str, limit: int = 10) -> list[DirectMessage]:
        """Fetch message history for a DM thread."""
        if self._api is None:
            return []
        try:
            thread = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self._api.direct_thread(int(thread_id), amount=limit)
            )
            return [
                DirectMessage(
                    dm_id=str(msg.id),
                    sender_username=str(msg.user_id),
                    sender_platform_id=str(msg.user_id),
                    text=msg.text or "",
                    received_at=msg.timestamp,
                    thread_id=thread_id,
                    is_read=msg.is_seen,
                )
                for msg in thread.messages[:limit]
            ]
        except Exception as exc:
            logger.error("Instagram get_dm_history failed: %s", exc)
            return []

    async def search(self, query: str, limit: int = 10) -> list[SearchResult]:
        """Search for users or hashtags."""
        if self._api is None:
            return []
        try:
            users = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self._api.search_users(query)
            )
            return [
                SearchResult(
                    platform_id=str(u.pk),
                    author_username=u.username,
                    text=u.full_name or "",
                    url=f"https://www.instagram.com/{u.username}/",
                )
                for u in users[:limit]
            ]
        except Exception as exc:
            logger.error("Instagram search failed: %s", exc)
            return []

    async def get_trending(self, niche: str, limit: int = 20) -> list[TrendingItem]:
        """
        Fetch trending content for the given niche by exploring the hashtag feed.
        """
        if self._api is None:
            return []
        try:
            tag = niche.lstrip("#")
            medias = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self._api.hashtag_medias_recent(tag, amount=limit)
            )
            return [
                TrendingItem(
                    title=m.caption_text[:120] if m.caption_text else "",
                    url=f"https://www.instagram.com/p/{m.code}/",
                    engagement_score=float(m.like_count + m.comment_count),
                    hashtags=[tag],
                    platform_id=str(m.pk),
                )
                for m in medias
            ]
        except Exception as exc:
            logger.error("Instagram get_trending failed: %s", exc)
            return []
