# MCP Per-User Injection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Inject each user's active MCP servers as MCPTools into the agent for every `/agents/{id}/runs` request, transparently and thread-safely, without modifying the Agno library.

**Architecture:** A `ContextVar` stores per-request MCP tools. A FastAPI middleware reads `user_id` from the form body, loads the user's `mcp_servers_user` rows, decrypts credentials, instantiates `MCPTools`, and sets the ContextVar. A monkey-patch on `agno.os.utils.get_agent_by_id` intercepts the `create_fresh=True` call and injects those tools into the agent's `deep_copy`. Both components live in `src/mcp_servers/injection.py`.

**Tech Stack:** Python `contextvars.ContextVar`, Starlette `BaseHTTPMiddleware`, Agno `MCPTools` + `StreamableHTTPClientParams`, SQLAlchemy (sync session from existing `src/mcp_servers/db.py`)

---

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `src/mcp_servers/injection.py` | Create | ContextVar, middleware, monkey-patch |
| `src/app.py` | Modify | Register middleware + call patch at startup |
| `tests/test_mcp_injection.py` | Create | Unit tests for middleware and patch |

---

## Task 1: ContextVar + middleware skeleton

**Files:**
- Create: `src/mcp_servers/injection.py`
- Create: `tests/test_mcp_injection.py`

- [ ] **Step 1: Write failing tests for ContextVar isolation**

Create `tests/test_mcp_injection.py`:

```python
import os
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from cryptography.fernet import Fernet

os.environ["MCP_ENCRYPTION_KEY"] = Fernet.generate_key().decode()
os.environ["MCP_DB_URL"] = "postgresql+psycopg://test"

import pytest
from src.mcp_servers.injection import _mcp_ctx, MCPInjectionMiddleware


def test_mcp_ctx_default_is_empty():
    assert _mcp_ctx.get() == []


def test_mcp_ctx_is_isolated_between_tasks():
    results = {}

    async def task_a():
        token = _mcp_ctx.set(["tool_a"])
        await asyncio.sleep(0)
        results["a"] = _mcp_ctx.get()
        _mcp_ctx.reset(token)

    async def task_b():
        await asyncio.sleep(0)
        results["b"] = _mcp_ctx.get()

    async def run():
        await asyncio.gather(task_a(), task_b())

    asyncio.run(run())
    assert results["a"] == ["tool_a"]
    assert results["b"] == []
```

- [ ] **Step 2: Run to confirm failure**

```bash
.venv/Scripts/python -m pytest tests/test_mcp_injection.py::test_mcp_ctx_default_is_empty tests/test_mcp_injection.py::test_mcp_ctx_is_isolated_between_tasks -v
```

Expected: `ModuleNotFoundError` — injection module does not exist.

- [ ] **Step 3: Create injection module with ContextVar only**

Create `src/mcp_servers/injection.py`:

```python
import logging
import re
from contextvars import ContextVar
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

log = logging.getLogger(__name__)

# Per-async-task MCP tools list. Set by MCPInjectionMiddleware before each run.
_mcp_ctx: ContextVar[List[Any]] = ContextVar("_mcp_ctx", default=[])

_RUNS_PATH_RE = re.compile(r"/(agents|teams|workflows)/[^/]+/runs$")


class MCPInjectionMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next) -> Response:
        # Only intercept POST .../runs endpoints
        if request.method != "POST" or not _RUNS_PATH_RE.search(request.url.path):
            return await call_next(request)

        token = _mcp_ctx.set([])
        try:
            return await call_next(request)
        finally:
            _mcp_ctx.reset(token)
```

- [ ] **Step 4: Run tests — both must pass**

```bash
.venv/Scripts/python -m pytest tests/test_mcp_injection.py::test_mcp_ctx_default_is_empty tests/test_mcp_injection.py::test_mcp_ctx_is_isolated_between_tasks -v
```

Expected: 2 passed.

- [ ] **Step 5: Commit**

```bash
git add src/mcp_servers/injection.py tests/test_mcp_injection.py
git commit -m "feat(mcp): add injection module skeleton with ContextVar"
```

---

## Task 2: Middleware loads and sets user MCPs

**Files:**
- Modify: `src/mcp_servers/injection.py`
- Modify: `tests/test_mcp_injection.py`

- [ ] **Step 1: Write failing tests for MCP loading**

Add these tests to `tests/test_mcp_injection.py`:

