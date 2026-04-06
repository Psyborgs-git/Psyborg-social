from __future__ import annotations

import json

from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.types import Tool, TextContent
from starlette.applications import Starlette
from starlette.routing import Route

from socialmind.mcp.tools import (
    account_tools,
    post_tools,
    engagement_tools,
    research_tools,
    dm_tools,
    campaign_tools,
    analytics_tools,
)

mcp_server = Server("socialmind")

ALL_MODULES = [
    account_tools,
    post_tools,
    engagement_tools,
    research_tools,
    dm_tools,
    campaign_tools,
    analytics_tools,
]


@mcp_server.list_tools()
async def list_tools() -> list[Tool]:
    tools = []
    for module in ALL_MODULES:
        tools.extend(module.TOOLS)
    return tools


@mcp_server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    for module in ALL_MODULES:
        if any(t.name == name for t in module.TOOLS):
            result = await module.handle(name, arguments)
            return [TextContent(type="text", text=json.dumps(result, default=str))]
    raise ValueError(f"Unknown tool: {name}")


def create_mcp_app() -> Starlette:
    sse = SseServerTransport("/mcp/messages")

    async def handle_sse(request):
        async with sse.connect_sse(
            request.scope, request.receive, request._send
        ) as streams:
            await mcp_server.run(
                streams[0], streams[1], mcp_server.create_initialization_options()
            )

    async def handle_messages(request):
        await sse.handle_post_message(request.scope, request.receive, request._send)

    return Starlette(
        routes=[
            Route("/sse", endpoint=handle_sse),
            Route("/messages", endpoint=handle_messages, methods=["POST"]),
        ]
    )
