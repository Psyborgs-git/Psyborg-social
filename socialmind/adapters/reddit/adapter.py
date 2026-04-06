from __future__ import annotations

from datetime import datetime, timezone

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


class RedditAdapter(BasePlatformAdapter):
    """
    Reddit adapter using asyncpraw (official async Reddit API).
    Reddit's free-tier API is permissive enough for most operations.
    Playwright fallback is used for UI-only features.
    """

    platform_slug = "reddit"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._api = None

    async def authenticate(self) -> bool:
        """Authenticate using asyncpraw with stored OAuth credentials."""
        try:
            import asyncpraw  # type: ignore[import-untyped]
        except ImportError:
            logger.warning("asyncpraw not installed — Reddit adapter unavailable")
            return False

        creds = self.account.decrypt_credentials()
        try:
            self._api = asyncpraw.Reddit(
                client_id=creds["client_id"],
                client_secret=creds["client_secret"],
                username=creds["username"],
                password=creds["password"],
                user_agent=f"SocialMind/1.0 by u/{creds['username']}",
            )
            me = await self._api.user.me()
            if me is not None:
                self.account.platform_user_id = str(me.id)
                return True
            return False
        except Exception as exc:
            logger.error("Reddit authenticate failed: %s", exc)
            return False

    @rate_limited("reddit", "posts")
    @with_human_delay("post")
    async def post(self, content: PostContent) -> PostResult:
        """Submit a post to a subreddit."""
        if self._api is None:
            return PostResult(success=False, error="Not authenticated")

        subreddit_name = content.metadata.get("subreddit", "test")
        try:
            subreddit = await self._api.subreddit(subreddit_name)
            if content.media_urls:
                image_path = await self._download_media(content.media_urls[0])
                submission = await subreddit.submit_image(
                    title=content.text[:300],
                    image_path=image_path,
                )
            else:
                body = content.text[300:] if len(content.text) > 300 else ""
                submission = await subreddit.submit(
                    title=content.text[:300],
                    selftext=body,
                )
            return PostResult(
                success=True,
                platform_post_id=submission.id,
                platform_url=f"https://reddit.com{submission.permalink}",
                adapter_used="api",
            )
        except Exception as exc:
            logger.error("Reddit post failed: %s", exc)
            return PostResult(success=False, error=str(exc))

    @rate_limited("reddit", "comments")
    @with_human_delay("comment")
    async def comment(self, target_id: str, text: str) -> CommentResult:
        """Reply to a Reddit submission or comment."""
        if self._api is None:
            return CommentResult(success=False, error="Not authenticated")
        try:
            submission = await self._api.submission(id=target_id)
            comment = await submission.reply(text)
            return CommentResult(success=True, comment_id=comment.id)
        except Exception as exc:
            logger.error("Reddit comment failed: %s", exc)
            return CommentResult(success=False, error=str(exc))

    @rate_limited("reddit", "dms")
    @with_human_delay("dm")
    async def reply_dm(self, dm_id: str, text: str) -> bool:
        """Reply to a Reddit direct message."""
        if self._api is None:
            return False
        try:
            message = await self._api.inbox.message(dm_id)
            await message.reply(text)
            return True
        except Exception as exc:
            logger.error("Reddit reply_dm failed: %s", exc)
            return False

    @rate_limited("reddit", "likes")
    @with_human_delay("like")
    async def like(self, target_id: str) -> bool:
        """Upvote a submission or comment."""
        if self._api is None:
            return False
        try:
            submission = await self._api.submission(id=target_id)
            await submission.upvote()
            return True
        except Exception as exc:
            logger.error("Reddit upvote failed: %s", exc)
            return False

    @rate_limited("reddit", "follows")
    @with_human_delay("follow")
    async def follow(self, user_id: str) -> bool:
        """Subscribe to a subreddit (Reddit's follow equivalent for content)."""
        if self._api is None:
            return False
        try:
            subreddit = await self._api.subreddit(user_id)
            await subreddit.subscribe()
            return True
        except Exception as exc:
            logger.error("Reddit follow/subscribe failed: %s", exc)
            return False

    @rate_limited("reddit", "unfollows")
    @with_human_delay("unfollow")
    async def unfollow(self, user_id: str) -> bool:
        """Unsubscribe from a subreddit."""
        if self._api is None:
            return False
        try:
            subreddit = await self._api.subreddit(user_id)
            await subreddit.unsubscribe()
            return True
        except Exception as exc:
            logger.error("Reddit unfollow failed: %s", exc)
            return False

    async def get_feed(self, limit: int = 20) -> list[FeedItem]:
        """Fetch the user's front page feed."""
        if self._api is None:
            return []
        try:
            items: list[FeedItem] = []
            async for post in self._api.front.hot(limit=limit):
                items.append(
                    FeedItem(
                        platform_id=post.id,
                        author_username=str(post.author) if post.author else "[deleted]",
                        text=post.title,
                        media_urls=[post.url] if post.url and not post.is_self else [],
                        likes_count=post.score,
                        comments_count=post.num_comments,
                        posted_at=datetime.fromtimestamp(
                            post.created_utc, tz=timezone.utc
                        ),
                        raw={"selftext": post.selftext, "subreddit": str(post.subreddit)},
                    )
                )
            return items
        except Exception as exc:
            logger.error("Reddit get_feed failed: %s", exc)
            return []

    async def get_dms(self, unread_only: bool = True) -> list[DirectMessage]:
        """Fetch Reddit inbox messages."""
        if self._api is None:
            return []
        try:
            messages: list[DirectMessage] = []
            source = self._api.inbox.unread() if unread_only else self._api.inbox.all()
            async for msg in source:
                messages.append(
                    DirectMessage(
                        dm_id=msg.id,
                        sender_username=str(msg.author) if msg.author else "[deleted]",
                        sender_platform_id=str(msg.author) if msg.author else "",
                        text=msg.body,
                        received_at=datetime.fromtimestamp(
                            msg.created_utc, tz=timezone.utc
                        ),
                        thread_id=msg.id,
                        is_read=not msg.new,
                    )
                )
            return messages
        except Exception as exc:
            logger.error("Reddit get_dms failed: %s", exc)
            return []

    async def get_dm_history(self, thread_id: str, limit: int = 10) -> list[DirectMessage]:
        """Fetch reply chain for a Reddit message thread."""
        if self._api is None:
            return []
        try:
            msg = await self._api.inbox.message(thread_id)
            await msg.load()
            history = [
                DirectMessage(
                    dm_id=msg.id,
                    sender_username=str(msg.author) if msg.author else "[deleted]",
                    sender_platform_id=str(msg.author) if msg.author else "",
                    text=msg.body,
                    received_at=datetime.fromtimestamp(msg.created_utc, tz=timezone.utc),
                    thread_id=thread_id,
                    is_read=not msg.new,
                )
            ]
            return history[:limit]
        except Exception as exc:
            logger.error("Reddit get_dm_history failed: %s", exc)
            return []

    async def search(self, query: str, limit: int = 10) -> list[SearchResult]:
        """Search Reddit across all subreddits."""
        if self._api is None:
            return []
        try:
            results: list[SearchResult] = []
            subreddit = await self._api.subreddit("all")
            async for post in subreddit.search(query, limit=limit):
                results.append(
                    SearchResult(
                        platform_id=post.id,
                        author_username=str(post.author) if post.author else "[deleted]",
                        text=post.title,
                        url=f"https://reddit.com{post.permalink}",
                        likes_count=post.score,
                    )
                )
            return results
        except Exception as exc:
            logger.error("Reddit search failed: %s", exc)
            return []

    async def get_trending(self, niche: str, limit: int = 20) -> list[TrendingItem]:
        """Fetch trending posts from the niche subreddit."""
        if self._api is None:
            return []
        try:
            subreddit = await self._api.subreddit(niche)
            items: list[TrendingItem] = []
            async for post in subreddit.hot(limit=limit):
                items.append(
                    TrendingItem(
                        title=post.title,
                        url=f"https://reddit.com{post.permalink}",
                        engagement_score=float(post.score),
                        hashtags=[],
                        platform_id=post.id,
                    )
                )
            return items
        except Exception as exc:
            logger.error("Reddit get_trending failed: %s", exc)
            return []
