# MCP Servers Configuration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add REST API endpoints to manage user-specific and global MCP server configurations, with Fernet-encrypted credentials stored in a separate Neon PostgreSQL database.

**Architecture:** A new `src/mcp_servers/` module provides SQLAlchemy models, Pydantic schemas, CRUD helpers, and a FastAPI router registered at `/api/mcp-servers`. User identity comes from the `x-user-id` request header (sent by the Next.js proxy layer), matching the pattern already used by `require_bearer_token`. Credentials are encrypted with Fernet before storage and never returned in API responses.

**Tech Stack:** FastAPI, SQLAlchemy (async, psycopg driver), Pydantic v2, `cryptography` (Fernet), pytest + pytest-asyncio

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `src/mcp_servers/__init__.py` | Create | Package marker |
| `src/mcp_servers/encryption.py` | Create | Fernet encrypt/decrypt helpers |
| `src/mcp_servers/models.py` | Create | SQLAlchemy ORM models |
| `src/mcp_servers/schemas.py` | Create | Pydantic request/response schemas |
| `src/mcp_servers/db.py` | Create | Async engine + session factory + table creation |
| `src/mcp_servers/crud.py` | Create | CRUD operations |
| `src/mcp_servers/dependencies.py` | Create | `get_user_id` FastAPI dependency |
| `src/mcp_servers/routes.py` | Create | FastAPI router with 5 endpoints |
| `src/config/settings.py` | Modify | Add `MCP_DB_URL` and `MCP_ENCRYPTION_KEY` |
| `src/app.py` | Modify | Register mcp_servers router |
| `tests/test_mcp_encryption.py` | Create | Unit tests for encryption |
| `tests/test_mcp_crud.py` | Create | Integration tests for CRUD |
| `tests/test_mcp_routes.py` | Create | Route-level tests |

---

## Task 1: Add settings for MCP database and encryption key

**Files:**
- Modify: `src/config/settings.py`

- [ ] **Step 1: Install the `cryptography` package**

```bash
uv add cryptography
```

Expected: `pyproject.toml` updated with `cryptography>=...`.

- [ ] **Step 2: Add the two new settings fields**

Open [src/config/settings.py](src/config/settings.py) and add after the `NEO4J_PASSWORD` line:

```python
    # MCP Servers — separate Neon DB + encryption key
    MCP_DB_URL: Optional[str] = None  # postgresql+psycopg://...
    MCP_ENCRYPTION_KEY: Optional[str] = None  # Fernet key (base64, 32 bytes)
```

- [ ] **Step 3: Verify settings load**

```bash
python -c "from src.config.settings import settings; print(settings.MCP_DB_URL, settings.MCP_ENCRYPTION_KEY)"
```

Expected output: `None None`

- [ ] **Step 4: Add placeholder vars to .env**

Add these two lines to `.env` (do NOT fill the values yet — just the keys):

```
MCP_DB_URL=
MCP_ENCRYPTION_KEY=
```

- [ ] **Step 5: Commit**

```bash
git add src/config/settings.py .env pyproject.toml
git commit -m "feat(mcp): add MCP_DB_URL and MCP_ENCRYPTION_KEY settings"
```

---

## Task 2: Encryption utilities

**Files:**
- Create: `src/mcp_servers/__init__.py`
- Create: `src/mcp_servers/encryption.py`
- Create: `tests/test_mcp_encryption.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_mcp_encryption.py`:

