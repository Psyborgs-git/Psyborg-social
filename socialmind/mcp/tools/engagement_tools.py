from __future__ import annotations

from mcp.types import Tool

TOOLS: list[Tool] = [
    Tool(
        name="engage_feed",
        description="Engage with the feed of an account (like posts).",
        inputSchema={
            "type": "object",
            "properties": {
                "account_id": {"type": "string"},
                "count": {"type": "integer", "default": 10},
            },
            "required": ["account_id"],
        },
    ),
    Tool(
        name="comment_on_post",
        description="Comment on a specific post.",
        inputSchema={
            "type": "object",
            "properties": {
                "account_id": {"type": "string"},
                "post_url": {"type": "string"},
                "comment_text": {"type": "string"},
            },
            "required": ["account_id", "post_url", "comment_text"],
        },
    ),
    Tool(
        name="follow_users",
        description="Follow a list of usernames.",
        inputSchema={
            "type": "object",
            "properties": {
                "account_id": {"type": "string"},
                "usernames": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["account_id", "usernames"],
        },
    ),
]


async def handle(name: str, arguments: dict) -> dict:
    if name == "engage_feed":
        return {
            "success": True,
            "account_id": arguments.get("account_id"),
            "message": f"Feed engagement queued for {arguments.get('count', 10)} posts",
        }
    elif name == "comment_on_post":
        return {
            "success": True,
            "account_id": arguments.get("account_id"),
            "post_url": arguments.get("post_url"),
            "message": "Comment queued",
        }
    elif name == "follow_users":
        usernames = arguments.get("usernames", [])
        return {
            "success": True,
            "account_id": arguments.get("account_id"),
            "queued_follows": len(usernames),
        }
    raise ValueError(f"Unknown tool: {name}")
