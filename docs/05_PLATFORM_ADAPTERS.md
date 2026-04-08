# Platform Adapters

Design and implementation guide for all 8 platform adapters. Each adapter uses a dual-strategy approach: private API client (fast, lightweight) with a Playwright browser fallback (robust, full-featured). LinkedIn currently follows the browser-first path because the official API is too limited for normal end-user automation.

---

## Base Adapter Interface

Every platform adapter must implement this abstract interface. This ensures all platform-specific logic stays behind a clean, swappable boundary.

```python
# socialmind/adapters/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import AsyncIterator

@dataclass
class PostContent:
    text: str
    media_urls: list[str] = field(default_factory=list)  # MinIO URLs
    hashtags: list[str] = field(default_factory=list)
    mentions: list[str] = field(default_factory=list)
    post_type: str = "feed"  # feed, story, reel, short, thread

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
    raw: dict  # Full raw response for downstream use

@dataclass
class DirectMessage:
    dm_id: str
    sender_username: str
    sender_platform_id: str
    text: str
    received_at: datetime
    thread_id: str
    is_read: bool

@dataclass
class TrendingItem:
    title: str
    url: str | None
    engagement_score: float
    hashtags: list[str]
    platform_id: str | None

class BasePlatformAdapter(ABC):
    def __init__(self, account: Account, session: AccountSession, proxy: Proxy | None):
        self.account = account
        self.session = session
        self.proxy = proxy
        self._logger = get_logger(f"adapter.{self.platform_slug}")

    @property
    @abstractmethod
    def platform_slug(self) -> str: ...

    @abstractmethod
    async def authenticate(self) -> bool: ...

    @abstractmethod
    async def post(self, content: PostContent) -> PostResult: ...

    @abstractmethod
    async def comment(self, target_id: str, text: str) -> bool: ...

    @abstractmethod
    async def reply_dm(self, dm_id: str, text: str) -> bool: ...

    @abstractmethod
    async def like(self, target_id: str) -> bool: ...

    @abstractmethod
    async def follow(self, user_id: str) -> bool: ...

    @abstractmethod
    async def unfollow(self, user_id: str) -> bool: ...

    @abstractmethod
    async def get_feed(self, limit: int = 20) -> list[FeedItem]: ...

    @abstractmethod
    async def get_dms(self, unread_only: bool = True) -> list[DirectMessage]: ...

    @abstractmethod
    async def search(self, query: str, limit: int = 10) -> list[FeedItem]: ...

    @abstractmethod
    async def get_trending(self, niche: str, limit: int = 20) -> list[TrendingItem]: ...

    # Concrete helpers available to all adapters
    async def _apply_human_delay(self, action_type: str):
        from socialmind.stealth.timing import TimingEngine
        await TimingEngine.delay(action_type)

    async def _get_browser_context(self):
        from socialmind.stealth.session import BrowserContextFactory
        return await BrowserContextFactory.get_or_create(self.account, self.proxy)
```

---

## Instagram Adapter

**Strategy**: `instagrapi` (private API) primary, Playwright fallback for stories, reels, and when detection is triggered.

