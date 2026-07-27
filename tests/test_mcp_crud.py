import os
import uuid
import pytest
from unittest.mock import patch, MagicMock
from cryptography.fernet import Fernet

os.environ["MCP_ENCRYPTION_KEY"] = Fernet.generate_key().decode()
os.environ["MCP_DB_URL"] = "postgresql+psycopg://test"

from src.mcp_servers.schemas import MCPServerCreate, MCPServerUpdate, AuthType
from src.mcp_servers import crud


@pytest.fixture
def mock_session():
    return MagicMock()


def _make_server(user_id="user_1", label="Test", url="https://mcp.example.com"):
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
    from datetime import datetime, timezone
    s.created_at = datetime.now(timezone.utc)
    s.updated_at = datetime.now(timezone.utc)
    return s


def test_create_server_no_credentials(mock_session):
    payload = MCPServerCreate(url="https://mcp.example.com", label="Test")
    mock_session.add = MagicMock()
    mock_session.commit = MagicMock()
    mock_session.refresh = MagicMock(side_effect=lambda s: None)

    server = crud.create_user_server(mock_session, "user_1", payload)
    mock_session.add.assert_called_once()
    assert server.encrypted_credentials is None


def test_create_server_encrypts_credentials(mock_session):
    payload = MCPServerCreate(
        url="https://mcp.example.com",
        label="Test",
        auth_type=AuthType.api_key,
        credentials="sk_live_secret",
    )
    mock_session.add = MagicMock()
    mock_session.commit = MagicMock()
    mock_session.refresh = MagicMock(side_effect=lambda s: None)

    server = crud.create_user_server(mock_session, "user_1", payload)
    assert server.encrypted_credentials is not None
    assert server.encrypted_credentials != b"sk_live_secret"


def test_get_user_servers_filters_deleted(mock_session):
    alive = _make_server()
    dead = _make_server(label="Dead")
    dead.is_deleted = True

    mock_query = MagicMock()
    mock_session.query.return_value = mock_query
    mock_query.filter.return_value = mock_query
    mock_query.all.return_value = [alive]

    result = crud.get_user_servers(mock_session, "user_1")
    assert len(result) == 1
    assert result[0].label == "Test"


def test_delete_server_soft_deletes(mock_session):
    server = _make_server()
    mock_query = MagicMock()
    mock_session.query.return_value = mock_query
    mock_query.filter.return_value = mock_query
    mock_query.first.return_value = server

    result = crud.delete_user_server(mock_session, server.id, "user_1")
    assert result is True
    assert server.is_deleted is True
    mock_session.commit.assert_called_once()


def test_delete_server_wrong_owner_returns_none(mock_session):
    server = _make_server(user_id="owner")
    mock_query = MagicMock()
    mock_session.query.return_value = mock_query
    mock_query.filter.return_value = mock_query
    mock_query.first.return_value = None

    result = crud.delete_user_server(mock_session, server.id, "other_user")
    assert result is None


def test_create_server_stores_nango_connection_id(mock_session):
    payload = MCPServerCreate(
        url="https://mcp.nango.dev/google-drive",
        label="Google Drive",
        auth_type=AuthType.nango,
        nango_connection_id="conn_xyz789",
    )
    mock_session.add = MagicMock()
    mock_session.commit = MagicMock()
    mock_session.refresh = MagicMock(side_effect=lambda s: None)

    server = crud.create_user_server(mock_session, "user_test", payload)
    assert server.nango_connection_id == "conn_xyz789"
    assert server.auth_type == "nango"
    assert server.encrypted_credentials is None
