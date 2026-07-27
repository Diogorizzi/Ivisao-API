from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.mcp_servers import crud
from src.mcp_servers.db import get_session
from src.mcp_servers.dependencies import get_user_id
from src.mcp_servers.schemas import (
    MCPServerCreate,
    MCPServerGlobalResponse,
    MCPServerListResponse,
    MCPServerResponse,
    MCPServerUpdate,
)

router = APIRouter(prefix="/api/mcp-servers", tags=["MCP Servers"])


@router.get("", response_model=MCPServerListResponse)
def list_mcp_servers(
    user_id: Annotated[str, Depends(get_user_id)],
    db: Annotated[Session, Depends(get_session)],
):
    global_servers = crud.get_global_servers(db)
    user_servers = crud.get_user_servers(db, user_id)
    return MCPServerListResponse(
        global_servers=[MCPServerGlobalResponse.model_validate(s) for s in global_servers],
        user_servers=[MCPServerResponse.model_validate(s) for s in user_servers],
    )


@router.post("", response_model=MCPServerResponse, status_code=status.HTTP_201_CREATED)
def create_mcp_server(
    payload: MCPServerCreate,
    user_id: Annotated[str, Depends(get_user_id)],
    db: Annotated[Session, Depends(get_session)],
):
    server = crud.create_user_server(db, user_id, payload)
    return MCPServerResponse.model_validate(server)


@router.patch("/{server_id}", response_model=MCPServerResponse)
def update_mcp_server(
    server_id: UUID,
    payload: MCPServerUpdate,
    user_id: Annotated[str, Depends(get_user_id)],
    db: Annotated[Session, Depends(get_session)],
):
    server = crud.update_user_server(db, server_id, user_id, payload)
    if server is None:
        raise HTTPException(status_code=404, detail="Server not found")
    return MCPServerResponse.model_validate(server)


@router.delete("/{server_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_mcp_server(
    server_id: UUID,
    user_id: Annotated[str, Depends(get_user_id)],
    db: Annotated[Session, Depends(get_session)],
):
    result = crud.delete_user_server(db, server_id, user_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Server not found")


@router.get("/global", response_model=list[MCPServerGlobalResponse])
def list_global_servers(db: Annotated[Session, Depends(get_session)]):
    return [MCPServerGlobalResponse.model_validate(s) for s in crud.get_global_servers(db)]