```python
# socialmind/adapters/instagram/adapter.py
from instagrapi import Client as InstagrapiClient
from instagrapi.exceptions import (
    LoginRequired, ChallengeRequired, TwoFactorRequired, ClientError
)

class InstagramAdapter(BasePlatformAdapter):
    platform_slug = "instagram"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._api: InstagrapiClient | None = None

    async def authenticate(self) -> bool:
        creds = self.account.decrypt_credentials()
        self._api = InstagrapiClient()

        # Configure proxy
        if self.proxy:
            self._api.set_proxy(self.proxy.as_url())

        # Configure device fingerprint (stored per account for consistency)
        device = self.account.platform_metadata.get("device")
        if device:
            self._api.set_device(device)
        else:
            self._api.set_device(InstagrapiClient.generate_device(creds["username"]))
            # Store for next time
            self.account.platform_metadata["device"] = self._api.device_settings

        # Try to restore session
        session_data = self.session.api_tokens
        if session_data:
            self._api.set_settings(session_data)
            try:
                self._api.get_timeline_feed()  # Validate session
                return True
            except LoginRequired:
                pass

        # Fresh login
        try:
            self._api.login(creds["username"], creds["password"])
            self.session.api_tokens = self._api.get_settings()
            return True
        except ChallengeRequired:
            # Handle email/phone challenge — requires manual intervention or 2FA solver
            self._logger.warning("Instagram challenge required for %s", self.account.username)
            return False
        except TwoFactorRequired:
            totp_secret = creds.get("totp_secret")
            if totp_secret:
                code = generate_totp(totp_secret)
                self._api.login(creds["username"], creds["password"], verification_code=code)
                return True
            return False

    async def post(self, content: PostContent) -> PostResult:
        await self._apply_human_delay("post")
        try:
            if content.post_type == "story":
                return await self._post_story_browser(content)  # Stories → browser
            elif content.post_type == "reel":
                return await self._post_reel(content)
            else:
                return await self._post_feed(content)
        except (ClientError, DetectionError):
            return await self._post_browser_fallback(content)

    async def _post_feed(self, content: PostContent) -> PostResult:
        caption = self._build_caption(content)
        if content.media_urls:
            media_paths = await self._download_media(content.media_urls)
            if len(media_paths) == 1 and media_paths[0].endswith((".mp4", ".mov")):
                media = self._api.video_upload(media_paths[0], caption=caption)
            elif len(media_paths) == 1:
                media = self._api.photo_upload(media_paths[0], caption=caption)
            else:
                media = self._api.album_upload(media_paths, caption=caption)
        else:
            # Text-only → use note or carousel with blank card (IG doesn't support pure text posts)
            media = self._api.photo_upload(self._create_text_image(content.text), caption=caption)

        return PostResult(
            success=True,
            platform_post_id=str(media.pk),
            platform_url=f"https://www.instagram.com/p/{media.code}/",
            adapter_used="api",
        )

    async def get_dms(self, unread_only: bool = True) -> list[DirectMessage]:
        threads = self._api.direct_threads(amount=20)
        dms = []
        for thread in threads:
            for msg in thread.messages:
                if unread_only and msg.is_seen:
                    continue
                dms.append(DirectMessage(
                    dm_id=str(msg.id),
                    sender_username=msg.user_id,
                    sender_platform_id=str(msg.user_id),
                    text=msg.text or "",
                    received_at=msg.timestamp,
                    thread_id=str(thread.id),
                    is_read=msg.is_seen,
                ))
        return dms

    async def reply_dm(self, dm_id: str, text: str) -> bool:
        await self._apply_human_delay("dm")
        thread_id = await self._get_thread_id_for_dm(dm_id)
        self._api.direct_send(text, thread_ids=[thread_id])
        return True
```

**Key `instagrapi` behaviors to be aware of:**
- Always reuse device settings across sessions (same device fingerprint)
- Use `set_proxy()` before any API call
- Handle `ChallengeRequired` — may need email/SMS verification
- Rate limits: max ~60 follows/hour, ~100 likes/hour in practice

---

## TikTok Adapter

