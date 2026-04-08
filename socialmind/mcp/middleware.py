from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


_EXEMPT_SUFFIXES = ("/health", "/docs", "/openapi.json")


def _is_exempt_path(path: str) -> bool:
    normalized = path.rstrip("/") or "/"
    return any(
        normalized == suffix or normalized.endswith(suffix)
        for suffix in _EXEMPT_SUFFIXES
    )


class MCPAuthMiddleware(BaseHTTPMiddleware):
    """Validates Bearer token on all MCP server requests."""

    async def dispatch(self, request: Request, call_next):
        if request.method == "OPTIONS" or _is_exempt_path(request.url.path):
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