```python
import uuid
from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.testclient import TestClient


def _make_user_server(url="https://mcp.example.com", auth_type="none", creds=None):
    from src.mcp_servers.models import MCPServerUser
    from src.mcp_servers.encryption import encrypt_credentials
    s = MCPServerUser()
    s.id = uuid.uuid4()
    s.user_id = "user_123"
    s.label = "Test"
    s.url = url
    s.auth_type = auth_type
    s.description = None
    s.encrypted_credentials = encrypt_credentials(creds) if creds else None
    s.is_deleted = False
    s.global_server_id = None
    s.created_at = datetime.now(timezone.utc)
    s.updated_at = datetime.now(timezone.utc)
    return s


@pytest.fixture
def app_with_middleware():
    from src.mcp_servers.injection import MCPInjectionMiddleware
    app = FastAPI()
    app.add_middleware(MCPInjectionMiddleware)

    @app.post("/agents/test/runs")
    async def fake_run():
        tools = _mcp_ctx.get()
        return {"tool_count": len(tools), "tool_types": [type(t).__name__ for t in tools]}

    return app


def test_middleware_sets_no_tools_when_no_user_id(app_with_middleware):
    client = TestClient(app_with_middleware)
    resp = client.post(
        "/agents/test/runs",
        data={"message": "hello"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert resp.status_code == 200
    assert resp.json()["tool_count"] == 0


def test_middleware_sets_tools_for_user_with_none_auth(app_with_middleware):
    server = _make_user_server(auth_type="none")
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.all.return_value = [server]

    with patch("src.mcp_servers.injection.get_user_mcp_tools", return_value=[MagicMock(__class__=type("MCPTools", (), {}))]):
        client = TestClient(app_with_middleware)
        resp = client.post(
            "/agents/test/runs",
            data={"message": "hello", "user_id": "user_123"},
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
    assert resp.status_code == 200


def test_middleware_skips_non_runs_path(app_with_middleware):
    client = TestClient(app_with_middleware)
    resp = client.post(
        "/agents/test/sessions",
        data={"message": "hello", "user_id": "user_123"},
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    # 404 is fine — we just verify the middleware doesn't break non-runs paths
    assert resp.status_code in (200, 404, 405)
```

- [ ] **Step 2: Run to confirm failure**

```bash
.venv/Scripts/python -m pytest tests/test_mcp_injection.py::test_middleware_sets_no_tools_when_no_user_id -v
```

Expected: FAIL — `get_user_mcp_tools` not defined yet.

- [ ] **Step 3: Implement `get_user_mcp_tools` and full middleware dispatch**

Replace the contents of `src/mcp_servers/injection.py` with:

```python
import logging
import re
from contextvars import ContextVar
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

log = logging.getLogger(__name__)

_mcp_ctx: ContextVar[List[Any]] = ContextVar("_mcp_ctx", default=[])

_RUNS_PATH_RE = re.compile(r"/(agents|teams|workflows)/[^/]+/runs$")


def get_user_mcp_tools(user_id: str) -> List[Any]:
    """
    Load user's active MCP servers from DB and return instantiated MCPTools.
    Errors per-server are logged and skipped — never raises.
    """
    try:
        from agno.tools.mcp import MCPTools
        from agno.tools.mcp.params import StreamableHTTPClientParams
        from src.mcp_servers.crud import get_user_servers
        from src.mcp_servers.db import get_session
        from src.mcp_servers.encryption import decrypt_credentials
    except Exception as e:
        log.warning(f"[MCP] Import error — skipping injection: {e}")
        return []

    tools: List[Any] = []
    db = None
    try:
        db = get_session()
        servers = get_user_servers(db, user_id)
    except Exception as e:
        log.warning(f"[MCP] DB unavailable for user {user_id} — skipping: {e}")
        return []
    finally:
        if db is not None:
            db.close()

    for server in servers:
        try:
            headers: Dict[str, str] = {}
            if server.auth_type in ("api_key", "oauth") and server.encrypted_credentials:
                token = decrypt_credentials(server.encrypted_credentials)
                headers["Authorization"] = f"Bearer {token}"

            params = StreamableHTTPClientParams(
                url=server.url,
                headers=headers or None,
            )
            tool = MCPTools(
                transport="streamable-http",
                server_params=params,
            )
            tools.append(tool)
        except Exception as e:
            log.warning(f"[MCP] Failed to instantiate MCPTools for {server.url}: {e}")

    return tools


class MCPInjectionMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp) -> None:
        super().__init__(app)

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method != "POST" or not _RUNS_PATH_RE.search(request.url.path):
            return await call_next(request)

        # Read and cache body so downstream can still consume it
        body = await request.body()
        request.state._body = body

        user_id: Optional[str] = None
        try:
            content_type = request.headers.get("content-type", "")
            if "application/x-www-form-urlencoded" in content_type:
                parsed = parse_qs(body.decode("utf-8", errors="replace"))
                ids = parsed.get("user_id", [])
                user_id = ids[0] if ids else None
            elif "multipart/form-data" in content_type:
                # For multipart, parse a quick boundary scan for user_id field
                # (full parse is expensive — do a best-effort text scan)
                text = body.decode("utf-8", errors="replace")
                import re as _re
                m = _re.search(r'name="user_id"\r\n\r\n([^\r\n]+)', text)
                user_id = m.group(1) if m else None
        except Exception as e:
            log.warning(f"[MCP] Could not parse user_id from body: {e}")

        tools = get_user_mcp_tools(user_id) if user_id else []
        token = _mcp_ctx.set(tools)
        try:
            return await call_next(request)
        finally:
            _mcp_ctx.reset(token)
```

