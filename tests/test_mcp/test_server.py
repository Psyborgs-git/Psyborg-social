from __future__ import annotations

import json

import mcp.types as types
import pytest
from httpx import ASGITransport, AsyncClient
from starlette.testclient import TestClient

from socialmind.config.settings import settings
from socialmind.mcp.app import app
from socialmind.mcp.server import call_tool, list_tools
from socialmind.mcp.tools import account_tools


@pytest.mark.asyncio
async def test_mcp_health_check():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["mcp_path"] == "/mcp"


@pytest.mark.asyncio
async def test_mcp_mounted_health_check():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/mcp/health")

    assert response.status_code == 200
    assert response.json()["messages_path"] == "/mcp/messages"


@pytest.mark.asyncio
async def test_mcp_sse_requires_auth():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/mcp/sse")

    assert response.status_code == 401


def test_mcp_streamable_http_endpoint_exists():
    initialize_params = types.InitializeRequestParams(
        protocolVersion=types.LATEST_PROTOCOL_VERSION,
        capabilities=types.ClientCapabilities(),
        clientInfo=types.Implementation(name="test-client", version="0.1.0"),
    )

    initialize_request = {
        "jsonrpc": "2.0",
        "id": "test-initialize",
        "method": "initialize",
        "params": initialize_params.model_dump(
            by_alias=True,
            mode="json",
            exclude_none=True,
        ),
    }

    headers = {
        "Authorization": f"Bearer {settings.MCP_API_KEY}",
        "Accept": "application/json, text/event-stream",
    }

    with TestClient(app) as client:
        response = client.post(
            "/mcp",
            json=initialize_request,
            headers=headers,
        )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert response.headers.get("mcp-session-id")


@pytest.mark.asyncio
async def test_mcp_list_tools_includes_core_actions():
    tools = await list_tools()
    tool_names = {tool.name for tool in tools}

    assert {
        "list_accounts",
        "create_post",
        "pause_account",
        "add_account",
        "login_account",
        "logout_account",
    } <= tool_names


@pytest.mark.asyncio
async def test_mcp_call_tool_dispatches(monkeypatch):
    async def fake_handle(name: str, arguments: dict) -> dict:
        return {
            "name": name,
            "platform": arguments.get("platform"),
            "ok": True,
        }

    monkeypatch.setattr(account_tools, "handle", fake_handle)

    result = await call_tool("list_accounts", {"platform": "linkedin"})

    assert len(result) == 1
    assert json.loads(result[0].text) == {
        "name": "list_accounts",
        "platform": "linkedin",
        "ok": True,
    }
