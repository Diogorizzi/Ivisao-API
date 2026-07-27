import logging
import os
from functools import lru_cache

from cryptography.fernet import Fernet

log = logging.getLogger(__name__)

_CONFIG_KEY = "encryption_key"


@lru_cache(maxsize=1)
def _load_or_create_key() -> str:
    """
    Returns the Fernet key for this deployment.

    Priority:
      1. MCP_ENCRYPTION_KEY env var (set explicitly → always wins)
      2. Key stored in mcp_config table (persisted from a previous startup)
      3. Generate a new key, persist it, and use it

    Result is cached in-process so the DB is only hit once per startup.
    """
    env_key = os.getenv("MCP_ENCRYPTION_KEY", "").strip()
    if env_key:
        return env_key

    # Lazy import to avoid circular deps at module load time
    from src.mcp_servers.db import get_session
    from src.mcp_servers.models import MCPConfig

    db = get_session()
    try:
        row = db.query(MCPConfig).filter(MCPConfig.key == _CONFIG_KEY).first()
        if row:
            return row.value

        new_key = Fernet.generate_key().decode()
        db.add(MCPConfig(key=_CONFIG_KEY, value=new_key))
        db.commit()
        log.info("[MCP] Generated and persisted new encryption key")
        return new_key
    finally:
        db.close()


def _get_fernet() -> Fernet:
    return Fernet(_load_or_create_key().encode())


def encrypt_credentials(plaintext: str) -> bytes:
    return _get_fernet().encrypt(plaintext.encode())


def decrypt_credentials(ciphertext: bytes) -> str:
    return _get_fernet().decrypt(ciphertext).decode()


def generate_key() -> str:
    return Fernet.generate_key().decode()
