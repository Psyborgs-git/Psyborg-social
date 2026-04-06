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
        """Authenticate with tweepy AsyncClient using stored credentials."""
        try:
            import tweepy.asynchronous  # type: ignore[import-untyped]
        except ImportError:
            logger.warning("tweepy not installed — Twitter adapter unavailable")
            return False

        creds = self.account.decrypt_credentials()
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
                return True
            return False
        except Exception as exc:
            logger.error("Twitter authenticate failed: %s", exc)
            return False

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
            logger.warning("Twitter API post failed, trying browser: %s", exc)
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
            await page.fill(
                '[data-testid="tweetTextarea_0"]', content.text[:280]
            )
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
            logger.error("Twitter comment failed: %s", exc)
            return CommentResult(success=False, error=str(exc))

    @rate_limited("twitter", "dms")
    @with_human_delay("dm")
    async def reply_dm(self, dm_id: str, text: str) -> bool:
        """Reply to a Twitter DM conversation."""
        if self._client is None:
            return False
        try:
            await self._client.create_direct_message(
                conversation_id=dm_id, text=text
            )
            return True
        except Exception as exc:
            logger.error("Twitter reply_dm failed: %s", exc)
            return False

    @rate_limited("twitter", "likes")
    @with_human_delay("like")
    async def like(self, target_id: str) -> bool:
        """Like a tweet via browser (avoids Free tier API limit)."""
        ctx = await self._get_browser_context()
        page = await ctx.new_page()
        try:
            await page.goto(
                f"https://twitter.com/i/web/status/{target_id}"
            )
            await page.wait_for_load_state("networkidle", timeout=20000)
            await page.click('[data-testid="like"]')
            return True
        except Exception as exc:
            logger.error("Twitter like failed: %s", exc)
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
            logger.error("Twitter follow failed: %s", exc)
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
            logger.error("Twitter unfollow failed: %s", exc)
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
                        author_username=author.username if author else str(tweet.author_id),
                        text=tweet.text,
                        media_urls=[],
                        likes_count=metrics.get("like_count", 0),
                        comments_count=metrics.get("reply_count", 0),
                        posted_at=tweet.created_at or __import__("datetime").datetime.now(timezone.utc),
                        raw={"metrics": metrics},
                    )
                )
            return items
        except Exception as exc:
            logger.error("Twitter get_feed failed: %s", exc)
            return []

    async def get_dms(self, unread_only: bool = True) -> list[DirectMessage]:
        """Fetch Twitter DMs (requires Elevated API access)."""
        return []

    async def get_dm_history(self, thread_id: str, limit: int = 10) -> list[DirectMessage]:
        """Fetch DM thread history."""
        return []

    async def search(self, query: str, limit: int = 10) -> list[SearchResult]:
        """Search recent tweets via the v2 API."""
        if self._client is None:
            return []
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
            logger.error("Twitter search failed: %s", exc)
            return []

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
                hashtags=[
                    w.lstrip("#")
                    for w in r.text.split()
                    if w.startswith("#")
                ],
                platform_id=r.platform_id,
            )
            for r in results
        ]
