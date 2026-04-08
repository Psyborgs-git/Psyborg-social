from __future__ import annotations

from mcp.types import Tool

TOOLS: list[Tool] = [
    Tool(
        name="create_post",
        description="Create a new post task for a social media account.",
        inputSchema={
            "type": "object",
            "properties": {
                "account_id": {"type": "string", "description": "Account ID"},
                "prompt": {"type": "string", "description": "Content prompt for AI generation"},
                "post_type": {"type": "string", "default": "feed", "description": "Post type"},
                "include_image": {"type": "boolean", "default": True},
                "schedule_at": {"type": "string", "description": "ISO datetime to schedule at"},
            },
            "required": ["account_id", "prompt"],
        },
    ),
    Tool(
        name="delete_post",
        description="Delete a post by ID.",
        inputSchema={
            "type": "object",
            "properties": {
                "account_id": {"type": "string"},
                "post_id": {"type": "string"},
            },
            "required": ["account_id", "post_id"],
        },
    ),
]


async def handle(name: str, arguments: dict) -> dict:
    if name == "delete_post":
        return {"success": False, "message": "Delete not implemented via API"}

    if name == "create_post":
        from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

        from socialmind.config.settings import settings
        from socialmind.services.post_service import PostService

        engine = create_async_engine(settings.DATABASE_URL)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        try:
            async with factory() as session:
                service = PostService(session)
                task = await service.create_post_task(
                    account_id=arguments["account_id"],
                    prompt=arguments["prompt"],
                    post_type=arguments.get("post_type", "feed"),
                    include_image=arguments.get("include_image", True),
                    schedule_at=arguments.get("schedule_at"),
                )
                return {
                    "success": True,
                    "task_id": task.id,
                    "status": task.status,
                }
        finally:
            await engine.dispose()

    raise ValueError(f"Unknown tool: {name}")
