import pytest
from unittest.mock import MagicMock, patch
from cryptography.fernet import Fernet

from src.mcp_servers.encryption import encrypt_credentials, decrypt_credentials, generate_key


@pytest.fixture(autouse=True)
def reset_key_cache():
    """Clear the lru_cache between tests so each test gets a clean key state."""
    from src.mcp_servers import encryption
    encryption._load_or_create_key.cache_clear()
    yield
    encryption._load_or_create_key.cache_clear()


@pytest.fixture
def env_key(monkeypatch):
    monkeypatch.setenv("MCP_ENCRYPTION_KEY", Fernet.generate_key().decode())


def test_encrypt_returns_bytes(env_key):
    result = encrypt_credentials("sk_live_test123")
    assert isinstance(result, bytes)
    assert result != b"sk_live_test123"


def test_decrypt_roundtrip(env_key):
    plaintext = "sk_live_test123"
    ciphertext = encrypt_credentials(plaintext)
    assert decrypt_credentials(ciphertext) == plaintext


def test_encrypt_different_outputs(env_key):
    a = encrypt_credentials("same")
    b = encrypt_credentials("same")
    assert a != b


def test_generate_key_is_valid_fernet():
    key = generate_key()
    Fernet(key.encode())


def test_auto_generates_key_when_env_missing(monkeypatch):
    """Without MCP_ENCRYPTION_KEY, a key is generated and persisted to the DB."""
    monkeypatch.delenv("MCP_ENCRYPTION_KEY", raising=False)

    persisted = {}

    mock_row = None

    def mock_get_session():
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = mock_row
        def fake_add(obj):
            persisted["key"] = obj.key
            persisted["value"] = obj.value
        db.add.side_effect = fake_add
        return db

    with patch("src.mcp_servers.db.get_session", mock_get_session):
        result = encrypt_credentials("test-secret")

    assert isinstance(result, bytes)
    assert persisted["key"] == "encryption_key"
    assert len(persisted["value"]) > 0
    Fernet(persisted["value"].encode())  # must be a valid key


def test_uses_persisted_key_on_subsequent_startup(monkeypatch):
    """Simulates a restart: key already in DB, no env var — must use stored key."""
    monkeypatch.delenv("MCP_ENCRYPTION_KEY", raising=False)

    stored_key = Fernet.generate_key().decode()

    mock_row = MagicMock()
    mock_row.value = stored_key

    def mock_get_session():
        db = MagicMock()
        db.query.return_value.filter.return_value.first.return_value = mock_row
        return db

    with patch("src.mcp_servers.db.get_session", mock_get_session):
        plaintext = "my-api-token"
        ciphertext = encrypt_credentials(plaintext)

    # Reset cache and decrypt using the same stored key directly
    from src.mcp_servers import encryption
    encryption._load_or_create_key.cache_clear()

    assert Fernet(stored_key.encode()).decrypt(ciphertext).decode() == plaintext
