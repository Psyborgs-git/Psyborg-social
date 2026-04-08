from __future__ import annotations

from typing import TYPE_CHECKING

from socialmind.adapters.base import BasePlatformAdapter
from socialmind.adapters.facebook.adapter import FacebookAdapter
from socialmind.adapters.instagram.adapter import InstagramAdapter
from socialmind.adapters.linkedin.adapter import LinkedInAdapter
from socialmind.adapters.reddit.adapter import RedditAdapter
from socialmind.adapters.threads.adapter import ThreadsAdapter
from socialmind.adapters.tiktok.adapter import TikTokAdapter
from socialmind.adapters.twitter.adapter import TwitterAdapter
from socialmind.adapters.youtube.adapter import YouTubeAdapter

if TYPE_CHECKING:
    from socialmind.models.account import Account, AccountSession
    from socialmind.models.proxy import Proxy

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


def get_adapter(
    account: Account,
    session: AccountSession | None,
    proxy: Proxy | None,
) -> BasePlatformAdapter:
    """Instantiate the correct platform adapter for the given account."""
    platform_slug = account.platform.slug
    adapter_class = ADAPTER_REGISTRY.get(platform_slug)
    if adapter_class is None:
        raise ValueError(
            f"No adapter registered for platform '{platform_slug}'. "
            f"Available: {list(ADAPTER_REGISTRY.keys())}"
        )
    if session is None:
        from socialmind.models.account import AccountSession

        session = AccountSession(account_id=account.id)
        if hasattr(account, "sessions"):
            account.sessions.append(session)
    return adapter_class(account=account, session=session, proxy=proxy)