**Strategy**: `pyktok` + TikTok private API (reverse-engineered) for reading; Playwright for posting (TikTok's upload flow is complex and locked down).

```python
# socialmind/adapters/tiktok/adapter.py
# TikTok has no official API for content posting as a regular user.
# We use Playwright for all write operations and pyktok for reads.

class TikTokAdapter(BasePlatformAdapter):
    platform_slug = "tiktok"

    async def authenticate(self) -> bool:
        ctx = await self._get_browser_context()
        page = await ctx.new_page()
        await page.goto("https://www.tiktok.com/login")

        # Restore cookies if we have a session
        if self.session.cookies:
            await ctx.add_cookies(self.session.cookies)
            await page.goto("https://www.tiktok.com/foryou")
            if "login" not in page.url:
                return True

        # Login flow
        creds = self.account.decrypt_credentials()
        await page.click('[data-e2e="channel-item"]')  # Use username/password
        await page.fill('input[name="username"]', creds["username"])
        await self._apply_human_delay("typing")
        await page.fill('input[type="password"]', creds["password"])
        await self._apply_human_delay("click")
        await page.click('[data-e2e="login-button"]')
        await page.wait_for_load_state("networkidle")

        # Save cookies
        self.session.cookies = await ctx.cookies()
        return True

    async def post(self, content: PostContent) -> PostResult:
        """TikTok requires video for main feed. For text/image, use photo mode."""
        ctx = await self._get_browser_context()
        page = await ctx.new_page()
        await page.goto("https://www.tiktok.com/upload")
        await page.wait_for_load_state("networkidle")

        if content.post_type == "reel" or content.media_urls:
            media_path = await self._download_media(content.media_urls[0])
            upload_input = page.locator('input[type="file"]')
            await upload_input.set_input_files(media_path)
            await page.wait_for_selector('[data-e2e="caption-input"]', timeout=30000)
            await page.fill('[data-e2e="caption-input"]', content.text[:2200])
            await self._apply_human_delay("form_fill")
            await page.click('[data-e2e="post-button"]')
            await page.wait_for_url("**/profile**", timeout=60000)
            return PostResult(success=True, adapter_used="browser")
        return PostResult(success=False, error="TikTok requires video content")

    async def get_trending(self, niche: str, limit: int = 20) -> list[TrendingItem]:
        """Use TikTok's internal API to get trending content."""
        # TikTok exposes a semi-public trending endpoint
        async with httpx.AsyncClient(proxies=self.proxy.as_httpx_proxies()) as client:
            resp = await client.get(
                "https://www.tiktok.com/api/explore/item_list/",
                params={"count": limit, "id": 1, "type": 5},
                headers=self._get_tiktok_headers(),
            )
            items = resp.json().get("itemList", [])
            return [TrendingItem(
                title=item["desc"],
                url=f"https://www.tiktok.com/@{item['author']['uniqueId']}/video/{item['id']}",
                engagement_score=item["stats"]["diggCount"],
                hashtags=[c["hashtagName"] for c in item.get("challenges", [])],
                platform_id=item["id"],
            ) for item in items]
```

---

## Reddit Adapter

**Strategy**: `praw` (official Reddit API) for everything — Reddit has a permissive free API tier. Playwright fallback for voting and UI-only features.

```python
# socialmind/adapters/reddit/adapter.py
import praw
import asyncpraw  # Async version of praw

class RedditAdapter(BasePlatformAdapter):
    platform_slug = "reddit"

    async def authenticate(self) -> bool:
        creds = self.account.decrypt_credentials()
        self._api = asyncpraw.Reddit(
            client_id=creds["client_id"],
            client_secret=creds["client_secret"],
            username=creds["username"],
            password=creds["password"],
            user_agent=f"SocialMind/1.0 by u/{creds['username']}",
        )
        me = await self._api.user.me()
        return me is not None

    async def post(self, content: PostContent) -> PostResult:
        await self._apply_human_delay("post")
        subreddit_name = content.metadata.get("subreddit", "test")
        subreddit = await self._api.subreddit(subreddit_name)

        if content.media_urls:
            # Image post
            submission = await subreddit.submit_image(
                title=content.text[:300],
                image_path=await self._download_media(content.media_urls[0]),
            )
        else:
            # Text post
            body = content.text[300:] if len(content.text) > 300 else ""
            submission = await subreddit.submit(
                title=content.text[:300],
                selftext=body,
            )

        return PostResult(
            success=True,
            platform_post_id=submission.id,
            platform_url=f"https://reddit.com{submission.permalink}",
        )

    async def comment(self, target_id: str, text: str) -> bool:
        await self._apply_human_delay("comment")
        submission = await self._api.submission(id=target_id)
        await submission.reply(text)
        return True

    async def get_trending(self, niche: str, limit: int = 20) -> list[TrendingItem]:
        subreddit = await self._api.subreddit(niche)
        items = []
        async for post in subreddit.hot(limit=limit):
            items.append(TrendingItem(
                title=post.title,
                url=f"https://reddit.com{post.permalink}",
                engagement_score=post.score,
                hashtags=[],
                platform_id=post.id,
            ))
        return items
```

**Reddit API setup required per account:**
1. Create Reddit app at `https://www.reddit.com/prefs/apps`
2. App type: `script`
3. Store `client_id` and `client_secret` in account credentials

---

## YouTube Adapter

**Strategy**: Google API Python Client for uploads, comments, metadata; `yt-dlp` for research/scraping; Playwright for UI actions not in the API.

```python
# socialmind/adapters/youtube/adapter.py
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

class YouTubeAdapter(BasePlatformAdapter):
    platform_slug = "youtube"
    SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]

    async def authenticate(self) -> bool:
        creds = self.account.decrypt_credentials()
        # Use stored OAuth2 tokens
        token_data = self.session.api_tokens
        if token_data:
            credentials = Credentials.from_authorized_user_info(token_data, self.SCOPES)
            if not credentials.expired:
                self._youtube = build("youtube", "v3", credentials=credentials)
                return True
        # First-time OAuth flow (requires manual browser step — document this)
        # In production, pre-authorize accounts and store refresh tokens
        return False

    async def post(self, content: PostContent) -> PostResult:
        """Upload a video to YouTube."""
        video_path = await self._download_media(content.media_urls[0])
        body = {
            "snippet": {
                "title": content.text[:100],
                "description": content.text,
                "tags": content.hashtags,
                "categoryId": "22",  # People & Blogs default
            },
            "status": {"privacyStatus": "public"},
        }
        media = MediaFileUpload(video_path, chunksize=-1, resumable=True)
        request = self._youtube.videos().insert(part="snippet,status", body=body, media_body=media)
        response = request.execute()
        video_id = response["id"]
        return PostResult(
            success=True,
            platform_post_id=video_id,
            platform_url=f"https://youtube.com/watch?v={video_id}",
        )

    async def get_trending(self, niche: str, limit: int = 20) -> list[TrendingItem]:
        """Use yt-dlp to scrape trending/search results without API quota."""
        import yt_dlp
        ydl_opts = {"quiet": True, "extract_flat": True, "playlistend": limit}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(f"ytsearch{limit}:{niche}", download=False)
            return [TrendingItem(
                title=e["title"],
                url=e["url"],
                engagement_score=e.get("view_count", 0),
                hashtags=[],
                platform_id=e["id"],
            ) for e in result.get("entries", [])]
```

---

## Facebook Adapter

**Strategy**: Playwright for all operations (Graph API scope is too restricted for regular posting without approved app review). `facebook-sdk` used where Graph API is accessible.

```python
# socialmind/adapters/facebook/adapter.py
class FacebookAdapter(BasePlatformAdapter):
    platform_slug = "facebook"

    async def post(self, content: PostContent) -> PostResult:
        ctx = await self._get_browser_context()
        page = await ctx.new_page()

        # Navigate to Facebook and create a post
        await page.goto("https://www.facebook.com/")
        await page.wait_for_selector('[aria-label="Create a post"]')
        await page.click('[aria-label="Create a post"]')
        await self._apply_human_delay("click")
        await page.wait_for_selector('[contenteditable="true"]')
        await page.fill('[contenteditable="true"]', content.text)

        if content.media_urls:
            # Add photo/video
            await page.click('[aria-label="Photo/video"]')
            file_input = page.locator('input[type="file"]')
            media_path = await self._download_media(content.media_urls[0])
            await file_input.set_input_files(media_path)
            await page.wait_for_selector('[aria-label="Post"]', timeout=30000)

        await self._apply_human_delay("form_submit")
        await page.click('[aria-label="Post"]')
        await page.wait_for_load_state("networkidle")
        return PostResult(success=True, adapter_used="browser")
```

---

## X (Twitter) Adapter

**Strategy**: `tweepy` v2 for API-accessible actions (posts, replies, DMs with Elevated access); Playwright for everything else (likes, follows, browsing without API quota).

```python
# socialmind/adapters/twitter/adapter.py
import tweepy
import tweepy.asynchronous

class TwitterAdapter(BasePlatformAdapter):
    platform_slug = "twitter"

    async def authenticate(self) -> bool:
        creds = self.account.decrypt_credentials()
        self._client = tweepy.AsyncClient(
            bearer_token=creds.get("bearer_token"),
            consumer_key=creds["api_key"],
            consumer_secret=creds["api_secret"],
            access_token=creds["access_token"],
            access_token_secret=creds["access_token_secret"],
        )
        me = await self._client.get_me()
        self.account.platform_user_id = str(me.data.id)
        return True

    async def post(self, content: PostContent) -> PostResult:
        await self._apply_human_delay("post")
        text = content.text[:280]  # Twitter char limit
        try:
            response = await self._client.create_tweet(text=text)
            tweet_id = response.data["id"]
            return PostResult(
                success=True,
                platform_post_id=tweet_id,
                platform_url=f"https://twitter.com/i/web/status/{tweet_id}",
            )
        except tweepy.Forbidden:
            # Free tier doesn't allow posting — use browser
            return await self._post_browser_fallback(content)

    async def _post_browser_fallback(self, content: PostContent) -> PostResult:
        ctx = await self._get_browser_context()
        page = await ctx.new_page()
        await page.goto("https://twitter.com/compose/tweet")
        await page.fill('[data-testid="tweetTextarea_0"]', content.text[:280])
        await self._apply_human_delay("form_submit")
        await page.click('[data-testid="tweetButton"]')
        await page.wait_for_load_state("networkidle")
        return PostResult(success=True, adapter_used="browser")
```

---

## Threads Adapter

**Strategy**: Threads has an official API (launched 2024) with limited scope; `instagrapi` can interface with Threads endpoints since it shares the Instagram backend. Playwright for anything else.

```python
# socialmind/adapters/threads/adapter.py
# Threads shares authentication with Instagram (same Meta account)
# instagrapi supports Threads via the same private API

class ThreadsAdapter(BasePlatformAdapter):
    platform_slug = "threads"

    async def authenticate(self) -> bool:
        # Threads uses Instagram session — reuse Instagram adapter's auth
        creds = self.account.decrypt_credentials()
        self._api = InstagrapiClient()
        if self.proxy:
            self._api.set_proxy(self.proxy.as_url())
        # Login via Instagram private API (Threads is the same backend)
        self._api.login(creds["username"], creds["password"])
        return True

    async def post(self, content: PostContent) -> PostResult:
        # Use Threads private API endpoint
        await self._apply_human_delay("post")
        resp = self._api.private.post(
            "https://i.instagram.com/api/v1/media/configure_text_post_app_feed/",
            data={
                "text_post_app_info": '{"reply_control":0}',
                "caption": content.text,
                "audience": "default",
            }
        )
        return PostResult(
            success=resp.status_code == 200,
            adapter_used="api",
        )
```

---

## Adapter Registry

All adapters are registered so they can be instantiated by platform slug:

```python
# socialmind/adapters/registry.py
from socialmind.adapters.instagram.adapter import InstagramAdapter
from socialmind.adapters.tiktok.adapter import TikTokAdapter
from socialmind.adapters.reddit.adapter import RedditAdapter
from socialmind.adapters.youtube.adapter import YouTubeAdapter
from socialmind.adapters.facebook.adapter import FacebookAdapter
from socialmind.adapters.twitter.adapter import TwitterAdapter
from socialmind.adapters.threads.adapter import ThreadsAdapter
from socialmind.adapters.linkedin.adapter import LinkedInAdapter

ADAPTER_REGISTRY: dict[str, type[BasePlatformAdapter]] = {
    "instagram": InstagramAdapter,
    "tiktok": TikTokAdapter,
    "reddit": RedditAdapter,
    "youtube": YouTubeAdapter,
    "facebook": FacebookAdapter,
    "twitter": TwitterAdapter,
    "threads": ThreadsAdapter,
    "linkedin": LinkedInAdapter,
}

def get_adapter(account: Account, session: AccountSession | None, proxy: Proxy | None) -> BasePlatformAdapter:
    AdapterClass = ADAPTER_REGISTRY[account.platform.slug]
    return AdapterClass(account=account, session=session, proxy=proxy)
```

---

## Platform Capability Matrix

| Capability | Instagram | TikTok | Reddit | YouTube | Facebook | X | Threads |
|---|---|---|---|---|---|---|---|
| Feed post | API ✓ | Browser | API ✓ | API ✓ | Browser | API/Browser | API ✓ |
| Story | Browser | Browser | — | — | Browser | — | — |
| Reel/Short | API ✓ | Browser | — | API ✓ | Browser | — | — |
| Comment | API ✓ | Browser | API ✓ | API ✓ | Browser | API ✓ | API ✓ |
| DM | API ✓ | Browser | API ✓ | — | Browser | API ✓ | Browser |
| Like | API ✓ | Browser | API ✓ | API ✓ | Browser | Browser | API ✓ |
| Follow | API ✓ | Browser | API ✓ | API ✓ | Browser | Browser | API ✓ |
| Trending | API ✓ | API ✓ | API ✓ | yt-dlp ✓ | Browser | API ✓ | Browser |
| Search | API ✓ | Browser | API ✓ | API ✓ | Browser | API ✓ | Browser |
