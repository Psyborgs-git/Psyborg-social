from __future__ import annotations

from mcp.types import Tool

TOOLS: list[Tool] = [
    Tool(
        name="check_dms",
        description="Check direct messages for an account.",
        inputSchema={
            "type": "object",
            "properties": {
                "account_id": {"type": "string"},
                "limit": {"type": "integer", "default": 10},
            },
            "required": ["account_id"],
        },
    ),
    Tool(
        name="respond_to_dms",
        description="Respond to a specific DM.",
        inputSchema={
            "type": "object",
            "properties": {
                "account_id": {"type": "string"},
                "dm_id": {"type": "string"},
                "message": {"type": "string"},
            },
            "required": ["account_id", "dm_id", "message"],
        },
    ),
    Tool(
        name="send_dm",
        description="Send a direct message to a user.",
        inputSchema={
            "type": "object",
            "properties": {
                "account_id": {"type": "string"},
                "recipient_username": {"type": "string"},
                "message": {"type": "string"},
            },
            "required": ["account_id", "recipient_username", "message"],
        },
    ),
]


async def handle(name: str, arguments: dict) -> dict:
    if name == "check_dms":
        return {
            "account_id": arguments.get("account_id"),
            "dms": [],
            "message": "DM access requires live platform session",
        }
    elif name == "respond_to_dms":
        return {
            "account_id": arguments.get("account_id"),
            "dm_id": arguments.get("dm_id"),
            "success": False,
            "message": "DM response requires live platform session",
        }
    elif name == "send_dm":
        return {
            "account_id": arguments.get("account_id"),
            "recipient_username": arguments.get("recipient_username"),
            "success": False,
            "message": "Sending DMs requires live platform session",
        }
    raise ValueError(f"Unknown tool: {name}")
