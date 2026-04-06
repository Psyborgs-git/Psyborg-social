from __future__ import annotations

from mcp.types import Tool

TOOLS: list[Tool] = [
    Tool(
        name="list_accounts",
        description="List social media accounts, optionally filtered by platform or status.",
        inputSchema={
            "type": "object",
            "properties": {
                "platform": {"type": "string", "description": "Filter by platform slug"},
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
    from socialmind.config.settings import settings
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from socialmind.services.account_service import AccountService

    engine = create_async_engine(settings.DATABASE_URL)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with factory() as session:
            service = AccountService(session)
            if name == "list_accounts":
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
                if account is None:
                    return {"error": "Account not found"}
                return {
                    "id": account.id,
                    "username": account.username,
                    "platform_id": account.platform_id,
                    "status": account.status,
                    "display_name": account.display_name,
                    "daily_action_limit": account.daily_action_limit,
                    "warmup_phase": account.warmup_phase,
                }
            elif name == "pause_account":
                await service.pause(arguments["account_id"], reason=arguments.get("reason"))
                return {"success": True, "account_id": arguments["account_id"], "status": "paused"}
            elif name == "resume_account":
                await service.resume(arguments["account_id"])
                return {"success": True, "account_id": arguments["account_id"], "status": "active"}
            raise ValueError(f"Unknown tool: {name}")
    finally:
        await engine.dispose()
