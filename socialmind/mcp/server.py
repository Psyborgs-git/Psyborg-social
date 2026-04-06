from __future__ import annotations

from fastapi import FastAPI
from socialmind.mcp.middleware import MCPAuthMiddleware

mcp_app = FastAPI(title="SocialMind MCP Server")
mcp_app.add_middleware(MCPAuthMiddleware)


@mcp_app.get("/health")
async def health() -> dict:
    return {"status": "ok"}
