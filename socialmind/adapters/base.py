from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

from loguru import logger

if TYPE_CHECKING:
    from socialmind.models.account import Account, AccountSession
    from socialmind.models.proxy import Proxy


@dataclass
class PostContent:
    text: str
    media_urls: list[str] = field(default_factory=list)
    hashtags: list[str] = field(default_factory=list)
    mentions: list[str] = field(default_factory=list)
    post_type: str = "feed"  # feed, story, reel, short, thread
    metadata: dict = field(default_factory=dict)


@dataclass
class PostResult:
    success: bool
    platform_post_id: str | None = None
    platform_url: str | None = None
    error: str | None = None
    adapter_used: str = "api"  # "api" or "browser"


@dataclass
class FeedItem:
    platform_id: str
    author_username: str
    text: str
    media_urls: list[str]
    likes_count: int
    comments_count: int
    posted_at: datetime
    raw: dict = field(default_factory=dict)


@dataclass
class DirectMessage:
    dm_id: str
    sender_username: str
    sender_platform_id: str
    text: str
    received_at: datetime
    thread_id: str
    is_read: bool = False


@dataclass
class TrendingItem:
    title: str
    url: str | None
    engagement_score: float
    hashtags: list[str]
    platform_id: str | None = None


@dataclass
class CommentResult:
    success: bool
    comment_id: str = ""
    error: str = ""


@dataclass
class SearchResult:
    platform_id: str
    author_username: str
    text: str
    url: str = ""
    media_urls: list[str] = field(default_factory=list)
    likes_count: int = 0


class BasePlatformAdapter(ABC):
    """Abstract base class that all platform adapters must implement."""

    platform_slug: str = ""

    def __init__(
        self,
        account: "Account",
        session: "AccountSession",
        proxy: "Proxy | None",
    ) -> None:
        self.account = account
        self.session = session
        self.proxy = proxy
        self._logger = logger.bind(adapter=self.platform_slug)
        self._rate_limiter = None  # Injected externally if needed

    @abstractmethod
    async def authenticate(self) -> bool:
        """Authenticate the account. Returns True on success."""
        ...

    @abstractmethod
    async def post(self, content: PostContent) -> PostResult:
        """Publish a post. Returns PostResult with platform ID on success."""
        ...

    @abstractmethod
    async def comment(self, target_id: str, text: str) -> CommentResult:
        """Post a comment on the target content. Returns CommentResult."""
        ...

    @abstractmethod
    async def reply_dm(self, dm_id: str, text: str) -> bool:
        """Reply to a direct message. Returns True on success."""
        ...

    @abstractmethod
    async def like(self, target_id: str) -> bool:
        """Like a piece of content. Returns True on success."""
        ...

    @abstractmethod
    async def follow(self, user_id: str) -> bool:
        """Follow a user. Returns True on success."""
        ...

    @abstractmethod
    async def unfollow(self, user_id: str) -> bool:
        """Unfollow a user. Returns True on success."""
        ...

    @abstractmethod
    async def get_feed(self, limit: int = 20) -> list[FeedItem]:
        """Fetch the account's home feed."""
        ...

    @abstractmethod
    async def get_dms(self, unread_only: bool = True) -> list[DirectMessage]:
        """Fetch direct messages for the account."""
        ...

    @abstractmethod
    async def get_dm_history(self, thread_id: str, limit: int = 10) -> list[DirectMessage]:
        """Fetch message history for a specific DM thread."""
        ...

    @abstractmethod
    async def search(self, query: str, limit: int = 10) -> list[SearchResult]:
        """Search for content or users on the platform."""
        ...

    @abstractmethod
    async def get_trending(self, niche: str, limit: int = 20) -> list[TrendingItem]:
        """Return trending content for the given niche."""
        ...

    # -----------------------------------------------------------------------
    # Concrete helpers available to all adapters
    # -----------------------------------------------------------------------

    async def _apply_human_delay(self, action_type: str, multiplier: float = 1.0) -> None:
        from socialmind.stealth.timing import TimingEngine

        await TimingEngine.delay(action_type, multiplier)

    async def _get_browser_context(self):
        from socialmind.stealth.session import BrowserContextFactory

        return await BrowserContextFactory.get_or_create(self.account, self.proxy)

    async def _download_media(self, url: str) -> str:
        """
        Download a media file from a URL (or MinIO key) and return its local path.

        Files are written to a `media_tmp/` subdirectory relative to the working
        directory. Callers are responsible for cleaning up files after use.
        """
        import os

        import httpx

        os.makedirs("media_tmp", exist_ok=True)
        suffix = os.path.splitext(url.split("?")[0])[-1] or ".bin"
        dest = os.path.join("media_tmp", f"{abs(hash(url))}{suffix}")
        async with httpx.AsyncClient(timeout=60.0) as client:
            async with client.stream("GET", url) as resp:
                resp.raise_for_status()
                with open(dest, "wb") as fh:
                    async for chunk in resp.aiter_bytes(chunk_size=8192):
                        fh.write(chunk)
        return dest

    def _build_caption(self, content: PostContent) -> str:
        """Construct a caption string from post content."""
        parts = [content.text]
        if content.hashtags:
            parts.append(" ".join(f"#{h.lstrip('#')}" for h in content.hashtags))
        if content.mentions:
            parts.append(" ".join(f"@{m.lstrip('@')}" for m in content.mentions))
        return "\n\n".join(parts)
