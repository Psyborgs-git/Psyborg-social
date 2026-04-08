from __future__ import annotations

from urllib.parse import quote_plus

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


class LinkedInAdapter(BasePlatformAdapter):
    """LinkedIn adapter backed by browser automation."""

    platform_slug = "linkedin"

    async def authenticate(self) -> bool:
        """Authenticate by restoring a browser session or performing a fresh login."""
        ctx = await self._get_browser_context()
        page = await ctx.new_page()
        try:
            if self.session.cookies:
                await ctx.add_cookies(self.session.cookies)
                await page.goto("https://www.linkedin.com/feed/")
                await page.wait_for_load_state("networkidle", timeout=20000)
                if "/login" not in page.url:
                    return True

            creds = self.account.decrypt_credentials()
            login_identifier = self.account.email or creds.get("email") or self.account.username
            password = creds.get("password")
            if not password:
                logger.error("LinkedIn account %s is missing a password", self.account.username)
                return False

            await page.goto("https://www.linkedin.com/login")
            await page.wait_for_load_state("networkidle", timeout=20000)
            await page.fill("#username", login_identifier)
            await self._apply_human_delay("typing")
            await page.fill("#password", password)
            await self._apply_human_delay("click")
            await page.click('button[type="submit"]')
            await page.wait_for_load_state("networkidle", timeout=30000)

            if self.session is not None:
                self.session.cookies = await ctx.cookies()
            return "/login" not in page.url
        except Exception as exc:
            logger.error("LinkedIn authenticate failed: %s", exc)
            return False
        finally:
            await page.close()

    @rate_limited("linkedin", "posts")
    @with_human_delay("post")
    async def post(self, content: PostContent) -> PostResult:
        """Create a LinkedIn post via browser automation."""
        ctx = await self._get_browser_context()
        page = await ctx.new_page()
        try:
            await page.goto("https://www.linkedin.com/feed/")
            await page.wait_for_load_state("networkidle", timeout=20000)
            trigger = await self._first_locator(
                page,
                (
                    'button[aria-label*="Start a post"]',
                    "button.share-box-feed-entry__trigger",
                ),
            )
            await trigger.click()
            editor = await self._first_locator(
                page,
                (
                    'div[role="textbox"]',
                    "div.ql-editor",
                ),
            )
            await editor.fill(content.text)

            if content.media_urls:
                media_path = await self._download_media(content.media_urls[0])
                file_input = page.locator('input[type="file"]').first
                await file_input.set_input_files(media_path)

            await self._apply_human_delay("form_submit")
            submit = await self._first_locator(
                page,
                (
                    "button.share-actions__primary-action",
                    'button[aria-label="Post"]',
                ),
            )
            await submit.click()
            await page.wait_for_load_state("networkidle", timeout=30000)
            return PostResult(success=True, adapter_used="browser")
        except Exception as exc:
            logger.error("LinkedIn post failed: %s", exc)
            return PostResult(success=False, error=str(exc))
        finally:
            await page.close()

    @rate_limited("linkedin", "comments")
    @with_human_delay("comment")
    async def comment(self, target_id: str, text: str) -> CommentResult:
        """Comment on a LinkedIn post via browser automation."""
        ctx = await self._get_browser_context()
        page = await ctx.new_page()
        try:
            await page.goto(self._update_url(target_id))
            await page.wait_for_load_state("networkidle", timeout=20000)
            editor = await self._first_locator(
                page,
                (
                    'div.comments-comment-box__editor[role="textbox"]',
                    'div[contenteditable="true"][role="textbox"]',
                ),
            )
            await editor.click()
            await editor.fill(text)
            await self._apply_human_delay("form_submit")
            await page.keyboard.press("Enter")
            return CommentResult(success=True)
        except Exception as exc:
            logger.error("LinkedIn comment failed: %s", exc)
            return CommentResult(success=False, error=str(exc))
        finally:
            await page.close()

    @rate_limited("linkedin", "dms")
    @with_human_delay("dm")
    async def reply_dm(self, dm_id: str, text: str) -> bool:
        """Reply to a LinkedIn messaging thread via browser automation."""
        ctx = await self._get_browser_context()
        page = await ctx.new_page()
        try:
            await page.goto(f"https://www.linkedin.com/messaging/thread/{dm_id}/")
            await page.wait_for_load_state("networkidle", timeout=20000)
            editor = await self._first_locator(
                page,
                (
                    'div.msg-form__contenteditable[role="textbox"]',
                    'div[contenteditable="true"][role="textbox"]',
                ),
            )
            await editor.click()
            await editor.fill(text)
            await page.keyboard.press("Enter")
            return True
        except Exception as exc:
            logger.error("LinkedIn reply_dm failed: %s", exc)
            return False
        finally:
            await page.close()

    @rate_limited("linkedin", "likes")
    @with_human_delay("like")
    async def like(self, target_id: str) -> bool:
        """Like a LinkedIn post via browser automation."""
        ctx = await self._get_browser_context()
        page = await ctx.new_page()
        try:
            await page.goto(self._update_url(target_id))
            await page.wait_for_load_state("networkidle", timeout=20000)
            button = await self._first_locator(
                page,
                (
                    'button[aria-label*="Like"]',
                    'button[aria-pressed="false"][aria-label*="Like"]',
                ),
            )
            await button.click()
            return True
        except Exception as exc:
            logger.error("LinkedIn like failed: %s", exc)
            return False
        finally:
            await page.close()

    @rate_limited("linkedin", "follows")
    @with_human_delay("follow")
    async def follow(self, user_id: str) -> bool:
        """Follow a LinkedIn profile via browser automation."""
        ctx = await self._get_browser_context()
        page = await ctx.new_page()
        try:
            await page.goto(self._profile_url(user_id))
            await page.wait_for_load_state("networkidle", timeout=20000)
            button = await self._first_locator(
                page,
                (
                    'button:has-text("Follow")',
                    'button[aria-label*="Follow"]',
                ),
            )
            await button.click()
            return True
        except Exception as exc:
            logger.error("LinkedIn follow failed: %s", exc)
            return False
        finally:
            await page.close()

    @rate_limited("linkedin", "unfollows")
    @with_human_delay("unfollow")
    async def unfollow(self, user_id: str) -> bool:
        """Unfollow a LinkedIn profile via browser automation."""
        ctx = await self._get_browser_context()
        page = await ctx.new_page()
        try:
            await page.goto(self._profile_url(user_id))
            await page.wait_for_load_state("networkidle", timeout=20000)
            button = await self._first_locator(
                page,
                (
                    'button:has-text("Following")',
                    'button[aria-label*="Following"]',
                ),
            )
            await button.click()
            return True
        except Exception as exc:
            logger.error("LinkedIn unfollow failed: %s", exc)
            return False
        finally:
            await page.close()

    async def get_feed(self, limit: int = 20) -> list[FeedItem]:
        """Fetch the LinkedIn home feed."""
        return []

    async def get_dms(self, unread_only: bool = True) -> list[DirectMessage]:
        """Fetch LinkedIn direct messages."""
        return []

    async def get_dm_history(self, thread_id: str, limit: int = 10) -> list[DirectMessage]:
        """Fetch LinkedIn DM thread history."""
        return []

    async def search(self, query: str, limit: int = 10) -> list[SearchResult]:
        """Search LinkedIn content via browser automation."""
        ctx = await self._get_browser_context()
        page = await ctx.new_page()
        try:
            await page.goto(
                f"https://www.linkedin.com/search/results/content/?keywords={quote_plus(query)}"
            )
            await page.wait_for_load_state("networkidle", timeout=20000)
            return []
        except Exception as exc:
            logger.error("LinkedIn search failed: %s", exc)
            return []
        finally:
            await page.close()

    async def get_trending(self, niche: str, limit: int = 20) -> list[TrendingItem]:
        """Fetch trending LinkedIn topics."""
        return []

    async def _first_locator(self, page, selectors: tuple[str, ...]):
        for selector in selectors:
            locator = page.locator(selector).first
            if await locator.count() > 0:
                return locator
        raise RuntimeError(f"No matching selector found from {selectors!r}")

    def _update_url(self, target_id: str) -> str:
        if target_id.startswith("http://") or target_id.startswith("https://"):
            return target_id
        return f"https://www.linkedin.com/feed/update/{target_id}/"

    def _profile_url(self, user_id: str) -> str:
        if user_id.startswith("http://") or user_id.startswith("https://"):
            return user_id
        return f"https://www.linkedin.com/in/{user_id}/"