```python
import os
import pytest
from cryptography.fernet import Fernet

os.environ["MCP_ENCRYPTION_KEY"] = Fernet.generate_key().decode()

from src.mcp_servers.encryption import encrypt_credentials, decrypt_credentials, generate_key


def test_encrypt_returns_bytes():
    result = encrypt_credentials("sk_live_test123")
    assert isinstance(result, bytes)
    assert result != b"sk_live_test123"


def test_decrypt_roundtrip():
    plaintext = "sk_live_test123"
    ciphertext = encrypt_credentials(plaintext)
    assert decrypt_credentials(ciphertext) == plaintext


def test_encrypt_different_outputs():
    # Fernet uses random IV — same plaintext yields different ciphertext
    a = encrypt_credentials("same")
    b = encrypt_credentials("same")
    assert a != b


def test_generate_key_is_valid_fernet():
    key = generate_key()
    # Should not raise
    Fernet(key.encode())


def test_missing_key_raises():
    original = os.environ.pop("MCP_ENCRYPTION_KEY", None)
    try:
        import importlib, src.mcp_servers.encryption as enc
        importlib.reload(enc)
        with pytest.raises(RuntimeError, match="MCP_ENCRYPTION_KEY"):
            enc.encrypt_credentials("test")
    finally:
        if original:
            os.environ["MCP_ENCRYPTION_KEY"] = original
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_mcp_encryption.py -v
```

Expected: `ModuleNotFoundError` — `src/mcp_servers` does not exist yet.

- [ ] **Step 3: Create package marker**

Create `src/mcp_servers/__init__.py` (empty file):

```python
```

- [ ] **Step 4: Implement encryption module**

Create `src/mcp_servers/encryption.py`:

```python
import os
from cryptography.fernet import Fernet


def _get_fernet() -> Fernet:
    key = os.getenv("MCP_ENCRYPTION_KEY", "")
    if not key:
        raise RuntimeError("MCP_ENCRYPTION_KEY is not set")
    return Fernet(key.encode())


def encrypt_credentials(plaintext: str) -> bytes:
    return _get_fernet().encrypt(plaintext.encode())


def decrypt_credentials(ciphertext: bytes) -> str:
    return _get_fernet().decrypt(ciphertext).decode()


def generate_key() -> str:
    return Fernet.generate_key().decode()
```

- [ ] **Step 5: Run tests — all must pass**

```bash
pytest tests/test_mcp_encryption.py -v
```

Expected: 5 passed.

- [ ] **Step 6: Commit**

```bash
git add src/mcp_servers/__init__.py src/mcp_servers/encryption.py tests/test_mcp_encryption.py
git commit -m "feat(mcp): add Fernet encryption utilities with tests"
```

---

## Task 3: SQLAlchemy models and database session

**Files:**
- Create: `src/mcp_servers/models.py`
- Create: `src/mcp_servers/db.py`

- [ ] **Step 1: Create models**

Create `src/mcp_servers/models.py`:

```python
import uuid
from datetime import datetime, timezone
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, LargeBinary, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


def _now() -> datetime:
    return datetime.now(timezone.utc)


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
    created_at = Column(DateTime(timezone=True), nullable=False, default=_now)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=_now, onupdate=_now)
    is_deleted = Column(Boolean, nullable=False, default=False)

    global_server = relationship("MCPServerGlobal", back_populates="user_servers")
```

- [ ] **Step 2: Create database session factory**

Create `src/mcp_servers/db.py`:

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from src.config.settings import settings
from src.mcp_servers.models import Base


def _get_engine():
    url = settings.MCP_DB_URL
    if not url:
        raise RuntimeError("MCP_DB_URL is not set")
    return create_engine(url, pool_pre_ping=True)


def get_session() -> Session:
    engine = _get_engine()
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    return SessionLocal()


def create_tables() -> None:
    engine = _get_engine()
    Base.metadata.create_all(bind=engine)
```

- [ ] **Step 3: Verify models import without error**

```bash
python -c "from src.mcp_servers.models import MCPServerGlobal, MCPServerUser; print('OK')"
```

Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add src/mcp_servers/models.py src/mcp_servers/db.py
git commit -m "feat(mcp): add SQLAlchemy models and session factory"
```

---

## Task 4: Pydantic schemas

**Files:**
- Create: `src/mcp_servers/schemas.py`

- [ ] **Step 1: Create schemas**

Create `src/mcp_servers/schemas.py`:

