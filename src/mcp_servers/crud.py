from typing import List, Optional
from uuid import UUID
from sqlalchemy.orm import Session
from src.mcp_servers.models import MCPServerGlobal, MCPServerUser
from src.mcp_servers.schemas import MCPServerCreate, MCPServerUpdate
from src.mcp_servers.encryption import encrypt_credentials


def get_global_servers(db: Session) -> List[MCPServerGlobal]:
    return db.query(MCPServerGlobal).all()


def get_user_servers(db: Session, user_id: str) -> List[MCPServerUser]:
    return (
        db.query(MCPServerUser)
        .filter(MCPServerUser.user_id == user_id, MCPServerUser.is_deleted == False)
        .all()
    )


def get_user_server_by_id(db: Session, server_id: UUID, user_id: str) -> Optional[MCPServerUser]:
    return (
        db.query(MCPServerUser)
        .filter(
            MCPServerUser.id == server_id,
            MCPServerUser.user_id == user_id,
            MCPServerUser.is_deleted == False,
        )
        .first()
    )


def create_user_server(db: Session, user_id: str, payload: MCPServerCreate) -> MCPServerUser:
    encrypted = None
    if payload.credentials:
        encrypted = encrypt_credentials(payload.credentials)

    server = MCPServerUser(
        user_id=user_id,
        label=payload.label,
        url=payload.url,
        description=payload.description,
        auth_type=payload.auth_type.value,
        encrypted_credentials=encrypted,
        nango_connection_id=payload.nango_connection_id,
    )
    db.add(server)
    db.commit()
    db.refresh(server)
    return server


def update_user_server(
    db: Session, server_id: UUID, user_id: str, payload: MCPServerUpdate
) -> Optional[MCPServerUser]:
    server = get_user_server_by_id(db, server_id, user_id)
    if server is None:
        return None

    if payload.url is not None:
        server.url = payload.url
    if payload.label is not None:
        server.label = payload.label
    if payload.description is not None:
        server.description = payload.description
    if payload.auth_type is not None:
        server.auth_type = payload.auth_type.value
    if payload.credentials is not None:
        server.encrypted_credentials = encrypt_credentials(payload.credentials)
    if payload.nango_connection_id is not None:
        server.nango_connection_id = payload.nango_connection_id

    db.commit()
    db.refresh(server)
    return server


def delete_user_server(db: Session, server_id: UUID, user_id: str) -> Optional[bool]:
    server = get_user_server_by_id(db, server_id, user_id)
    if server is None:
        return None
    server.is_deleted = True
    db.commit()
    return True
