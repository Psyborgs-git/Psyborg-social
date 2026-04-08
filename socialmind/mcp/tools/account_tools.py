from __future__ import annotations

from mcp.types import Tool

TOOLS: list[Tool] = [
    Tool(
        name="add_account",
        description="Add a social media account with credentials for automation.",
        inputSchema={
            "type": "object",
            "properties": {
                "platform": {"type": "string", "description": "Platform slug"},
                "username": {"type": "string", "description": "Primary username"},
                "credentials": {
                    "type": "object",
                    "description": "Credential payload such as password, email, API tokens, cookies, or 2FA secret",
                },
                "proxy_url": {"type": "string", "description": "Optional proxy URL"},
            },
            "required": ["platform", "username", "credentials"],
        },
    ),
    Tool(
        name="login_account",
        description="Authenticate an account against its platform and establish a live session.",
        inputSchema={
            "type": "object",
            "properties": {
                "account_id": {"type": "string", "description": "Account ID"},
            },
            "required": ["account_id"],
        },
    ),
    Tool(
        name="logout_account",
        description="Invalidate a stored live session for an account.",
        inputSchema={
            "type": "object",
            "properties": {
                "account_id": {"type": "string", "description": "Account ID"},
            },
            "required": ["account_id"],
        },
    ),
    Tool(
        name="list_accounts",
        description="List social media accounts, optionally filtered by platform or status.",
        inputSchema={
            "type": "object",
            "properties": {
                "platform": {
                    "type": "string",
                    "description": "Filter by platform slug",
                },
                "status": {"type": "string", "description": "Filter by account status"},
            },
        },
    ),
    Tool(
        name="get_account_status",
        description="Get the current status and details of an account.",
        inputSchema={
            "type": "object",
            "properties": {
                "account_id": {"type": "string", "description": "Account ID"},
            },
            "required": ["account_id"],
        },
    ),
    Tool(
        name="pause_account",
        description="Pause an account from performing automated actions.",
        inputSchema={
            "type": "object",
            "properties": {
                "account_id": {"type": "string", "description": "Account ID"},
                "reason": {"type": "string", "description": "Reason for pausing"},
            },
            "required": ["account_id"],
        },
    ),
    Tool(
        name="resume_account",
        description="Resume a paused account.",
        inputSchema={
            "type": "object",
            "properties": {
                "account_id": {"type": "string", "description": "Account ID"},
            },
            "required": ["account_id"],
        },
    ),
]


async def handle(name: str, arguments: dict) -> dict | list:
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
            try:
                if name == "add_account":
                    account = await service.create_account(
                        platform=arguments["platform"],
                        username=arguments["username"],
                        credentials=arguments["credentials"],
                        proxy_url=arguments.get("proxy_url"),
                    )
                    await session_manager.sync_from_account(account)
                    return {
                        "id": account.id,
                        "username": account.username,
                        "platform_id": account.platform_id,
                        "status": account.status,
                        "display_name": account.display_name,
                    }
                elif name == "login_account":
                    account = await service.get_account(arguments["account_id"])
                    adapter = get_adapter(
                        account=account,
                        session=account.sessions[0] if account.sessions else None,
                        proxy=account.proxy,
                    )
                    authenticated = await adapter.authenticate()
                    if authenticated:
                        await session.flush()
                        await session.commit()
                        await session_manager.persist_account_session(account)
                        return {
                            "success": True,
                            "account_id": account.id,
                            "status": account.status,
                            "session_cached": True,
                            "expires_at": (
                                account.sessions[0].expires_at
                                if account.sessions
                                else None
                            ),
                        }
                    await session.rollback()
                    return {
                        "success": False,
                        "account_id": account.id,
                        "error": getattr(adapter, "last_error", None)
                        or "Authentication failed",
                    }
                elif name == "logout_account":
                    account = await service.get_account(arguments["account_id"])
                    if account.sessions:
                        account.sessions[0].is_valid = False
                        account.sessions[0].invalidation_reason = "manual_logout"
                    await session.commit()
                    await session_manager.invalidate_session(account.id)
                    return {"success": True, "account_id": account.id}
                elif name == "list_accounts":
                    accounts = await service.list_accounts(
                        platform=arguments.get("platform"),
                        status=arguments.get("status"),
                    )
                    return [
                        {
                            "id": a.id,
                            "username": a.username,
                            "platform_id": a.platform_id,
                            "status": a.status,
                            "display_name": a.display_name,
                        }
                        for a in accounts
                    ]
                elif name == "get_account_status":
                    account = await service.get_account(arguments["account_id"])
                    redis_session = await session_manager.get_session(account.id)
                    return {
                        "id": account.id,
                        "username": account.username,
                        "platform_id": account.platform_id,
                        "status": account.status,
                        "display_name": account.display_name,
                        "daily_action_limit": account.daily_action_limit,
                        "warmup_phase": account.warmup_phase,
                        "session_valid": bool(redis_session and redis_session.is_valid),
                        "session_expires_at": (
                            redis_session.expires_at if redis_session else None
                        ),
                    }
                elif name == "pause_account":
                    await service.pause(
                        arguments["account_id"], reason=arguments.get("reason")
                    )
                    return {
                        "success": True,
                        "account_id": arguments["account_id"],
                        "status": "paused",
                    }
                elif name == "resume_account":
                    await service.resume(arguments["account_id"])
                    return {
                        "success": True,
                        "account_id": arguments["account_id"],
                        "status": "active",
                    }
                raise ValueError(f"Unknown tool: {name}")
            except ValueError as exc:
                await session.rollback()
                return {"error": str(exc)}
    finally:
        await engine.dispose()
