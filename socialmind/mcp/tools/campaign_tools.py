from __future__ import annotations

from mcp.types import Tool

TOOLS: list[Tool] = [
    Tool(
        name="create_campaign",
        description="Create a new automation campaign.",
        inputSchema={
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "description": {"type": "string"},
                "account_ids": {"type": "array", "items": {"type": "string"}},
                "cron_expression": {"type": "string"},
            },
            "required": ["name"],
        },
    ),
    Tool(
        name="list_campaigns",
        description="List all campaigns.",
        inputSchema={
            "type": "object",
            "properties": {
                "active_only": {"type": "boolean", "default": False},
            },
        },
    ),
    Tool(
        name="pause_campaign",
        description="Pause an active campaign.",
        inputSchema={
            "type": "object",
            "properties": {
                "campaign_id": {"type": "string"},
            },
            "required": ["campaign_id"],
        },
    ),
]


async def handle(name: str, arguments: dict) -> dict | list:
    from socialmind.config.settings import settings
    from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
    from socialmind.services.campaign_service import CampaignService

    engine = create_async_engine(settings.DATABASE_URL)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with factory() as session:
            service = CampaignService(session)
            if name == "create_campaign":
                campaign = await service.create_campaign(
                    name=arguments["name"],
                    description=arguments.get("description"),
                    cron_expression=arguments.get("cron_expression"),
                    account_ids=arguments.get("account_ids", []),
                    config={},
                )
                return {
                    "id": campaign.id,
                    "name": campaign.name,
                    "is_active": campaign.is_active,
                }
            elif name == "list_campaigns":
                campaigns = await service.list_campaigns(
                    active_only=arguments.get("active_only", False)
                )
                return [
                    {"id": c.id, "name": c.name, "is_active": c.is_active}
                    for c in campaigns
                ]
            elif name == "pause_campaign":
                await service.pause(arguments["campaign_id"])
                return {"success": True, "campaign_id": arguments["campaign_id"], "status": "paused"}
            raise ValueError(f"Unknown tool: {name}")
    finally:
        await engine.dispose()