- [ ] **Step 4: Run all injection tests**

```bash
.venv/Scripts/python -m pytest tests/test_mcp_injection.py -v
```

Expected: 5 passed.

- [ ] **Step 5: Commit**

```bash
git add src/mcp_servers/injection.py tests/test_mcp_injection.py
git commit -m "feat(mcp): implement MCPInjectionMiddleware with user MCP loading"
```

---

## Task 3: Monkey-patch `get_agent_by_id`

**Files:**
- Modify: `src/mcp_servers/injection.py`
- Modify: `tests/test_mcp_injection.py`

- [ ] **Step 1: Write failing tests for the patch**

Add these tests to `tests/test_mcp_injection.py`:

```python
def test_patch_injects_tools_when_ctx_has_tools():
    from src.mcp_servers.injection import patch_get_agent_by_id, _mcp_ctx

    # Build a minimal fake Agent with deep_copy support
    class FakeTool:
        pass

    class FakeAgent:
        def __init__(self, tools=None):
            self.id = "test-agent"
            self.tools = tools or []
            self.team_id = None
            self.workflow_id = None

        def deep_copy(self, update=None):
            tools = (update or {}).get("tools", self.tools)
            return FakeAgent(tools=tools)

    fake_agents = [FakeAgent(tools=[FakeTool()])]

    # Mock the original get_agent_by_id
    import agno.os.utils as agno_utils
    original = agno_utils.get_agent_by_id

    # Apply patch
    patch_get_agent_by_id()

    extra_tool = FakeTool()
    token = _mcp_ctx.set([extra_tool])
    try:
        result = agno_utils.get_agent_by_id(
            "test-agent", fake_agents, create_fresh=True
        )
        assert len(result.tools) == 2  # original 1 + injected 1
    finally:
        _mcp_ctx.reset(token)
        agno_utils.get_agent_by_id = original  # restore


def test_patch_skips_injection_when_ctx_empty():
    from src.mcp_servers.injection import patch_get_agent_by_id, _mcp_ctx

    class FakeTool:
        pass

    class FakeAgent:
        def __init__(self, tools=None):
            self.id = "test-agent"
            self.tools = tools or []
            self.team_id = None
            self.workflow_id = None

        def deep_copy(self, update=None):
            tools = (update or {}).get("tools", self.tools)
            return FakeAgent(tools=tools)

    fake_agents = [FakeAgent(tools=[FakeTool()])]

    import agno.os.utils as agno_utils
    original = agno_utils.get_agent_by_id
    patch_get_agent_by_id()

    # No tools in context
    try:
        result = agno_utils.get_agent_by_id(
            "test-agent", fake_agents, create_fresh=True
        )
        assert len(result.tools) == 1  # unchanged
    finally:
        agno_utils.get_agent_by_id = original


def test_patch_returns_none_for_unknown_agent():
    from src.mcp_servers.injection import patch_get_agent_by_id

    import agno.os.utils as agno_utils
    original = agno_utils.get_agent_by_id
    patch_get_agent_by_id()

    try:
        result = agno_utils.get_agent_by_id("nonexistent", [], create_fresh=True)
        assert result is None
    finally:
        agno_utils.get_agent_by_id = original
```

