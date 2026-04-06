from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


class MCPAuthMiddleware(BaseHTTPMiddleware):
    """Validates Bearer token on all MCP server requests."""

    async def dispatch(self, request: Request, call_next):
        if request.url.path in ("/health", "/docs", "/openapi.json"):
            return await call_next(request)

        from socialmind.config.settings import settings

        if not settings.MCP_REQUIRE_AUTH:
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return Response("Unauthorized", status_code=401)

        token = auth_header[7:]
        if token != settings.MCP_API_KEY:
            return Response("Unauthorized", status_code=401)

        return await call_next(request)
