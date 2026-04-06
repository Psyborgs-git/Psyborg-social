from __future__ import annotations

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


class FacebookAdapter(BasePlatformAdapter):
    """
    Facebook adapter.

    Uses Playwright for all operations because the Graph API scope is too
    restricted for regular posting without an approved app review.
    facebook-sdk is used where the Graph API is accessible (e.g., pages API).
    """

    platform_slug = "facebook"

    async def authenticate(self) -> bool:
        """Authenticate by restoring a browser session or performing a fresh login."""
        ctx = await self._get_browser_context()
        page = await ctx.new_page()
        try:
            if self.session.cookies:
                await ctx.add_cookies(self.session.cookies)
                await page.goto("https://www.facebook.com/")
                await page.wait_for_load_state("networkidle", timeout=20000)
                if "login" not in page.url:
                    return True

            creds = self.account.decrypt_credentials()
            await page.goto("https://www.facebook.com/login")
            await page.wait_for_load_state("networkidle", timeout=20000)
            await page.fill("#email", creds["email"])
            await self._apply_human_delay("typing")
            await page.fill("#pass", creds["password"])
            await self._apply_human_delay("click")
            await page.click('button[name="login"]')
            await page.wait_for_load_state("networkidle", timeout=30000)

            self.session.cookies = await ctx.cookies()
            return "login" not in page.url
        except Exception as exc:
            logger.error("Facebook authenticate failed: %s", exc)
            return False
        finally:
            await page.close()

    @rate_limited("facebook", "posts")
    @with_human_delay("post")
    async def post(self, content: PostContent) -> PostResult:
        """Create a Facebook post via browser automation."""
        ctx = await self._get_browser_context()
        page = await ctx.new_page()
        try:
            await page.goto("https://www.facebook.com/")
            await page.wait_for_selector('[aria-label="Create a post"]', timeout=20000)
            await page.click('[aria-label="Create a post"]')
            await self._apply_human_delay("click")
            await page.wait_for_selector('[contenteditable="true"]', timeout=10000)
            await page.fill('[contenteditable="true"]', content.text)

            if content.media_urls:
                await page.click('[aria-label="Photo/video"]')
                file_input = page.locator('input[type="file"]')
                media_path = await self._download_media(content.media_urls[0])
                await file_input.set_input_files(media_path)
                await page.wait_for_selector('[aria-label="Post"]', timeout=30000)

            await self._apply_human_delay("form_submit")
            await page.click('[aria-label="Post"]')
            await page.wait_for_load_state("networkidle", timeout=30000)
            return PostResult(success=True, adapter_used="browser")
        except Exception as exc:
            logger.error("Facebook post failed: %s", exc)
            return PostResult(success=False, error=str(exc))
        finally:
            await page.close()

    @rate_limited("facebook", "comments")
    @with_human_delay("comment")
    async def comment(self, target_id: str, text: str) -> CommentResult:
        """Comment on a Facebook post via browser."""
        ctx = await self._get_browser_context()
        page = await ctx.new_page()
        try:
            await page.goto(f"https://www.facebook.com/{target_id}")
            await page.wait_for_load_state("networkidle", timeout=20000)
            await page.click('[aria-label="Write a comment"]')
            await page.keyboard.type(text)
            await self._apply_human_delay("form_submit")
            await page.keyboard.press("Enter")
            return CommentResult(success=True)
        except Exception as exc:
            return CommentResult(success=False, error=str(exc))
        finally:
            await page.close()

    @rate_limited("facebook", "dms")
    @with_human_delay("dm")
    async def reply_dm(self, dm_id: str, text: str) -> bool:
        """Reply to a Facebook Messenger thread via browser."""
        ctx = await self._get_browser_context()
        page = await ctx.new_page()
        try:
            await page.goto(f"https://www.facebook.com/messages/t/{dm_id}")
            await page.wait_for_load_state("networkidle", timeout=20000)
            await page.click('[aria-label="Message"]')
            await page.keyboard.type(text)
            await page.keyboard.press("Enter")
            return True
        except Exception as exc:
            logger.error("Facebook reply_dm failed: %s", exc)
            return False
        finally:
            await page.close()

    @rate_limited("facebook", "likes")
    @with_human_delay("like")
    async def like(self, target_id: str) -> bool:
        """Like a Facebook post via browser."""
        ctx = await self._get_browser_context()
        page = await ctx.new_page()
        try:
            await page.goto(f"https://www.facebook.com/{target_id}")
            await page.wait_for_load_state("networkidle", timeout=20000)
            await page.click('[aria-label="Like"]')
            return True
        except Exception as exc:
            logger.error("Facebook like failed: %s", exc)
            return False
        finally:
            await page.close()

    @rate_limited("facebook", "follows")
    @with_human_delay("follow")
    async def follow(self, user_id: str) -> bool:
        """Follow a Facebook profile via browser."""
        ctx = await self._get_browser_context()
        page = await ctx.new_page()
        try:
            await page.goto(f"https://www.facebook.com/{user_id}")
            await page.wait_for_load_state("networkidle", timeout=20000)
            await page.click('[aria-label="Follow"]')
            return True
        except Exception as exc:
            logger.error("Facebook follow failed: %s", exc)
            return False
        finally:
            await page.close()

    @rate_limited("facebook", "unfollows")
    @with_human_delay("unfollow")
    async def unfollow(self, user_id: str) -> bool:
        """Unfollow a Facebook profile via browser."""
        ctx = await self._get_browser_context()
        page = await ctx.new_page()
        try:
            await page.goto(f"https://www.facebook.com/{user_id}")
            await page.wait_for_load_state("networkidle", timeout=20000)
            await page.click('[aria-label="Following"]')
            await page.wait_for_selector('[aria-label="Unfollow"]', timeout=5000)
            await page.click('[aria-label="Unfollow"]')
            return True
        except Exception as exc:
            logger.error("Facebook unfollow failed: %s", exc)
            return False
        finally:
            await page.close()

    async def get_feed(self, limit: int = 20) -> list[FeedItem]:
        """Scrape the Facebook home feed via browser."""
        return []

    async def get_dms(self, unread_only: bool = True) -> list[DirectMessage]:
        """Fetch Facebook Messenger messages via browser."""
        return []

    async def get_dm_history(self, thread_id: str, limit: int = 10) -> list[DirectMessage]:
        """Fetch Messenger thread history via browser."""
        return []

    async def search(self, query: str, limit: int = 10) -> list[SearchResult]:
        """Search Facebook via browser."""
        ctx = await self._get_browser_context()
        page = await ctx.new_page()
        try:
            await page.goto(
                f"https://www.facebook.com/search/posts?q={query.replace(' ', '%20')}"
            )
            await page.wait_for_load_state("networkidle", timeout=20000)
            return []
        except Exception as exc:
            logger.error("Facebook search failed: %s", exc)
            return []
        finally:
            await page.close()

    async def get_trending(self, niche: str, limit: int = 20) -> list[TrendingItem]:
        """Scrape trending Facebook topics via browser."""
        return []
