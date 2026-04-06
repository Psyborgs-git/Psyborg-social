# MCP Server

SocialMind exposes all automation capabilities as MCP (Model Context Protocol) tools, allowing any compatible AI agent — Claude Desktop, custom agents, or other MCP clients — to directly control social media accounts.

---

## Overview

The MCP server runs on port 8001 and is implemented using Anthropic's official Python MCP SDK. It is mounted as a Starlette sub-application inside FastAPI, using HTTP + Server-Sent Events (SSE) as the transport.

```
AI Agent (Claude Desktop / custom agent)
    │
    │  HTTP POST /mcp  (tool calls)
    │  GET  /mcp/sse   (SSE stream for responses)
    ▼
MCP Server (port 8001)
    │
    │  Internal Python function calls
    ▼
SocialMindService (business logic layer)
    │
    ├── Platform Adapters
    ├── DSPy Pipelines
    └── Task Queue (Celery)
```

---

## Server Setup

```python
# socialmind/mcp/server.py
from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import Tool, TextContent, ImageContent
from starlette.applications import Starlette
from starlette.routing import Route, Mount
import mcp.types as types

# Initialize MCP server
app = Server("socialmind")

# Import all tool handlers
from socialmind.mcp.tools import (
    account_tools,
    post_tools,
    engagement_tools,
    research_tools,
    dm_tools,
    campaign_tools,
    analytics_tools,
)

# Register tool groups
for tool_group in [
    account_tools,
    post_tools,
    engagement_tools,
    research_tools,
    dm_tools,
    campaign_tools,
    analytics_tools,
]:
    tool_group.register(app)


# Create SSE transport and mount as Starlette app
def create_mcp_app() -> Starlette:
    sse = SseServerTransport("/mcp/messages")

    async def handle_sse(request):
        async with sse.connect_sse(request.scope, request.receive, request._send) as streams:
            await app.run(streams[0], streams[1], app.create_initialization_options())

    async def handle_messages(request):
        await sse.handle_post_message(request.scope, request.receive, request._send)

    return Starlette(routes=[
        Route("/sse", endpoint=handle_sse),
        Route("/messages", endpoint=handle_messages, methods=["POST"]),
    ])
```

---

## Tools Catalog

### Account Tools

```python
# socialmind/mcp/tools/account_tools.py

@app.list_tools()
async def list_account_tools():
    return [
        Tool(
            name="list_accounts",
            description="List all connected social media accounts with their status",
            inputSchema={
                "type": "object",
                "properties": {
                    "platform": {
                        "type": "string",
                        "description": "Filter by platform (instagram, tiktok, reddit, youtube, facebook, twitter, threads). Omit for all.",
                        "enum": ["instagram", "tiktok", "reddit", "youtube", "facebook", "twitter", "threads"],
                    },
                    "status": {
                        "type": "string",
                        "description": "Filter by account status",
                        "enum": ["active", "paused", "suspended", "warming_up"],
                    }
                }
            }
        ),
        Tool(
            name="get_account_status",
            description="Get detailed status for a specific account including rate limit usage and recent activity",
            inputSchema={
                "type": "object",
                "properties": {
                    "account_id": {"type": "string", "description": "Account UUID"},
                },
                "required": ["account_id"],
            }
        ),
        Tool(
            name="pause_account",
            description="Pause all automation for a specific account",
            inputSchema={
                "type": "object",
                "properties": {
                    "account_id": {"type": "string"},
                    "reason": {"type": "string", "description": "Reason for pausing"},
                },
                "required": ["account_id"],
            }
        ),
        Tool(
            name="resume_account",
            description="Resume automation for a paused account",
            inputSchema={
                "type": "object",
                "properties": {"account_id": {"type": "string"}},
                "required": ["account_id"],
            }
        ),
    ]
```

### Post Tools

