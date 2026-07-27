import os
import uuid
from unittest.mock import MagicMock, patch
from cryptography.fernet import Fernet

os.environ["MCP_ENCRYPTION_KEY"] = Fernet.generate_key().decode()
os.environ["MCP_DB_URL"] = "postgresql+psycopg://test"

import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI
from datetime import datetime, timezone

from src.mcp_servers.routes import router
from src.mcp_servers.dependencies import get_user_id
from src.mcp_servers.db import get_session


app = FastAPI()
app.include_router(router)

USER_ID = "user_test_1"

def _override_user():
    return USER_ID

def _make_db_server(user_id=USER_ID, label="Test", url="https://mcp.example.com"):
    from src.mcp_servers.models import MCPServerUser
    s = MCPServerUser()
    s.id = uuid.uuid4()
    s.user_id = user_id
    s.label = label
    s.url = url
    s.auth_type = "none"
    s.description = None
    s.encrypted_credentials = None
    s.is_deleted = False
    s.global_server_id = None
    s.created_at = datetime.now(timezone.utc)
    s.updated_at = datetime.now(timezone.utc)
    return s


@pytest.fixture
def client():
    mock_db = MagicMock()
    app.dependency_overrides[get_user_id] = _override_user
    app.dependency_overrides[get_session] = lambda: mock_db
    yield TestClient(app), mock_db
    app.dependency_overrides.clear()


def test_list_returns_global_and_user_servers(client):
    test_client, mock_db = client
    from src.mcp_servers.models import MCPServerGlobal
    g = MCPServerGlobal()
    g.id = uuid.uuid4()
    g.label = "Global"
    g.url = "https://global.mcp.io"
    g.description = None
    g.auth_type = "none"
    g.created_at = g.updated_at = datetime.now(timezone.utc)

    with patch("src.mcp_servers.routes.crud.get_global_servers", return_value=[g]), \
         patch("src.mcp_servers.routes.crud.get_user_servers", return_value=[_make_db_server()]):
        resp = test_client.get("/api/mcp-servers")

    assert resp.status_code == 200
    data = resp.json()
    assert len(data["global_servers"]) == 1
    assert len(data["user_servers"]) == 1


def test_create_returns_201(client):
    test_client, mock_db = client
    server = _make_db_server()
    with patch("src.mcp_servers.routes.crud.create_user_server", return_value=server):
        resp = test_client.post(
            "/api/mcp-servers",
            json={"url": "https://mcp.example.com", "label": "Test", "auth_type": "none"},
        )
    assert resp.status_code == 201
    assert "id" in resp.json()
    assert "encrypted_credentials" not in resp.json()


def test_delete_returns_204(client):
    test_client, mock_db = client
    server_id = str(uuid.uuid4())
    with patch("src.mcp_servers.routes.crud.delete_user_server", return_value=True):
        resp = test_client.delete(f"/api/mcp-servers/{server_id}")
    assert resp.status_code == 204


def test_delete_not_found_returns_404(client):
    test_client, mock_db = client
    server_id = str(uuid.uuid4())
    with patch("src.mcp_servers.routes.crud.delete_user_server", return_value=None):
        resp = test_client.delete(f"/api/mcp-servers/{server_id}")
    assert resp.status_code == 404


def test_update_returns_200(client):
    test_client, mock_db = client
    server = _make_db_server(label="Updated")
    server_id = str(server.id)
    with patch("src.mcp_servers.routes.crud.update_user_server", return_value=server):
        resp = test_client.patch(
            f"/api/mcp-servers/{server_id}",
            json={"label": "Updated"},
        )
    assert resp.status_code == 200
    assert resp.json()["label"] == "Updated"


def test_missing_user_id_header_returns_401():
    app.dependency_overrides.clear()
    c = TestClient(app)
    resp = c.get("/api/mcp-servers")
    assert resp.status_code == 401
