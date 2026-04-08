from __future__ import annotations

from datetime import datetime, timezone
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


class TwitterAdapter(BasePlatformAdapter):
    """
    X (Twitter) adapter.

    Uses tweepy v2 async client for API-accessible actions (posts, replies).
    Falls back to Playwright for likes, follows, and browsing when API quota is
    insufficient (Free tier is heavily limited).
    """

    platform_slug = "twitter"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._client = None

    async def authenticate(self) -> bool:
        """Authenticate with API credentials first, then fall back to browser login."""
        self.last_error = None
        if await self._authenticate_api():
            return True
        return await self._authenticate_browser()

    async def _authenticate_api(self) -> bool:
        """Authenticate with tweepy AsyncClient using stored credentials."""
        try:
            import tweepy.asynchronous  # type: ignore[import-untyped]
        except Exception as exc:
            logger.warning(
                "Twitter API adapter unavailable, falling back to browser: {}", exc
            )
            return False

        creds = self.account.decrypt_credentials()
        if not any(
            creds.get(key)
            for key in (
                "bearer_token",
                "api_key",
                "api_secret",
                "access_token",
                "access_token_secret",
            )
        ):
            return False
        try:
            self._client = tweepy.asynchronous.AsyncClient(
                bearer_token=creds.get("bearer_token"),
                consumer_key=creds.get("api_key"),
                consumer_secret=creds.get("api_secret"),
                access_token=creds.get("access_token"),
                access_token_secret=creds.get("access_token_secret"),
            )
            me = await self._client.get_me()
            if me.data:
                self.account.platform_user_id = str(me.data.id)
                self.last_error = None
                return True
            return False
        except Exception as exc:
            logger.error("Twitter authenticate failed: {}", exc)
            return False

    async def _wait_for_page_ready(self, page, timeout: int = 10000) -> None:
        try:
            from playwright.async_api import TimeoutError as PlaywrightTimeoutError

            await page.wait_for_load_state("networkidle", timeout=timeout)
        except PlaywrightTimeoutError:
            logger.debug(
                "Twitter page did not reach networkidle within {}ms; continuing",
                timeout,
            )

    async def _authenticate_browser(self) -> bool:
        """Authenticate to X using Playwright and persist resulting browser state."""
        ctx = await self._get_browser_context()
        page = await ctx.new_page()
        try:
            await page.goto("https://x.com/home", wait_until="domcontentloaded")
            await self._wait_for_page_ready(page, timeout=5000)
            if await self._is_logged_in(page):
                self.session.cookies = await ctx.cookies()
                self.last_error = None
                return True

            creds = self.account.decrypt_credentials()
            identifier = (
                creds.get("email")
                or creds.get("username")
                or self.account.email
                or self.account.username
            )
            password = creds.get("password")
            if not identifier or not password:
                self.last_error = f"Twitter account {self.account.username} is missing browser login credentials"
                logger.error(self.last_error)
                return False

            await page.goto("https://x.com/i/flow/login", wait_until="domcontentloaded")
            await page.wait_for_selector(
                'input[autocomplete="username"]', timeout=30000
            )
            await page.fill('input[autocomplete="username"]', identifier)
            await self._apply_human_delay("typing")
            await page.keyboard.press("Enter")
            await self._wait_for_page_ready(page)

            challenge_input = page.locator(
                'input[data-testid="ocfEnterTextTextInput"]'
            ).first
            if await challenge_input.count() > 0:
                challenge_value = (
                    creds.get("handle")
                    or creds.get("username")
                    or self.account.username
                )
                await challenge_input.fill(challenge_value)
                await self._apply_human_delay("typing")
                await page.keyboard.press("Enter")
                await self._wait_for_page_ready(page)

            await page.wait_for_selector('input[name="password"]', timeout=30000)
            await page.fill('input[name="password"]', password)
            await self._apply_human_delay("typing")
            await page.keyboard.press("Enter")
            await self._wait_for_page_ready(page, timeout=10000)

            if not await self._is_logged_in(page):
                self.last_error = "Twitter login did not reach an authenticated state"
                return False

            state = await ctx.storage_state()
            self.session.cookies = state.get("cookies", [])
            self.session.local_storage = state.get("origins", [])
            self.session.is_valid = True
            self.account.last_active_at = datetime.now(timezone.utc)
            self.last_error = None
            return True
        except Exception as exc:
            if exc.__class__.__name__ == "InvalidToken":
                self.last_error = (
                    "Account credentials could not be decrypted. Set ENCRYPTION_KEY to the value "
                    "used when the account was added."
                )
            else:
                self.last_error = str(exc) or exc.__class__.__name__
            logger.error("Twitter browser authenticate failed: {}", exc)
            return False
        finally:
            await page.close()

    @rate_limited("twitter", "posts")
    @with_human_delay("post")
    async def post(self, content: PostContent) -> PostResult:
        """Post a tweet via tweepy, falling back to browser if needed."""
        if self._client is None:
            return PostResult(success=False, error="Not authenticated")

        text = content.text[:280]
        try:
            import tweepy  # type: ignore[import-untyped]

            response = await self._client.create_tweet(text=text)
            tweet_id = response.data["id"]
            return PostResult(
                success=True,
                platform_post_id=str(tweet_id),
                platform_url=f"https://twitter.com/i/web/status/{tweet_id}",
                adapter_used="api",
            )
        except Exception as exc:
            logger.warning("Twitter API post failed, trying browser: {}", exc)
            return await self._post_browser_fallback(content)

    async def _post_browser_fallback(self, content: PostContent) -> PostResult:
        """Compose and submit a tweet via Playwright."""
        ctx = await self._get_browser_context()
        page = await ctx.new_page()
        try:
            await page.goto("https://twitter.com/compose/tweet")
            await page.wait_for_selector(
                '[data-testid="tweetTextarea_0"]', timeout=15000
            )
            await page.fill('[data-testid="tweetTextarea_0"]', content.text[:280])
            await self._apply_human_delay("form_submit")
            await page.click('[data-testid="tweetButton"]')
            await page.wait_for_load_state("networkidle", timeout=20000)
            return PostResult(success=True, adapter_used="browser")
        except Exception as exc:
            return PostResult(success=False, error=str(exc))
        finally:
            await page.close()

    @rate_limited("twitter", "comments")
    @with_human_delay("comment")
    async def comment(self, target_id: str, text: str) -> CommentResult:
        """Reply to a tweet."""
        if self._client is None:
            return CommentResult(success=False, error="Not authenticated")
        try:
            response = await self._client.create_tweet(
                text=text[:280],
                in_reply_to_tweet_id=int(target_id),
            )
            return CommentResult(success=True, comment_id=str(response.data["id"]))
        except Exception as exc:
            logger.error("Twitter comment failed: {}", exc)
            return CommentResult(success=False, error=str(exc))

    @rate_limited("twitter", "dms")
    @with_human_delay("dm")
    async def reply_dm(self, dm_id: str, text: str) -> bool:
        """Reply to a Twitter DM conversation."""
        if self._client is None:
            return False
        try:
            await self._client.create_direct_message(conversation_id=dm_id, text=text)
            return True
        except Exception as exc:
            logger.error("Twitter reply_dm failed: {}", exc)
            return False

    @rate_limited("twitter", "likes")
    @with_human_delay("like")
    async def like(self, target_id: str) -> bool:
        """Like a tweet via browser (avoids Free tier API limit)."""
        ctx = await self._get_browser_context()
        page = await ctx.new_page()
        try:
            await page.goto(f"https://twitter.com/i/web/status/{target_id}")
            await page.wait_for_load_state("networkidle", timeout=20000)
            await page.click('[data-testid="like"]')
            return True
        except Exception as exc:
            logger.error("Twitter like failed: {}", exc)
            return False
        finally:
            await page.close()

    @rate_limited("twitter", "follows")
    @with_human_delay("follow")
    async def follow(self, user_id: str) -> bool:
        """Follow a Twitter user via browser."""
        ctx = await self._get_browser_context()
        page = await ctx.new_page()
        try:
            await page.goto(f"https://twitter.com/{user_id}")
            await page.wait_for_load_state("networkidle", timeout=20000)
            await page.click('[data-testid="followButton"]')
            return True
        except Exception as exc:
            logger.error("Twitter follow failed: {}", exc)
            return False
        finally:
            await page.close()

    @rate_limited("twitter", "unfollows")
    @with_human_delay("unfollow")
    async def unfollow(self, user_id: str) -> bool:
        """Unfollow a Twitter user via browser."""
        ctx = await self._get_browser_context()
        page = await ctx.new_page()
        try:
            await page.goto(f"https://twitter.com/{user_id}")
            await page.wait_for_load_state("networkidle", timeout=20000)
            await page.click('[data-testid="unfollowButton"]')
            await page.click('[data-testid="confirmationSheetConfirm"]')
            return True
        except Exception as exc:
            logger.error("Twitter unfollow failed: {}", exc)
            return False
        finally:
            await page.close()

    async def get_feed(self, limit: int = 20) -> list[FeedItem]:
        """Fetch the authenticated user's home timeline."""
        if self._client is None:
            return []
        try:
            from datetime import timezone

            response = await self._client.get_home_timeline(
                max_results=min(limit, 100),
                tweet_fields=["created_at", "public_metrics", "author_id"],
                expansions=["author_id"],
            )
            if not response.data:
                return []
            users = {u.id: u for u in (response.includes.get("users") or [])}
            items: list[FeedItem] = []
            for tweet in response.data:
                author = users.get(tweet.author_id)
                metrics = tweet.public_metrics or {}
                items.append(
                    FeedItem(
                        platform_id=str(tweet.id),
                        author_username=(
                            author.username if author else str(tweet.author_id)
                        ),
                        text=tweet.text,
                        media_urls=[],
                        likes_count=metrics.get("like_count", 0),
                        comments_count=metrics.get("reply_count", 0),
                        posted_at=tweet.created_at or datetime.now(timezone.utc),
                        raw={"metrics": metrics},
                    )
                )
            return items
        except Exception as exc:
            logger.error("Twitter get_feed failed: {}", exc)
            return []

    async def get_dms(self, unread_only: bool = True) -> list[DirectMessage]:
        """Fetch Twitter DMs (requires Elevated API access)."""
        return []

    async def get_dm_history(
        self, thread_id: str, limit: int = 10
    ) -> list[DirectMessage]:
        """Fetch DM thread history."""
        return []

    async def search(self, query: str, limit: int = 10) -> list[SearchResult]:
        """Search recent tweets via the API, with browser fallback when needed."""
        if self._client is None:
            return await self._search_browser(query, limit=limit)
        try:
            response = await self._client.search_recent_tweets(
                query=query,
                max_results=min(limit, 100),
                tweet_fields=["author_id", "public_metrics"],
                expansions=["author_id"],
            )
            if not response.data:
                return []
            users = {u.id: u for u in (response.includes.get("users") or [])}
            return [
                SearchResult(
                    platform_id=str(tweet.id),
                    author_username=(
                        users[tweet.author_id].username
                        if tweet.author_id in users
                        else str(tweet.author_id)
                    ),
                    text=tweet.text,
                    url=f"https://twitter.com/i/web/status/{tweet.id}",
                    likes_count=(tweet.public_metrics or {}).get("like_count", 0),
                )
                for tweet in response.data
            ]
        except Exception as exc:
            logger.error("Twitter search failed: {}", exc)
            return await self._search_browser(query, limit=limit)

    async def get_trending(self, niche: str, limit: int = 20) -> list[TrendingItem]:
        """
        Fetch trending topics/tweets for the niche using recent search.
        For full trending topics, the v1.1 API is required (Elevated access).
        """
        results = await self.search(niche, limit=limit)
        return [
            TrendingItem(
                title=r.text[:120],
                url=r.url,
                engagement_score=float(r.likes_count),
                hashtags=[w.lstrip("#") for w in r.text.split() if w.startswith("#")],
                platform_id=r.platform_id,
            )
            for r in results
        ]

    async def _search_browser(self, query: str, limit: int = 10) -> list[SearchResult]:
        ctx = await self._get_browser_context()
        page = await ctx.new_page()
        try:
            await page.goto(
                f"https://x.com/search?q={quote_plus(query)}&src=typed_query&f=live",
                wait_until="domcontentloaded",
            )
            await page.wait_for_selector('article[data-testid="tweet"]', timeout=30000)

            articles = page.locator('article[data-testid="tweet"]')
            count = await articles.count()
            results: list[SearchResult] = []
            for index in range(min(count, limit)):
                article = articles.nth(index)
                text_parts = await article.locator(
                    '[data-testid="tweetText"]'
                ).all_inner_texts()
                handle = await article.locator(
                    'a[role="link"][href^="/"]'
                ).first.get_attribute("href")
                tweet_link = article.locator('a[href*="/status/"]').first
                href = await tweet_link.get_attribute("href")
                likes_label = await article.locator(
                    '[data-testid="like"]'
                ).first.get_attribute("aria-label")
                like_count = self._extract_count(likes_label)

                platform_id = ""
                if href and "/status/" in href:
                    platform_id = href.rstrip("/").split("/status/")[-1]

                results.append(
                    SearchResult(
                        platform_id=platform_id,
                        author_username=(handle or "").lstrip("/"),
                        text="\n".join(
                            part.strip() for part in text_parts if part.strip()
                        ),
                        url=f"https://x.com{href}" if href else "",
                        likes_count=like_count,
                    )
                )

            state = await ctx.storage_state()
            self.session.cookies = state.get("cookies", [])
            self.session.local_storage = state.get("origins", [])
            return results
        except Exception as exc:
            logger.error("Twitter browser search failed: {}", exc)
            return []
        finally:
            await page.close()

    async def _is_logged_in(self, page) -> bool:
        return (
            await page.locator('[data-testid="SideNav_NewTweet_Button"]').count() > 0
            or await page.locator('a[href="/home"][aria-label]').count() > 0
        )

    def _extract_count(self, label: str | None) -> int:
        if not label:
            return 0
        digits = "".join(ch for ch in label if ch.isdigit())
        return int(digits) if digits else 0
