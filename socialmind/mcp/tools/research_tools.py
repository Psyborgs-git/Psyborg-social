from __future__ import annotations

from mcp.types import Tool


def _normalize_platform(platform: str | None) -> str | None:
    if platform is None:
        return None

    normalized = platform.strip().lower()
    return {
        "x": "twitter",
        "x.com": "twitter",
    }.get(normalized, normalized)


def _is_active_account(account) -> bool:
    status = getattr(account, "status", None)
    if status is None:
        return False
    if hasattr(status, "value"):
        return status.value == "active"
    return str(status) == "active"


async def _resolve_account(
    service,
    *,
    platform: str | None,
    account_id: str | None = None,
    username: str | None = None,
):
    normalized_platform = _normalize_platform(platform)

    if account_id is not None:
        try:
            account = await service.get_account(account_id)
        except ValueError as exc:
            return None, normalized_platform, str(exc)

        if (
            normalized_platform is not None
            and account.platform.slug != normalized_platform
        ):
            return (
                None,
                normalized_platform,
                f"Account {account_id} is not on platform {normalized_platform}",
            )
        if (
            username is not None
            and account.username.lower() != username.strip().lower()
        ):
            return (
                None,
                normalized_platform,
                f"Account {account_id} does not match username {username}",
            )
        if not _is_active_account(account):
            return None, normalized_platform, f"Account {account_id} is not active"
        return account, normalized_platform, None

    accounts = await service.list_accounts(
        platform=normalized_platform, status="active"
    )
    if username is not None:
        normalized_username = username.strip().lower()
        for account in accounts:
            if account.username.lower() == normalized_username:
                return account, normalized_platform, None
        return (
            None,
            normalized_platform,
            f"No active account found for username {username}",
        )

    if not accounts:
        return None, normalized_platform, "No active account available for platform"

    return accounts[0], normalized_platform, None


TOOLS: list[Tool] = [
    Tool(
        name="research_trends",
        description="Research current trends for a platform and niche.",
        inputSchema={
            "type": "object",
            "properties": {
                "platform": {"type": "string"},
                "niche": {"type": "string"},
                "account_id": {"type": "string"},
                "username": {"type": "string"},
            },
            "required": ["platform", "niche"],
        },
    ),
    Tool(
        name="search_content",
        description="Search for content matching a query.",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "platform": {"type": "string"},
                "account_id": {"type": "string"},
                "username": {"type": "string"},
            },
            "required": ["query"],
        },
    ),
    Tool(
        name="analyze_competitor",
        description="Analyze a competitor account.",
        inputSchema={
            "type": "object",
            "properties": {
                "account_id": {"type": "string"},
                "competitor_username": {"type": "string"},
            },
            "required": ["account_id", "competitor_username"],
        },
    ),
]


async def handle(name: str, arguments: dict) -> dict:
    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    from socialmind.adapters.registry import get_adapter
    from socialmind.config.settings import settings
    from socialmind.services.account_service import AccountService
    from socialmind.session import RedisSessionManager

    engine = create_async_engine(settings.DATABASE_URL)
    factory = async_sessionmaker(engine, expire_on_commit=False)

    try:
        async with factory() as session:
            service = AccountService(session)
            session_manager = RedisSessionManager()
            if name == "research_trends":
                account, normalized_platform, resolve_error = await _resolve_account(
                    service,
                    platform=arguments.get("platform"),
                    account_id=arguments.get("account_id"),
                    username=arguments.get("username"),
                )
                if account is None:
                    return {
                        "platform": normalized_platform or arguments.get("platform"),
                        "niche": arguments.get("niche"),
                        "trends": [],
                        "message": resolve_error,
                    }
                await session_manager.hydrate_account(account)
                adapter = get_adapter(
                    account=account,
                    session=account.sessions[0] if account.sessions else None,
                    proxy=account.proxy,
                )
                authenticated = await adapter.authenticate()
                if not authenticated:
                    return {
                        "platform": account.platform.slug,
                        "niche": arguments.get("niche"),
                        "trends": [],
                        "message": getattr(adapter, "last_error", None)
                        or "Authentication failed for active account",
                    }
                trends = await adapter.get_trending(arguments["niche"], limit=20)
                await session.flush()
                await session.commit()
                await session_manager.persist_account_session(account)
                return {
                    "account_id": account.id,
                    "platform": account.platform.slug,
                    "niche": arguments.get("niche"),
                    "trends": [
                        {
                            "title": trend.title,
                            "url": trend.url,
                            "engagement_score": trend.engagement_score,
                            "hashtags": trend.hashtags,
                            "platform_id": trend.platform_id,
                        }
                        for trend in trends
                    ],
                    "message": None,
                }
            elif name == "search_content":
                account, normalized_platform, resolve_error = await _resolve_account(
                    service,
                    platform=arguments.get("platform"),
                    account_id=arguments.get("account_id"),
                    username=arguments.get("username"),
                )
                if account is None:
                    return {
                        "query": arguments.get("query"),
                        "platform": normalized_platform or arguments.get("platform"),
                        "results": [],
                        "message": resolve_error,
                    }
                await session_manager.hydrate_account(account)
                adapter = get_adapter(
                    account=account,
                    session=account.sessions[0] if account.sessions else None,
                    proxy=account.proxy,
                )
                authenticated = await adapter.authenticate()
                if not authenticated:
                    return {
                        "query": arguments.get("query"),
                        "platform": account.platform.slug,
                        "results": [],
                        "message": getattr(adapter, "last_error", None)
                        or "Authentication failed for active account",
                    }
                results = await adapter.search(arguments["query"], limit=10)
                await session.flush()
                await session.commit()
                await session_manager.persist_account_session(account)
                return {
                    "account_id": account.id,
                    "query": arguments.get("query"),
                    "platform": account.platform.slug,
                    "results": [
                        {
                            "platform_id": result.platform_id,
                            "author_username": result.author_username,
                            "text": result.text,
                            "url": result.url,
                            "media_urls": result.media_urls,
                            "likes_count": result.likes_count,
                        }
                        for result in results
                    ],
                    "message": None,
                }
            elif name == "analyze_competitor":
                return {
                    "account_id": arguments.get("account_id"),
                    "competitor_username": arguments.get("competitor_username"),
                    "analysis": {},
                    "message": "Competitor analysis is not implemented yet",
                }
    finally:
        await engine.dispose()
    raise ValueError(f"Unknown tool: {name}")
