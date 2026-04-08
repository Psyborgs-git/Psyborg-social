from __future__ import annotations

import asyncio
from datetime import UTC, datetime

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


class ThreadsAdapter(BasePlatformAdapter):
    """
    Threads adapter.

    Threads shares authentication with Instagram (same Meta account).
    instagrapi supports Threads via the same private API backend.
    Playwright is used for operations not available via the private API.
    """

    platform_slug = "threads"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._api = None

    async def authenticate(self) -> bool:
        """Authenticate via instagrapi (Threads uses Instagram's backend)."""
        try:
            from instagrapi import Client as InstagrapiClient  # type: ignore[import-untyped]
            from instagrapi.exceptions import ClientError  # type: ignore[import-untyped]
        except ImportError:
            logger.warning("instagrapi not installed — Threads adapter unavailable")
            return False

        creds = self.account.decrypt_credentials()
        try:
            self._api = InstagrapiClient()
            if self.proxy:
                self._api.set_proxy(self.proxy.as_url())

            session_data = self.session.api_tokens
            if session_data:
                self._api.set_settings(session_data)
                try:
                    await asyncio.get_event_loop().run_in_executor(
                        None, self._api.get_timeline_feed
                    )
                    return True
                except Exception:
                    pass

            await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._api.login(creds["username"], creds["password"]),
            )
            self.session.api_tokens = self._api.get_settings()
            return True
        except ClientError as exc:
            logger.error("Threads authenticate failed: %s", exc)
            return False

    @rate_limited("threads", "posts")
    @with_human_delay("post")
    async def post(self, content: PostContent) -> PostResult:
        """Post to Threads via the Instagram private API Threads endpoint."""
        if self._api is None:
            return PostResult(success=False, error="Not authenticated")
        try:
            resp = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self._api.private.post(
                    "https://i.instagram.com/api/v1/media/configure_text_post_app_feed/",
                    data={
                        "text_post_app_info": '{"reply_control":0}',
                        "caption": content.text,
                        "audience": "default",
                    },
                ),
            )
            success = resp.status_code == 200
            platform_post_id = ""
            if success:
                json_resp = resp.json()
                platform_post_id = str(
                    json_resp.get("media", {}).get("pk", "")
                )
            return PostResult(
                success=success,
                platform_post_id=platform_post_id,
                adapter_used="api",
                error=None if success else f"HTTP {resp.status_code}",
            )
        except Exception as exc:
            logger.error("Threads post failed: %s", exc)
            return PostResult(success=False, error=str(exc))

    @rate_limited("threads", "comments")
    @with_human_delay("comment")
    async def comment(self, target_id: str, text: str) -> CommentResult:
        """Reply to a Threads post via instagrapi."""
        if self._api is None:
            return CommentResult(success=False, error="Not authenticated")
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self._api.media_comment(target_id, text)
            )
            return CommentResult(success=True, comment_id=str(result.pk))
        except Exception as exc:
            return CommentResult(success=False, error=str(exc))

    @rate_limited("threads", "dms")
    @with_human_delay("dm")
    async def reply_dm(self, dm_id: str, text: str) -> bool:
        """Reply to a Threads DM thread via browser (DMs not in private API)."""
        ctx = await self._get_browser_context()
        page = await ctx.new_page()
        try:
            await page.goto("https://www.threads.net/direct")
            await page.wait_for_load_state("networkidle", timeout=20000)
            return True
        except Exception as exc:
            logger.error("Threads reply_dm failed: %s", exc)
            return False
        finally:
            await page.close()

    @rate_limited("threads", "likes")
    @with_human_delay("like")
    async def like(self, target_id: str) -> bool:
        """Like a Threads post via instagrapi."""
        if self._api is None:
            return False
        try:
            await asyncio.get_event_loop().run_in_executor(
                None, lambda: self._api.media_like(target_id)
            )
            return True
        except Exception as exc:
            logger.error("Threads like failed: %s", exc)
            return False

    @rate_limited("threads", "follows")
    @with_human_delay("follow")
    async def follow(self, user_id: str) -> bool:
        """Follow a Threads user via instagrapi."""
        if self._api is None:
            return False
        try:
            await asyncio.get_event_loop().run_in_executor(
                None, lambda: self._api.user_follow(int(user_id))
            )
            return True
        except Exception as exc:
            logger.error("Threads follow failed: %s", exc)
            return False

    @rate_limited("threads", "unfollows")
    @with_human_delay("unfollow")
    async def unfollow(self, user_id: str) -> bool:
        """Unfollow a Threads user via instagrapi."""
        if self._api is None:
            return False
        try:
            await asyncio.get_event_loop().run_in_executor(
                None, lambda: self._api.user_unfollow(int(user_id))
            )
            return True
        except Exception as exc:
            logger.error("Threads unfollow failed: %s", exc)
            return False

    async def get_feed(self, limit: int = 20) -> list[FeedItem]:
        """Fetch the Threads home feed via instagrapi."""
        if self._api is None:
            return []
        try:
            items = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self._api.get_timeline_feed()
            )
            feed: list[FeedItem] = []
            for item in items.get("feed_items", [])[:limit]:
                mi = item.get("media_or_ad", {})
                caption = mi.get("caption")
                feed.append(
                    FeedItem(
                        platform_id=mi.get("id", ""),
                        author_username=mi.get("user", {}).get("username", ""),
                        text=caption.get("text", "") if caption else "",
                        media_urls=[],
                        likes_count=mi.get("like_count", 0),
                        comments_count=mi.get("comment_count", 0),
                        posted_at=datetime.fromtimestamp(
                            mi.get("taken_at", 0), tz=UTC
                        ),
                        raw=mi,
                    )
                )
            return feed
        except Exception as exc:
            logger.error("Threads get_feed failed: %s", exc)
            return []

    async def get_dms(self, unread_only: bool = True) -> list[DirectMessage]:
        """Fetch Threads DMs via instagrapi."""
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
            logger.error("Threads get_dms failed: %s", exc)
            return []

    async def get_dm_history(self, thread_id: str, limit: int = 10) -> list[DirectMessage]:
        """Fetch Threads DM thread history via instagrapi."""
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
            logger.error("Threads get_dm_history failed: %s", exc)
            return []

    async def search(self, query: str, limit: int = 10) -> list[SearchResult]:
        """Search Threads users via instagrapi."""
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
                    url=f"https://www.threads.net/@{u.username}",
                )
                for u in users[:limit]
            ]
        except Exception as exc:
            logger.error("Threads search failed: %s", exc)
            return []

    async def get_trending(self, niche: str, limit: int = 20) -> list[TrendingItem]:
        """Fetch trending Threads content via browser scraping."""
        ctx = await self._get_browser_context()
        page = await ctx.new_page()
        try:
            await page.goto(f"https://www.threads.net/search?q={niche}&serp_type=default")
            await page.wait_for_load_state("networkidle", timeout=20000)
            return []
        except Exception as exc:
            logger.error("Threads get_trending failed: %s", exc)
            return []
        finally:
            await page.close()
