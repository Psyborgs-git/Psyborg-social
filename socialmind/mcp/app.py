from __future__ import annotations

from socialmind.mcp.middleware import MCPAuthMiddleware
from socialmind.mcp.server import create_mcp_app

_starlette_app = create_mcp_app()
app = MCPAuthMiddleware(_starlette_app)
