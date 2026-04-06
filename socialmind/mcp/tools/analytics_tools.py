from __future__ import annotations

from mcp.types import Tool

TOOLS: list[Tool] = [
    Tool(
        name="get_account_analytics",
        description="Get analytics and rate limit usage for an account.",
        inputSchema={
            "type": "object",
            "properties": {"account_id": {"type": "string"}},
            "required": ["account_id"],
        },
    ),
    Tool(
        name="get_task_logs",
        description="Get logs for a specific task.",
        inputSchema={
            "type": "object",
            "properties": {"task_id": {"type": "string"}},
            "required": ["task_id"],
        },
    ),
]


async def handle(name: str, arguments: dict) -> dict | list:
    from socialmind.config.settings import settings
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

    engine = create_async_engine(settings.DATABASE_URL)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with factory() as session:
            if name == "get_account_analytics":
                from socialmind.services.account_service import AccountService
                service = AccountService(session)
                usage = await service.get_rate_limit_usage(arguments["account_id"])
                return {"account_id": arguments["account_id"], "rate_limit_usage": usage}
            elif name == "get_task_logs":
                from socialmind.repositories.task_repository import TaskRepository
                repo = TaskRepository(session)
                logs = await repo.get_logs(arguments["task_id"])
                return [
                    {"id": l.id, "level": l.level, "message": l.message, "timestamp": str(l.timestamp)}
                    for l in logs
                ]
            raise ValueError(f"Unknown tool: {name}")
    finally:
        await engine.dispose()