```python
from datetime import datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, HttpUrl, field_validator
from enum import Enum


class AuthType(str, Enum):
    none = "none"
    api_key = "api_key"
    oauth = "oauth"


class MCPServerCreate(BaseModel):
    url: str
    label: str
    description: Optional[str] = None
    auth_type: AuthType = AuthType.none
    credentials: Optional[str] = None

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


class MCPServerResponse(BaseModel):
    id: UUID
    user_id: str
    global_server_id: Optional[UUID] = None
    label: str
    url: str
    description: Optional[str]
    auth_type: AuthType
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MCPServerGlobalResponse(BaseModel):
    id: UUID
    label: str
    url: str
    description: Optional[str]
    auth_type: AuthType
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class MCPServerListResponse(BaseModel):
    global_servers: List[MCPServerGlobalResponse]
    user_servers: List[MCPServerResponse]
```

- [ ] **Step 2: Verify schemas import without error**

```bash
python -c "from src.mcp_servers.schemas import MCPServerCreate, MCPServerListResponse; print('OK')"
```

Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add src/mcp_servers/schemas.py
git commit -m "feat(mcp): add Pydantic schemas for MCP server requests/responses"
```

---

## Task 5: CRUD operations

**Files:**
- Create: `src/mcp_servers/crud.py`
- Create: `tests/test_mcp_crud.py`

- [ ] **Step 1: Write failing tests**

Create `tests/test_mcp_crud.py`:

```python
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
```

- [ ] **Step 2: Run tests to confirm they fail**

```bash
pytest tests/test_mcp_crud.py -v
```

Expected: `ImportError` — crud module does not exist yet.

- [ ] **Step 3: Implement CRUD module**

Create `src/mcp_servers/crud.py`:

```python
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
```

- [ ] **Step 4: Run tests — all must pass**

```bash
pytest tests/test_mcp_crud.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add src/mcp_servers/crud.py tests/test_mcp_crud.py
git commit -m "feat(mcp): add CRUD operations with soft-delete and credential encryption"
```

---

## Task 6: FastAPI dependency and routes

**Files:**
- Create: `src/mcp_servers/dependencies.py`
- Create: `src/mcp_servers/routes.py`
- Create: `tests/test_mcp_routes.py`

- [ ] **Step 1: Create user dependency**

Create `src/mcp_servers/dependencies.py`:

```python
from fastapi import Header, HTTPException


def get_user_id(x_user_id: str = Header(None)) -> str:
    """
    Extracts user identity from the X-User-Id header.
    The Next.js proxy layer injects this header after validating the session.
    """
    if not x_user_id:
        raise HTTPException(status_code=401, detail="Missing X-User-Id header")
    return x_user_id
```

- [ ] **Step 2: Write failing route tests**

Create `tests/test_mcp_routes.py`:

```python
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
    c = TestClient(app)
    resp = c.get("/api/mcp-servers")
    assert resp.status_code == 401
```

- [ ] **Step 3: Run tests to confirm they fail**

```bash
pytest tests/test_mcp_routes.py -v
```

Expected: `ImportError` — routes module does not exist yet.

- [ ] **Step 4: Create routes module**

Create `src/mcp_servers/routes.py`:

```python
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
```

- [ ] **Step 5: Run tests — all must pass**

```bash
pytest tests/test_mcp_routes.py -v
```

Expected: 6 passed.

- [ ] **Step 6: Commit**

```bash
git add src/mcp_servers/dependencies.py src/mcp_servers/routes.py tests/test_mcp_routes.py
git commit -m "feat(mcp): add FastAPI routes and user dependency"
```

---

## Task 7: Register router in the app

**Files:**
- Modify: `src/app.py`

- [ ] **Step 1: Add import and router registration**

Open [src/app.py](src/app.py) and add after the line `app.include_router(admin_router, prefix="/admin")`:

```python
from src.mcp_servers.routes import router as mcp_router
from src.mcp_servers.db import create_tables as _create_mcp_tables

