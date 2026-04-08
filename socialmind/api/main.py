from __future__ import annotations
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from socialmind.api.routers import (
    accounts,
    tasks,
    campaigns,
    analytics,
    auth,
    websocket,
    personas,
    media,
    user,
)
from socialmind.config.settings import settings
from socialmind.config.logging import configure_logging
from socialmind.mcp.middleware import MCPAuthMiddleware
from socialmind.mcp.server import create_mcp_app


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="SocialMind API",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:3000",
            "http://localhost:5173",
            "http://localhost:5174",
            "http://localhost:4174",
            "http://jae.local:5173",
            "http://localhost:8000",
        ],
        allow_origin_regex=r"https?://(localhost|jae\.local)(:\d+)?$",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
    app.include_router(accounts.router, prefix="/api/v1/accounts", tags=["accounts"])
    app.include_router(personas.router, prefix="/api/v1/personas", tags=["personas"])
    app.include_router(media.router, prefix="/api/v1/media", tags=["media"])
    app.include_router(tasks.router, prefix="/api/v1/tasks", tags=["tasks"])
    app.include_router(campaigns.router, prefix="/api/v1/campaigns", tags=["campaigns"])
    app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["analytics"])
    app.include_router(user.router, prefix="/api/v1/user", tags=["user"])
    app.include_router(websocket.router, tags=["websocket"])

    # Mount MCP server
    mcp_app = MCPAuthMiddleware(create_mcp_app())
    app.mount("/mcp", mcp_app)

    @app.get("/health")
    async def health():
        return {"status": "ok", "version": "0.1.0"}

    return app


app = create_app()