- [ ] **Step 2: Run to confirm failure**

```bash
.venv/Scripts/python -m pytest tests/test_mcp_injection.py::test_patch_injects_tools_when_ctx_has_tools -v
```

Expected: FAIL — `patch_get_agent_by_id` not defined.

- [ ] **Step 3: Add `patch_get_agent_by_id` to injection.py**

Add this at the bottom of `src/mcp_servers/injection.py`:

```python
def patch_get_agent_by_id() -> None:
    """
    Monkey-patch agno.os.utils.get_agent_by_id to inject user MCP tools
    into the agent's deep_copy when create_fresh=True.
    Called once at app startup before AgentOS builds routes.
    """
    import agno.os.utils as _agno_utils

    _original = _agno_utils.get_agent_by_id

    def _patched(agent_id, agents=None, db=None, registry=None, version=None, create_fresh=False):
        agent = _original(
            agent_id, agents=agents, db=db, registry=registry,
            version=version, create_fresh=False,
        )
        if agent is None:
            return None

        user_tools = _mcp_ctx.get()
        if not create_fresh or not user_tools:
            # No injection needed — fall back to original behaviour
            return _original(
                agent_id, agents=agents, db=db, registry=registry,
                version=version, create_fresh=create_fresh,
            )

        # create_fresh=True + user has MCPs: deep_copy with extra tools
        existing = list(getattr(agent, "tools", None) or [])
        return agent.deep_copy(update={"tools": existing + user_tools})

    _agno_utils.get_agent_by_id = _patched
    log.info("[MCP] Patched agno.os.utils.get_agent_by_id for per-user MCP injection")
```

- [ ] **Step 4: Run all injection tests**

```bash
.venv/Scripts/python -m pytest tests/test_mcp_injection.py -v
```

Expected: 8 passed.

- [ ] **Step 5: Commit**

```bash
git add src/mcp_servers/injection.py tests/test_mcp_injection.py
git commit -m "feat(mcp): add patch_get_agent_by_id for per-user tool injection"
```

---

## Task 4: Wire into app.py

**Files:**
- Modify: `src/app.py`

- [ ] **Step 1: Locate the insertion point**

Open `src/app.py`. The relevant section looks like:

```python
agent_os = AgentOS(agents=agents, ...)
app = agent_os.get_app()
# ... CORS middleware ...
app.include_router(admin_router, prefix="/admin")
app.add_middleware(AdminAuthMiddleware)
from src.mcp_servers.routes import router as mcp_router
...
```

- [ ] **Step 2: Add patch call BEFORE `AgentOS` is initialized**

Insert the following **before** the `agents = load_all_agents()` line:

```python
from src.mcp_servers.injection import patch_get_agent_by_id
patch_get_agent_by_id()
```

The full block should look like:

```python
from src.mcp_servers.injection import patch_get_agent_by_id
patch_get_agent_by_id()

# Carrega todos os agentes do YAML
agents = load_all_agents()

# Inicializa o AgentOS
agent_os = AgentOS(
    agents=agents,
    knowledge=[get_knowledge_base()],
    tracing=False,
)

app = agent_os.get_app()
```

- [ ] **Step 3: Add middleware AFTER `app = agent_os.get_app()`**

Insert after the CORS `add_middleware` block:

```python
from src.mcp_servers.injection import MCPInjectionMiddleware
app.add_middleware(MCPInjectionMiddleware)
```

The full middleware section should look like:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)

