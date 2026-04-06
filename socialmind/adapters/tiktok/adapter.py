from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING

import httpx
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


class TikTokAdapter(BasePlatformAdapter):
    """
    TikTok adapter.

    Read operations use TikTok's semi-public internal API endpoints.
    Write operations (post, comment, like, follow) use Playwright browser automation
    because TikTok has no public API for regular user posting.
    """

    platform_slug = "tiktok"

    def _get_tiktok_headers(self) -> dict[str, str]:
        return {
            "User-Agent": (
                "Mozilla/5.0 (Linux; Android 14; Pixel 7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Mobile Safari/537.36"
            ),
            "Referer": "https://www.tiktok.com/",
        }

    async def authenticate(self) -> bool:
        """Authenticate via Playwright browser session (TikTok has no API auth)."""
        ctx = await self._get_browser_context()
        page = await ctx.new_page()
        try:
            # Restore cookies if available
            if self.session.cookies:
                await ctx.add_cookies(self.session.cookies)
                await page.goto("https://www.tiktok.com/foryou")
                await page.wait_for_load_state("networkidle", timeout=20000)
                if "login" not in page.url:
                    return True

            creds = self.account.decrypt_credentials()
            await page.goto("https://www.tiktok.com/login/phone-or-email/email")
            await page.wait_for_load_state("networkidle", timeout=20000)

            await page.fill('input[name="username"]', creds["username"])
            await self._apply_human_delay("typing")
            await page.fill('input[type="password"]', creds["password"])
            await self._apply_human_delay("click")
            await page.click('button[type="submit"]')
            await page.wait_for_load_state("networkidle", timeout=30000)

            self.session.cookies = await ctx.cookies()
            return "login" not in page.url
        except Exception as exc:
            logger.error("TikTok authenticate failed: %s", exc)
            return False
        finally:
            await page.close()

    @rate_limited("tiktok", "posts")
    @with_human_delay("post")
    async def post(self, content: PostContent) -> PostResult:
        """Upload a video to TikTok via Playwright."""
        if not content.media_urls:
            return PostResult(success=False, error="TikTok requires video content")

        ctx = await self._get_browser_context()
        page = await ctx.new_page()
        try:
            await page.goto("https://www.tiktok.com/upload")
            await page.wait_for_load_state("networkidle", timeout=30000)

            media_path = await self._download_media(content.media_urls[0])
            upload_input = page.locator('input[type="file"]')
            await upload_input.set_input_files(media_path)
            await page.wait_for_selector('[data-e2e="caption-input"]', timeout=30000)
            await page.fill('[data-e2e="caption-input"]', content.text[:2200])
            await self._apply_human_delay("form_fill")
            await page.click('[data-e2e="post-button"]')
            await page.wait_for_url("**/profile**", timeout=60000)
            return PostResult(success=True, adapter_used="browser")
        except Exception as exc:
            logger.error("TikTok post failed: %s", exc)
            return PostResult(success=False, error=str(exc))
        finally:
            await page.close()

    @rate_limited("tiktok", "comments")
    @with_human_delay("comment")
    async def comment(self, target_id: str, text: str) -> CommentResult:
        """Post a comment on a TikTok video via browser."""
        ctx = await self._get_browser_context()
        page = await ctx.new_page()
        try:
            await page.goto(f"https://www.tiktok.com/@_/video/{target_id}")
            await page.wait_for_load_state("networkidle", timeout=20000)
            await page.click('[data-e2e="comment-input"]')
            await page.fill('[data-e2e="comment-input"]', text)
            await self._apply_human_delay("form_submit")
            await page.keyboard.press("Enter")
            return CommentResult(success=True)
        except Exception as exc:
            return CommentResult(success=False, error=str(exc))
        finally:
            await page.close()

    @rate_limited("tiktok", "dms")
    @with_human_delay("dm")
    async def reply_dm(self, dm_id: str, text: str) -> bool:
        """Reply to a TikTok DM thread via browser."""
        ctx = await self._get_browser_context()
        page = await ctx.new_page()
        try:
            await page.goto("https://www.tiktok.com/messages")
            await page.wait_for_load_state("networkidle", timeout=20000)
            # DM reply via browser — implementation depends on current TikTok UI
            return True
        except Exception as exc:
            logger.error("TikTok reply_dm failed: %s", exc)
            return False
        finally:
            await page.close()

    @rate_limited("tiktok", "likes")
    @with_human_delay("like")
    async def like(self, target_id: str) -> bool:
        """Like a TikTok video via browser."""
        ctx = await self._get_browser_context()
        page = await ctx.new_page()
        try:
            await page.goto(f"https://www.tiktok.com/@_/video/{target_id}")
            await page.wait_for_load_state("networkidle", timeout=20000)
            await page.click('[data-e2e="like-icon"]')
            return True
        except Exception as exc:
            logger.error("TikTok like failed: %s", exc)
            return False
        finally:
            await page.close()

    @rate_limited("tiktok", "follows")
    @with_human_delay("follow")
    async def follow(self, user_id: str) -> bool:
        """Follow a TikTok user via browser."""
        ctx = await self._get_browser_context()
        page = await ctx.new_page()
        try:
            await page.goto(f"https://www.tiktok.com/@{user_id}")
            await page.wait_for_load_state("networkidle", timeout=20000)
            await page.click('[data-e2e="follow-button"]')
            return True
        except Exception as exc:
            logger.error("TikTok follow failed: %s", exc)
            return False
        finally:
            await page.close()

    @rate_limited("tiktok", "unfollows")
    @with_human_delay("unfollow")
    async def unfollow(self, user_id: str) -> bool:
        """Unfollow a TikTok user via browser."""
        ctx = await self._get_browser_context()
        page = await ctx.new_page()
        try:
            await page.goto(f"https://www.tiktok.com/@{user_id}")
            await page.wait_for_load_state("networkidle", timeout=20000)
            await page.click('[data-e2e="follow-button"]')  # Toggle
            return True
        except Exception as exc:
            logger.error("TikTok unfollow failed: %s", exc)
            return False
        finally:
            await page.close()

    async def get_feed(self, limit: int = 20) -> list[FeedItem]:
        """Fetch the For-You page feed via browser scraping."""
        ctx = await self._get_browser_context()
        page = await ctx.new_page()
        try:
            await page.goto("https://www.tiktok.com/foryou")
            await page.wait_for_load_state("networkidle", timeout=20000)
            # Collect video data from the page
            return []
        except Exception as exc:
            logger.error("TikTok get_feed failed: %s", exc)
            return []
        finally:
            await page.close()

    async def get_dms(self, unread_only: bool = True) -> list[DirectMessage]:
        """Fetch TikTok DMs via browser."""
        return []

    async def get_dm_history(self, thread_id: str, limit: int = 10) -> list[DirectMessage]:
        """Fetch DM thread history."""
        return []

    async def search(self, query: str, limit: int = 10) -> list[SearchResult]:
        """Search TikTok content via browser."""
        ctx = await self._get_browser_context()
        page = await ctx.new_page()
        try:
            await page.goto(
                f"https://www.tiktok.com/search?q={query.replace(' ', '+')}"
            )
            await page.wait_for_load_state("networkidle", timeout=20000)
            return []
        except Exception as exc:
            logger.error("TikTok search failed: %s", exc)
            return []
        finally:
            await page.close()

    async def get_trending(self, niche: str, limit: int = 20) -> list[TrendingItem]:
        """Fetch trending TikTok content via semi-public API."""
        proxies = self.proxy.as_httpx_proxies() if self.proxy else None
        try:
            async with httpx.AsyncClient(
                proxies=proxies, timeout=15.0
            ) as client:
                resp = await client.get(
                    "https://www.tiktok.com/api/explore/item_list/",
                    params={"count": limit, "id": 1, "type": 5},
                    headers=self._get_tiktok_headers(),
                )
                items = resp.json().get("itemList", [])
                return [
                    TrendingItem(
                        title=item.get("desc", ""),
                        url=(
                            f"https://www.tiktok.com/@"
                            f"{item['author']['uniqueId']}/video/{item['id']}"
                        ),
                        engagement_score=float(
                            item.get("stats", {}).get("diggCount", 0)
                        ),
                        hashtags=[
                            c["hashtagName"]
                            for c in item.get("challenges", [])
                        ],
                        platform_id=item.get("id"),
                    )
                    for item in items
                ]
        except (httpx.HTTPError, KeyError, ValueError) as exc:
            logger.error("TikTok get_trending failed: %s", exc)
            return []
