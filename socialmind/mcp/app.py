from __future__ import annotations

from contextlib import asynccontextmanager

from mcp.server.sse import SseServerTransport
from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
from starlette.applications import Starlette
from starlette.responses import JSONResponse, Response
from starlette.routing import Mount, Route

from socialmind.mcp.middleware import MCPAuthMiddleware
from socialmind.mcp.server import mcp_server


class _ASGIEndpointAdapter:
    def __init__(self, handler):
        self._handler = handler

    async def __call__(self, scope, receive, send):
        await self._handler(scope, receive, send)


async def health(request):
    return JSONResponse(
        {
            "status": "ok",
            "server": "socialmind-mcp",
            "mcp_path": "/mcp",
            "messages_path": "/mcp/messages",
        }
    )


sse = SseServerTransport("/mcp/messages")
streamable_http = StreamableHTTPSessionManager(mcp_server)


@asynccontextmanager
async def lifespan(app: Starlette):
    async with streamable_http.run():
        yield


async def mounted_health(request):
    return JSONResponse(
        {
            "status": "ok",
            "server": "socialmind-mcp",
            "mcp_path": "/mcp",
            "messages_path": "/mcp/messages",
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


_starlette_app = Starlette(
    lifespan=lifespan,
    routes=[
        Route("/health", endpoint=health, methods=["GET"]),
        Route("/mcp/health", endpoint=mounted_health, methods=["GET"]),
        Route("/mcp/sse", endpoint=handle_sse, methods=["GET"]),
        Mount("/mcp/messages", app=sse.handle_post_message),
        Route(
            "/mcp",
            endpoint=_ASGIEndpointAdapter(streamable_http.handle_request),
            methods=["GET", "POST", "DELETE"],
        ),
        Mount("/mcp", app=streamable_http.handle_request),
    ],
)
_starlette_app.router.redirect_slashes = False
app = MCPAuthMiddleware(_starlette_app)