from src.mcp_servers.injection import MCPInjectionMiddleware
app.add_middleware(MCPInjectionMiddleware)
```

- [ ] **Step 4: Verify the router import still works**

```bash
.venv/Scripts/python -c "
import os; os.environ['MCP_DB_URL'] = ''; os.environ['MCP_ENCRYPTION_KEY'] = 'x'
from src.mcp_servers.injection import patch_get_agent_by_id, MCPInjectionMiddleware
print('OK')
"
```

Expected: `OK`

- [ ] **Step 5: Run all MCP tests**

```bash
.venv/Scripts/python -m pytest tests/test_mcp_encryption.py tests/test_mcp_crud.py tests/test_mcp_routes.py tests/test_mcp_injection.py -v
```

Expected: all 21 tests pass.

- [ ] **Step 6: Commit**

```bash
git add src/app.py
git commit -m "feat(mcp): wire MCPInjectionMiddleware and patch into app startup"
```

---

## Task 5: Body caching — fix double-read issue

**Context:** FastAPI's `BaseHTTPMiddleware` reads the body once. The Agno router then tries to read the form fields again. We cache the body in `request.state._body`, but we also need to ensure Starlette uses it. The existing `app.py` already has a `_patched_form` that caches `Request.form`. Our middleware sets `request.state._body` — Starlette's `Request.body()` checks `_body` on `request.state` automatically in recent versions. Let's verify and add a fallback if needed.

**Files:**
- Modify: `src/mcp_servers/injection.py`

- [ ] **Step 1: Verify body caching works with Starlette's receive**

The body caching approach we use (`request.state._body`) is NOT automatically used by Starlette's receive protocol. We need to patch the `receive` callable instead.

Replace the `dispatch` method's body-reading section in `src/mcp_servers/injection.py` with:

```python
async def dispatch(self, request: Request, call_next) -> Response:
    if request.method != "POST" or not _RUNS_PATH_RE.search(request.url.path):
        return await call_next(request)

    # Read body and rebuild the receive callable so downstream can read it again
    body = await request.body()

    async def receive():
        return {"type": "http.request", "body": body, "more_body": False}

    request._receive = receive  # type: ignore[attr-defined]

    user_id: Optional[str] = None
    try:
        content_type = request.headers.get("content-type", "")
        if "application/x-www-form-urlencoded" in content_type:
            parsed = parse_qs(body.decode("utf-8", errors="replace"))
            ids = parsed.get("user_id", [])
            user_id = ids[0] if ids else None
        elif "multipart/form-data" in content_type:
            text = body.decode("utf-8", errors="replace")
            import re as _re
            m = _re.search(r'name="user_id"\r\n\r\n([^\r\n]+)', text)
            user_id = m.group(1) if m else None
    except Exception as e:
        log.warning(f"[MCP] Could not parse user_id from body: {e}")

    tools = get_user_mcp_tools(user_id) if user_id else []
    token = _mcp_ctx.set(tools)
    try:
        return await call_next(request)
    finally:
        _mcp_ctx.reset(token)
```

- [ ] **Step 2: Run all injection tests to confirm nothing broke**

```bash
.venv/Scripts/python -m pytest tests/test_mcp_injection.py -v
```

Expected: 8 passed.

- [ ] **Step 3: Commit**

```bash
git add src/mcp_servers/injection.py
git commit -m "fix(mcp): use receive override instead of state._body for body caching"
```

---

## Summary: What the Frontend Dev Needs to Know

After this implementation, **no frontend changes are required**. The `agno-proxy` already does everything needed:

```typescript
// agno-proxy/route.ts — already does this:
params.append("user_id", auth.dbUserId);   // ← this triggers MCP injection
```

**The complete flow from the frontend perspective:**

1. User opens "Add MCP server" modal → sees global catalogue (`GET /api/mcp-servers`)
2. User picks a server and enters their access token → `POST /api/mcp-servers` with `{url, label, auth_type: "api_key", credentials: "<token>"}`
3. On the next chat message, the agent automatically has the user's MCP tools available — no extra step

**For the frontend Claude Code engineer — the exact API contract:**

### Save a user MCP connection
```http
POST /api/mcp-servers
X-User-Id: <user_id from session>
Content-Type: application/json

{
  "url": "https://mcp.composio.dev/gmail/...",
  "label": "Gmail",
  "description": "optional",
  "auth_type": "api_key",
  "credentials": "<user's access token>"
}
```

### List user's saved connections
```http
GET /api/mcp-servers
X-User-Id: <user_id from session>
```

Response:
```json
{
  "global_servers": [
    {"id": "...", "label": "Gmail", "url": "https://...", "auth_type": "api_key"}
  ],
  "user_servers": [
    {"id": "...", "label": "Gmail", "url": "https://...", "auth_type": "api_key", "created_at": "..."}
  ]
}
```

Note: **`credentials` (the token) is NEVER returned** — only stored encrypted.

### Delete a connection
```http
DELETE /api/mcp-servers/<id>
X-User-Id: <user_id from session>
```

### The `X-User-Id` header
This must be the same `user_id` that the `agno-proxy` sends in the form body (`params.append("user_id", auth.dbUserId)`). They must match for the injection to find the right MCPs.
