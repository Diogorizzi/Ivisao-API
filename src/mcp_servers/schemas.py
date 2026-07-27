from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, field_validator
from enum import Enum


class AuthType(str, Enum):
    none = "none"
    api_key = "api_key"
    oauth = "oauth"
    nango = "nango"


class MCPServerCreate(BaseModel):
    url: str
    label: str
    description: Optional[str] = None
    auth_type: AuthType = AuthType.none
    credentials: Optional[str] = None
    nango_connection_id: Optional[str] = None

    @field_validator("label")
    @classmethod
    def label_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("label cannot be empty")
        if len(v) > 255:
            raise ValueError("label too long (max 255)")
        return v

    @field_validator("url")
    @classmethod
    def url_not_empty(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("url cannot be empty")
        return v


class MCPServerUpdate(BaseModel):
    url: Optional[str] = None
    label: Optional[str] = None
    description: Optional[str] = None
    auth_type: Optional[AuthType] = None
    credentials: Optional[str] = None
    nango_connection_id: Optional[str] = None


class MCPServerResponse(BaseModel):
    id: UUID
    user_id: str
    global_server_id: Optional[UUID] = None
    label: str
    url: str
    description: Optional[str] = None
    auth_type: AuthType
    nango_connection_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MCPServerGlobalResponse(BaseModel):
    id: UUID
    label: str
    url: str
    description: Optional[str] = None
    auth_type: AuthType
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MCPServerListResponse(BaseModel):
    global_servers: List[MCPServerGlobalResponse]
    user_servers: List[MCPServerResponse]