_create_mcp_tables()
app.include_router(mcp_router)
```

- [ ] **Step 2: Verify the app starts (with MCP_DB_URL unset — expect RuntimeError to be deferred)**

```bash
python -c "
import os
os.environ['MCP_DB_URL'] = ''
# Only import — don't start server
from src.mcp_servers.routes import router
print('Router imported OK, endpoints:', [r.path for r in router.routes])
"
```

Expected: prints the 5 route paths.

- [ ] **Step 3: Run all tests to confirm nothing broke**

```bash
pytest tests/ -v
```

Expected: all previous tests still pass.

- [ ] **Step 4: Commit**

```bash
git add src/app.py
git commit -m "feat(mcp): register MCP servers router in FastAPI app"
```

---

## Task 8: Configure Neon database

- [ ] **Step 1: Generate the encryption key**

```bash
python -c "from src.mcp_servers.encryption import generate_key; print(generate_key())"
```

Copy the output. This is your `MCP_ENCRYPTION_KEY`.

- [ ] **Step 2: Fill in `.env`**

```
MCP_DB_URL=postgresql+psycopg://user:password@ep-xxx.neon.tech/mcp_servers?sslmode=require
MCP_ENCRYPTION_KEY=<output from step 1>
```

- [ ] **Step 3: Run table migration against Neon**

```bash
python -c "from src.mcp_servers.db import create_tables; create_tables(); print('Tables created')"
```

Expected: `Tables created` (no errors).

- [ ] **Step 4: Verify tables exist on Neon**

Run in the Neon SQL editor or via psql:

```sql
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_name LIKE 'mcp_servers%';
```

Expected: two rows — `mcp_servers_global`, `mcp_servers_user`.

- [ ] **Step 5: Commit (env file NOT included)**

```bash
git add src/  # only source changes if any
git commit -m "feat(mcp): production MCP database configured on Neon"
```

---

## Task 9: Full integration smoke test

- [ ] **Step 1: Start the server locally**

```bash
python -m uvicorn src.app:app --port 7777 --reload
```

- [ ] **Step 2: Test create**

```bash
curl -s -X POST http://localhost:7777/api/mcp-servers \
  -H "Content-Type: application/json" \
  -H "X-User-Id: test_user_1" \
  -d '{"url":"https://mcp.example.com","label":"My Test MCP","auth_type":"api_key","credentials":"sk_test_123"}' | python -m json.tool
```

Expected: JSON with `id`, `label`, `user_id`, no `credentials` field.

- [ ] **Step 3: Test list**

```bash
curl -s http://localhost:7777/api/mcp-servers \
  -H "X-User-Id: test_user_1" | python -m json.tool
```

Expected: `{"global_servers": [], "user_servers": [{"label": "My Test MCP", ...}]}`

- [ ] **Step 4: Test update**

Copy the `id` from step 2, then:

```bash
curl -s -X PATCH http://localhost:7777/api/mcp-servers/<id> \
  -H "Content-Type: application/json" \
  -H "X-User-Id: test_user_1" \
  -d '{"label":"Updated Label"}' | python -m json.tool
```

Expected: `{"label": "Updated Label", ...}`

- [ ] **Step 5: Test delete**

```bash
curl -s -X DELETE http://localhost:7777/api/mcp-servers/<id> \
  -H "X-User-Id: test_user_1" -v
```

Expected: HTTP 204 No Content.

- [ ] **Step 6: Verify soft delete (row still in DB, is_deleted=true)**

Run in Neon SQL editor:

```sql
SELECT id, label, is_deleted FROM mcp_servers_user WHERE user_id = 'test_user_1';
```

Expected: row present with `is_deleted = true`.

- [ ] **Step 7: Commit final state**

```bash
git add -A
git commit -m "feat(mcp): MCP servers config system complete — CRUD + encryption + Neon"
```

---

## What the Frontend Needs to Send

For every request, the Next.js proxy must inject:

```
X-User-Id: <user_id from session>
```

No bearer token needed for these endpoints — the user ID header is sufficient. The `require_bearer_token` middleware is NOT applied to `/api/mcp-servers` (it only guards `/v1/*`).
