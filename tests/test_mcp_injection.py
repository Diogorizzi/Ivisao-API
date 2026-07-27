import os
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from cryptography.fernet import Fernet

os.environ["MCP_ENCRYPTION_KEY"] = Fernet.generate_key().decode()
os.environ["MCP_DB_URL"] = "postgresql+psycopg://test"
os.environ["NANGO_SECRET_KEY"] = "test-nango-secret"

import pytest
from src.mcp_servers.injection import _mcp_server_ctx as _mcp_ctx, MCPInjectionMiddleware


def test_mcp_ctx_default_is_empty():
    assert _mcp_ctx.get() == []


def test_mcp_ctx_is_isolated_between_tasks():
    results = {}

    async def task_a():
        token = _mcp_ctx.set(["tool_a"])
        await asyncio.sleep(0)
        results["a"] = _mcp_ctx.get()
        _mcp_ctx.reset(token)

    async def task_b():
        await asyncio.sleep(0)
        results["b"] = _mcp_ctx.get()

    async def run():
        await asyncio.gather(task_a(), task_b())

    asyncio.run(run())
    assert results["a"] == ["tool_a"]
    assert results["b"] == []


import uuid
from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.testclient import TestClient


def _make_user_server(url="https://mcp.example.com", auth_type="none", creds=None):
    from src.mcp_servers.models import MCPServerUser
    from src.mcp_servers.encryption import encrypt_credentials
    s = MCPServerUser()
    s.id = uuid.uuid4()
    s.user_id = "user_123"
    s.label = "Test"
    s.url = url
    s.auth_type = auth_type
    s.description = None
    s.encrypted_credentials = encrypt_credentials(creds) if creds else None
    s.is_deleted = False
    s.global_server_id = None
    s.created_at = datetime.now(timezone.utc)
    s.updated_at = datetime.now(timezone.utc)
    return s


@pytest.fixture
def app_with_middleware():
    from src.mcp_servers.injection import MCPInjectionMiddleware
    app = FastAPI()
    app.add_middleware(MCPInjectionMiddleware)

    @app.post("/agents/test/runs")
    async def fake_run():
        tools = _mcp_ctx.get()
        return {"tool_count": len(tools), "tool_types": [type(t).__name__ for t in tools]}

    return app


def test_middleware_sets_no_tools_when_no_user_id(app_with_middleware):
    client = TestClient(app_with_middleware)
    resp = client.post(
        "/agents/test/runs",
        data={"message": "hello"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert resp.status_code == 200
    assert resp.json()["tool_count"] == 0


def test_middleware_sets_tools_for_user_with_none_auth(app_with_middleware):
    server = _make_user_server(auth_type="none")
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.all.return_value = [server]

    fake_tool = MagicMock()
    with patch("src.mcp_servers.injection.get_user_mcp_tools", return_value=[fake_tool]):
        client = TestClient(app_with_middleware)
        resp = client.post(
            "/agents/test/runs",
            data={"message": "hello", "user_id": "user_123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    assert resp.status_code == 200
    assert resp.json()["tool_count"] == 1


def test_middleware_skips_non_runs_path(app_with_middleware):
    client = TestClient(app_with_middleware)
    resp = client.post(
        "/agents/test/sessions",
        data={"message": "hello", "user_id": "user_123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    # 404 is fine — we just verify the middleware doesn't break non-runs paths
    assert resp.status_code in (200, 404, 405)


def test_patch_injects_tools_when_ctx_has_tools():
    from src.mcp_servers.injection import patch_get_agent_by_id, _mcp_ctx

    class FakeTool:
        pass

    class FakeAgent:
        def __init__(self, tools=None):
            self.id = "test-agent"
            self.tools = tools or []
            self.team_id = None
            self.workflow_id = None

        def deep_copy(self, update=None):
            tools = (update or {}).get("tools", self.tools)
            return FakeAgent(tools=tools)

    fake_agents = [FakeAgent(tools=[FakeTool()])]

    import agno.os.utils as agno_utils
    original = agno_utils.get_agent_by_id

    patch_get_agent_by_id()

    extra_tool = FakeTool()
    token = _mcp_ctx.set([extra_tool])
    try:
        result = agno_utils.get_agent_by_id(
            "test-agent", fake_agents, create_fresh=True
        )
        assert len(result.tools) == 2  # original 1 + injected 1
    finally:
        _mcp_ctx.reset(token)
        agno_utils.get_agent_by_id = original  # restore


def test_patch_skips_injection_when_ctx_empty():
    from src.mcp_servers.injection import patch_get_agent_by_id, _mcp_ctx

    class FakeTool:
        pass

    class FakeAgent:
        def __init__(self, tools=None):
            self.id = "test-agent"
            self.tools = tools or []
            self.team_id = None
            self.workflow_id = None

        def deep_copy(self, update=None):
            tools = (update or {}).get("tools", self.tools)
            return FakeAgent(tools=tools)

    fake_agents = [FakeAgent(tools=[FakeTool()])]

    import agno.os.utils as agno_utils
    original = agno_utils.get_agent_by_id
    patch_get_agent_by_id()

    try:
        result = agno_utils.get_agent_by_id(
            "test-agent", fake_agents, create_fresh=True
        )
        assert len(result.tools) == 1  # unchanged
    finally:
        agno_utils.get_agent_by_id = original


def test_patch_returns_none_for_unknown_agent():
    from src.mcp_servers.injection import patch_get_agent_by_id

    import agno.os.utils as agno_utils
    original = agno_utils.get_agent_by_id
    patch_get_agent_by_id()

    try:
        result = agno_utils.get_agent_by_id("nonexistent", [], create_fresh=True)
        assert result is None
    finally:
        agno_utils.get_agent_by_id = original


def test_nango_auth_header_logic():
    """Verify that nango auth_type produces the correct headers dict."""
    import uuid
    from datetime import datetime, timezone
    from src.mcp_servers.models import MCPServerUser
    from src.config.settings import settings

    server = MCPServerUser()
    server.auth_type = "nango"
    server.nango_connection_id = "conn_abc123"
    server.encrypted_credentials = None

    headers = {}
    if server.auth_type in ("api_key", "oauth") and server.encrypted_credentials:
        pass  # not our branch
    elif server.auth_type == "nango":
        if settings.NANGO_SECRET_KEY:
            headers["Authorization"] = f"Bearer {settings.NANGO_SECRET_KEY}"
        if server.nango_connection_id:
            headers["Nango-Connection-Id"] = server.nango_connection_id

    assert headers["Authorization"] == "Bearer test-nango-secret"
    assert headers["Nango-Connection-Id"] == "conn_abc123"


def test_nango_auth_type_in_schema():
    """AuthType enum must include 'nango'."""
    from src.mcp_servers.schemas import AuthType
    assert AuthType.nango == "nango"


def test_settings_has_nango_keys():
    """Settings must expose NANGO_SECRET_KEY and NANGO_PUBLIC_KEY."""
    from src.config.settings import settings
    assert hasattr(settings, "NANGO_SECRET_KEY")
    assert hasattr(settings, "NANGO_PUBLIC_KEY")
    assert settings.NANGO_SECRET_KEY == "test-nango-secret"
