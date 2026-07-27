import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, LargeBinary, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


class MCPConfig(Base):
    """Stores deployment-scoped config — currently just the encryption key."""
    __tablename__ = "mcp_config"

    key = Column(String(128), primary_key=True)
    value = Column(Text, nullable=False)


class MCPServerGlobal(Base):
    __tablename__ = "mcp_servers_global"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    label = Column(String(255), nullable=False, unique=True)
    url = Column(String(2048), nullable=False)
    description = Column(Text, nullable=True)
    auth_type = Column(String(50), nullable=False, default="none")
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)

    user_servers = relationship("MCPServerUser", back_populates="global_server")


class MCPServerUser(Base):
    __tablename__ = "mcp_servers_user"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(String(255), nullable=False, index=True)
    global_server_id = Column(
        UUID(as_uuid=True),
        ForeignKey("mcp_servers_global.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    label = Column(String(255), nullable=False)
    url = Column(String(2048), nullable=False)
    description = Column(Text, nullable=True)
    auth_type = Column(String(50), nullable=False, default="none")
    encrypted_credentials = Column(LargeBinary, nullable=True)
    nango_connection_id = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)
    is_deleted = Column(Boolean, nullable=False, default=False)

    global_server = relationship("MCPServerGlobal", back_populates="user_servers")