```python
Tool(
    name="create_post",
    description=(
        "Generate and publish a post to one or more social media accounts. "
        "The AI will generate content based on the persona and optional prompt. "
        "Supports text, image (AI-generated), and video content."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "account_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of account UUIDs to post from",
            },
            "prompt": {
                "type": "string",
                "description": "Content direction or topic. Leave empty to let AI decide based on trends.",
            },
            "post_type": {
                "type": "string",
                "enum": ["feed", "story", "reel", "thread"],
                "default": "feed",
            },
            "include_image": {
                "type": "boolean",
                "default": True,
                "description": "Whether to generate and attach an AI image",
            },
            "schedule_at": {
                "type": "string",
                "format": "date-time",
                "description": "ISO 8601 datetime to schedule the post. Omit to post immediately.",
            },
            "cross_post": {
                "type": "boolean",
                "default": False,
                "description": "If true, adapt and post to all platforms the accounts belong to",
            },
        },
        "required": ["account_ids"],
    }
),

Tool(
    name="create_post_from_content",
    description="Publish a post with specific pre-written content (no AI generation)",
    inputSchema={
        "type": "object",
        "properties": {
            "account_ids": {"type": "array", "items": {"type": "string"}},
            "text": {"type": "string", "description": "The exact post text"},
            "hashtags": {"type": "array", "items": {"type": "string"}},
            "image_url": {"type": "string", "description": "URL of image to attach (optional)"},
            "schedule_at": {"type": "string", "format": "date-time"},
        },
        "required": ["account_ids", "text"],
    }
),

Tool(
    name="delete_post",
    description="Delete a published post by its record ID",
    inputSchema={
        "type": "object",
        "properties": {
            "post_record_id": {"type": "string"},
        },
        "required": ["post_record_id"],
    }
),
```

### Engagement Tools

```python
Tool(
    name="engage_feed",
    description=(
        "Automatically browse and engage with the feed of an account — "
        "liking, commenting, and following based on persona settings. "
        "This simulates natural human browsing behavior."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "account_id": {"type": "string"},
            "duration_minutes": {
                "type": "integer",
                "description": "How long to engage for",
                "default": 10,
                "minimum": 1,
                "maximum": 60,
            },
            "actions": {
                "type": "array",
                "items": {"type": "string", "enum": ["like", "comment", "follow"]},
                "default": ["like", "comment"],
                "description": "Which engagement actions to take",
            },
        },
        "required": ["account_id"],
    }
),

Tool(
    name="comment_on_post",
    description="Generate and post a comment on a specific post",
    inputSchema={
        "type": "object",
        "properties": {
            "account_id": {"type": "string"},
            "platform_post_url": {"type": "string", "description": "URL of the post to comment on"},
            "comment_intent": {
                "type": "string",
                "enum": ["agree", "question", "compliment", "add_value", "disagree"],
                "default": "add_value",
            },
            "custom_comment": {
                "type": "string",
                "description": "Specific comment text to use (skips AI generation)",
            },
        },
        "required": ["account_id", "platform_post_url"],
    }
),

Tool(
    name="follow_users",
    description="Follow a list of users from a given account",
    inputSchema={
        "type": "object",
        "properties": {
            "account_id": {"type": "string"},
            "usernames": {"type": "array", "items": {"type": "string"}},
            "platform": {"type": "string"},
        },
        "required": ["account_id", "usernames", "platform"],
    }
),
```

### Research Tools

```python
Tool(
    name="research_trends",
    description=(
        "Scrape and analyze trending content for a niche on a platform. "
        "Returns a trend report with content ideas, hashtags, and posting strategy."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "platform": {
                "type": "string",
                "enum": ["instagram", "tiktok", "reddit", "youtube", "twitter"],
            },
            "niche": {"type": "string", "description": "Content niche, e.g., 'fitness', 'crypto', 'cooking'"},
            "limit": {"type": "integer", "default": 20, "description": "Number of trending items to analyze"},
        },
        "required": ["platform", "niche"],
    }
),

Tool(
    name="search_content",
    description="Search for content on a platform using a query string",
    inputSchema={
        "type": "object",
        "properties": {
            "account_id": {"type": "string"},
            "query": {"type": "string"},
            "limit": {"type": "integer", "default": 10},
        },
        "required": ["account_id", "query"],
    }
),

Tool(
    name="analyze_competitor",
    description="Analyze a competitor's account — their posting frequency, top content, engagement rate",
    inputSchema={
        "type": "object",
        "properties": {
            "account_id": {"type": "string", "description": "Your account to use for access"},
            "competitor_username": {"type": "string"},
            "platform": {"type": "string"},
        },
        "required": ["account_id", "competitor_username", "platform"],
    }
),
```

### DM Tools

