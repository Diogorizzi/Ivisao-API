from functools import lru_cache
from sqlalchemy import create_engine, Engine, text
from sqlalchemy.orm import sessionmaker, Session
from src.config.settings import settings
from src.mcp_servers.models import Base


@lru_cache(maxsize=1)
def _get_engine() -> Engine:
    url = settings.MCP_DB_URL
    if not url:
        raise RuntimeError("MCP_DB_URL is not set")
    return create_engine(url, pool_pre_ping=True)


def get_session() -> Session:
    return sessionmaker(bind=_get_engine(), autocommit=False, autoflush=False)()


def create_tables() -> None:
    if not settings.MCP_DB_URL:
        return
    engine = _get_engine()
    Base.metadata.create_all(bind=engine)
    with engine.connect() as conn:
        conn.execute(text("""
            ALTER TABLE mcp_servers_user
            ADD COLUMN IF NOT EXISTS nango_connection_id VARCHAR(255)
        """))
        conn.commit()
