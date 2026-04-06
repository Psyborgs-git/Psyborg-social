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

_YOUTUBE_SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]


class YouTubeAdapter(BasePlatformAdapter):
    """
    YouTube adapter using the official Google API Python Client for uploads and
    comments, and yt-dlp for research/scraping.
    """

    platform_slug = "youtube"

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._youtube = None

    async def authenticate(self) -> bool:
        """Authenticate using stored OAuth2 tokens."""
        try:
            from google.oauth2.credentials import Credentials  # type: ignore[import-untyped]
            from googleapiclient.discovery import build  # type: ignore[import-untyped]
        except ImportError:
            logger.warning(
                "google-api-python-client not installed — YouTube adapter unavailable"
            )
            return False

        token_data = self.session.api_tokens
        if token_data:
            try:
                credentials = Credentials.from_authorized_user_info(
                    token_data, _YOUTUBE_SCOPES
                )
                if not credentials.expired:
                    self._youtube = build(
                        "youtube", "v3", credentials=credentials, cache_discovery=False
                    )
                    return True
                if credentials.refresh_token:
                    import google.auth.transport.requests  # type: ignore[import-untyped]

                    credentials.refresh(google.auth.transport.requests.Request())
                    self.session.api_tokens = {
                        "token": credentials.token,
                        "refresh_token": credentials.refresh_token,
                        "token_uri": credentials.token_uri,
                        "client_id": credentials.client_id,
                        "client_secret": credentials.client_secret,
                        "scopes": list(credentials.scopes or []),
                    }
                    self._youtube = build(
                        "youtube", "v3", credentials=credentials, cache_discovery=False
                    )
                    return True
            except Exception as exc:
                logger.warning("YouTube token refresh failed: %s", exc)
        logger.warning(
            "YouTube requires pre-authorized OAuth tokens for account %s",
            self.account.username,
        )
        return False

    @rate_limited("youtube", "posts")
    @with_human_delay("post")
    async def post(self, content: PostContent) -> PostResult:
        """Upload a video to YouTube."""
        if self._youtube is None:
            return PostResult(success=False, error="Not authenticated")
        if not content.media_urls:
            return PostResult(success=False, error="YouTube requires a video URL")

        try:
            import asyncio

            from googleapiclient.http import MediaFileUpload  # type: ignore[import-untyped]

            video_path = await self._download_media(content.media_urls[0])
            body = {
                "snippet": {
                    "title": content.text[:100],
                    "description": content.text,
                    "tags": content.hashtags,
                    "categoryId": "22",
                },
                "status": {"privacyStatus": "public"},
            }
            media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
            request = self._youtube.videos().insert(
                part="snippet,status", body=body, media_body=media
            )
            response = await asyncio.get_event_loop().run_in_executor(
                None, request.execute
            )
            video_id = response["id"]
            return PostResult(
                success=True,
                platform_post_id=video_id,
                platform_url=f"https://youtube.com/watch?v={video_id}",
                adapter_used="api",
            )
        except Exception as exc:
            logger.error("YouTube post failed: %s", exc)
            return PostResult(success=False, error=str(exc))

    @rate_limited("youtube", "comments")
    @with_human_delay("comment")
    async def comment(self, target_id: str, text: str) -> CommentResult:
        """Post a comment on a YouTube video."""
        if self._youtube is None:
            return CommentResult(success=False, error="Not authenticated")
        try:
            import asyncio

            body = {
                "snippet": {
                    "videoId": target_id,
                    "topLevelComment": {
                        "snippet": {"textOriginal": text}
                    },
                }
            }
            request = self._youtube.commentThreads().insert(
                part="snippet", body=body
            )
            response = await asyncio.get_event_loop().run_in_executor(
                None, request.execute
            )
            return CommentResult(
                success=True,
                comment_id=response["id"],
            )
        except Exception as exc:
            logger.error("YouTube comment failed: %s", exc)
            return CommentResult(success=False, error=str(exc))

    async def reply_dm(self, dm_id: str, text: str) -> bool:
        """YouTube does not support direct messages."""
        logger.info("YouTube does not support DMs — skipping reply_dm")
        return False

    @rate_limited("youtube", "likes")
    @with_human_delay("like")
    async def like(self, target_id: str) -> bool:
        """Like a YouTube video via the API."""
        if self._youtube is None:
            return False
        try:
            import asyncio

            request = self._youtube.videos().rate(id=target_id, rating="like")
            await asyncio.get_event_loop().run_in_executor(None, request.execute)
            return True
        except Exception as exc:
            logger.error("YouTube like failed: %s", exc)
            return False

    @rate_limited("youtube", "follows")
    @with_human_delay("follow")
    async def follow(self, user_id: str) -> bool:
        """Subscribe to a YouTube channel."""
        if self._youtube is None:
            return False
        try:
            import asyncio

            body = {"snippet": {"resourceId": {"kind": "youtube#channel", "channelId": user_id}}}
            request = self._youtube.subscriptions().insert(part="snippet", body=body)
            await asyncio.get_event_loop().run_in_executor(None, request.execute)
            return True
        except Exception as exc:
            logger.error("YouTube subscribe failed: %s", exc)
            return False

    @rate_limited("youtube", "unfollows")
    @with_human_delay("unfollow")
    async def unfollow(self, user_id: str) -> bool:
        """Unsubscribe from a YouTube channel."""
        if self._youtube is None:
            return False
        try:
            import asyncio

            # Find subscription ID first
            req = self._youtube.subscriptions().list(
                part="id",
                forChannelId=user_id,
                mine=True,
            )
            resp = await asyncio.get_event_loop().run_in_executor(None, req.execute)
            items = resp.get("items", [])
            if not items:
                return False
            sub_id = items[0]["id"]
            del_req = self._youtube.subscriptions().delete(id=sub_id)
            await asyncio.get_event_loop().run_in_executor(None, del_req.execute)
            return True
        except Exception as exc:
            logger.error("YouTube unsubscribe failed: %s", exc)
            return False

    async def get_feed(self, limit: int = 20) -> list[FeedItem]:
        """Fetch the authenticated user's subscription feed."""
        if self._youtube is None:
            return []
        try:
            import asyncio

            request = self._youtube.activities().list(
                part="snippet,contentDetails",
                home=True,
                maxResults=limit,
            )
            response = await asyncio.get_event_loop().run_in_executor(
                None, request.execute
            )
            items: list[FeedItem] = []
            for activity in response.get("items", []):
                snippet = activity.get("snippet", {})
                items.append(
                    FeedItem(
                        platform_id=activity.get("id", ""),
                        author_username=snippet.get("channelTitle", ""),
                        text=snippet.get("title", ""),
                        media_urls=[
                            snippet.get("thumbnails", {})
                            .get("high", {})
                            .get("url", "")
                        ],
                        likes_count=0,
                        comments_count=0,
                        posted_at=datetime.fromisoformat(
                            snippet.get("publishedAt", "1970-01-01T00:00:00Z").replace(
                                "Z", "+00:00"
                            )
                        ),
                        raw=activity,
                    )
                )
            return items
        except Exception as exc:
            logger.error("YouTube get_feed failed: %s", exc)
            return []

    async def get_dms(self, unread_only: bool = True) -> list[DirectMessage]:
        """YouTube does not support direct messages."""
        return []

    async def get_dm_history(self, thread_id: str, limit: int = 10) -> list[DirectMessage]:
        """YouTube does not support direct messages."""
        return []

    async def search(self, query: str, limit: int = 10) -> list[SearchResult]:
        """Search YouTube for videos."""
        if self._youtube is None:
            return []
        try:
            import asyncio

            request = self._youtube.search().list(
                part="snippet", q=query, maxResults=limit, type="video"
            )
            response = await asyncio.get_event_loop().run_in_executor(
                None, request.execute
            )
            results: list[SearchResult] = []
            for item in response.get("items", []):
                snippet = item.get("snippet", {})
                vid_id = item.get("id", {}).get("videoId", "")
                results.append(
                    SearchResult(
                        platform_id=vid_id,
                        author_username=snippet.get("channelTitle", ""),
                        text=snippet.get("title", ""),
                        url=f"https://youtube.com/watch?v={vid_id}",
                    )
                )
            return results
        except Exception as exc:
            logger.error("YouTube search failed: %s", exc)
            return []

    async def get_trending(self, niche: str, limit: int = 20) -> list[TrendingItem]:
        """Use yt-dlp to scrape trending/search results without consuming API quota."""
        try:
            import asyncio
            import yt_dlp  # type: ignore[import-untyped]

            ydl_opts: dict = {
                "quiet": True,
                "extract_flat": True,
                "playlistend": limit,
            }
            search_query = f"ytsearch{limit}:{niche}"

            def _extract() -> list[TrendingItem]:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    result = ydl.extract_info(search_query, download=False)
                    return [
                        TrendingItem(
                            title=e.get("title", ""),
                            url=e.get("url") or f"https://youtube.com/watch?v={e.get('id', '')}",
                            engagement_score=float(e.get("view_count", 0) or 0),
                            hashtags=[],
                            platform_id=e.get("id"),
                        )
                        for e in (result or {}).get("entries", [])
                    ]

            return await asyncio.get_event_loop().run_in_executor(None, _extract)
        except Exception as exc:
            logger.error("YouTube get_trending failed: %s", exc)
            return []