```python
Tool(
    name="check_dms",
    description="Retrieve unread direct messages for an account",
    inputSchema={
        "type": "object",
        "properties": {
            "account_id": {"type": "string"},
            "unread_only": {"type": "boolean", "default": True},
        },
        "required": ["account_id"],
    }
),

Tool(
    name="respond_to_dms",
    description=(
        "Automatically read and respond to all unread DMs for an account "
        "using the account's AI persona."
    ),
    inputSchema={
        "type": "object",
        "properties": {
            "account_id": {"type": "string"},
            "max_replies": {"type": "integer", "default": 10},
        },
        "required": ["account_id"],
    }
),

Tool(
    name="send_dm",
    description="Send a direct message to a specific user",
    inputSchema={
        "type": "object",
        "properties": {
            "account_id": {"type": "string"},
            "recipient_username": {"type": "string"},
            "message": {"type": "string"},
            "platform": {"type": "string"},
        },
        "required": ["account_id", "recipient_username", "message", "platform"],
    }
),
```

### Campaign Tools

```python
Tool(
    name="create_campaign",
    description="Create a recurring automation campaign for one or more accounts",
    inputSchema={
        "type": "object",
        "properties": {
            "name": {"type": "string"},
            "account_ids": {"type": "array", "items": {"type": "string"}},
            "cron_expression": {
                "type": "string",
                "description": "Cron expression for schedule, e.g., '0 9 * * *' for 9am daily",
            },
            "task_type": {
                "type": "string",
                "enum": ["post", "engage_feed", "respond_dms", "research"],
            },
            "config": {
                "type": "object",
                "description": "Task-specific configuration (prompt, post_type, etc.)",
            },
        },
        "required": ["name", "account_ids", "cron_expression", "task_type"],
    }
),

Tool(
    name="list_campaigns",
    description="List all active automation campaigns",
    inputSchema={"type": "object", "properties": {}}
),

Tool(
    name="pause_campaign",
    description="Pause a campaign (stops creating new tasks)",
    inputSchema={
        "type": "object",
        "properties": {"campaign_id": {"type": "string"}},
        "required": ["campaign_id"],
    }
),
```

### Analytics Tools

```python
Tool(
    name="get_account_analytics",
    description="Get engagement analytics for an account over a time period",
    inputSchema={
        "type": "object",
        "properties": {
            "account_id": {"type": "string"},
            "period": {
                "type": "string",
                "enum": ["24h", "7d", "30d"],
                "default": "7d",
            },
        },
        "required": ["account_id"],
    }
),

Tool(
    name="get_task_logs",
    description="Get recent task execution logs for debugging",
    inputSchema={
        "type": "object",
        "properties": {
            "account_id": {"type": "string"},
            "limit": {"type": "integer", "default": 50},
            "status": {
                "type": "string",
                "enum": ["all", "success", "failed", "running"],
                "default": "all",
            },
        },
        "required": ["account_id"],
    }
),
```

---

## Tool Handler Implementation Pattern

```python
# socialmind/mcp/tools/post_tools.py
from mcp.server import Server
from mcp.types import TextContent
from socialmind.services.post_service import PostService

def register(app: Server):

    @app.call_tool()
    async def create_post(name: str, arguments: dict):
        if name != "create_post":
            return

        service = PostService()
        results = []

        for account_id in arguments["account_ids"]:
            task_id = await service.create_post_task(
                account_id=account_id,
                prompt=arguments.get("prompt", ""),
                post_type=arguments.get("post_type", "feed"),
                include_image=arguments.get("include_image", True),
                schedule_at=arguments.get("schedule_at"),
            )
            results.append({"account_id": account_id, "task_id": task_id})

        summary = f"Created {len(results)} post task(s):\n"
        for r in results:
            summary += f"  - Account {r['account_id']}: Task {r['task_id']}\n"

        return [TextContent(type="text", text=summary)]
```

---

## Connecting from Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "socialmind": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/client-sse",
        "http://localhost:8001/mcp/sse"
      ]
    }
  }
}
```

Or if running remotely, replace `localhost:8001` with your server's address.

---

## Security

The MCP server requires an API key by default. Set `MCP_API_KEY` in your `.env` file. The key is validated via a middleware that checks the `Authorization: Bearer <key>` header on every request.

For local-only use, set `MCP_REQUIRE_AUTH=false` in development.

```python
# socialmind/mcp/middleware.py
class MCPAuthMiddleware:
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            headers = dict(scope["headers"])
            auth = headers.get(b"authorization", b"").decode()
            if not auth.startswith("Bearer ") or auth[7:] != settings.MCP_API_KEY:
                response = Response("Unauthorized", status_code=401)
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)
```
