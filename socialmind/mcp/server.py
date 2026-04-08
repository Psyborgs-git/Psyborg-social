from __future__ import annotations

import json
from contextlib import asynccontextmanager

from mcp.server import Server
from mcp.server.sse import SseServerTransport
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from mcp.types import TextContent, Tool
from starlette.applications import Starlette
from starlette.responses import JSONResponse, Response
from starlette.routing import Mount, Route

from socialmind.mcp.tools import (
    account_tools,
    analytics_tools,
    campaign_tools,
    dm_tools,
    engagement_tools,
    post_tools,
    research_tools,
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


def _full_path(scope: dict, path: str) -> str:
    root_path = (scope.get("root_path") or "").rstrip("/")
    normalized_path = path if path.startswith("/") else f"/{path}"
    return f"{root_path}{normalized_path}" if root_path else normalized_path


def create_mcp_app(base_path: str = "") -> Starlette:
    # Retained for backwards compatibility with older call sites; transport
    # endpoints must stay relative so mounted apps do not double-prefix paths.
    _ = base_path

    sse = SseServerTransport("/messages")
    streamable_http = StreamableHTTPSessionManager(mcp_server)

    @asynccontextmanager
    async def lifespan(app: Starlette):
        async with streamable_http.run():
            yield

    async def health(request):
        return JSONResponse(
            {
                "status": "ok",
                "server": "socialmind-mcp",
                "mcp_path": (request.scope.get("root_path") or "") or "/",
                "messages_path": _full_path(request.scope, "/messages"),
            }
        )

    async def handle_sse(request):
        async with sse.connect_sse(
            request.scope, request.receive, request._send
        ) as streams:
            await mcp_server.run(
                streams[0], streams[1], mcp_server.create_initialization_options()
            )
        return Response()

    return Starlette(
        lifespan=lifespan,
        routes=[
            Route("/health", endpoint=health, methods=["GET"]),
            Route("/sse", endpoint=handle_sse, methods=["GET"]),
            Mount("/messages", app=sse.handle_post_message),
            Mount("/", app=streamable_http.handle_request),
        ],
    )
