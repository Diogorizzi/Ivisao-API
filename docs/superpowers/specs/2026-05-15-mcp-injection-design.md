# MCP Per-User Injection — Design Spec

**Date:** 2026-05-15
**Scope:** Inject user-activated MCP servers into each agent run dynamically, with per-user session isolation
**Depends on:** `src/mcp_servers/` module (CRUD + encryption, already built)

---

## 1. Overview

When a request reaches `/agents/{id}/runs`, the agent must automatically have access to the MCP servers that **this specific user has explicitly connected and authenticated**.

Two distinct concepts:
- **`mcp_servers_global`** = **catalogue only** — visible in the "Add MCP server" UI screen so the user can choose what to connect. No automatic injection. No connection without the user's own credentials.
- **`mcp_servers_user`** = **active connections** — rows that exist only after the user clicked "Connect" and provided their own token/credentials. These are what get injected into the agent.

Users who have not connected any MCP run the agent normally with no extra tools. The agent becomes an MCP client only for the tools each user has individually activated.

---

## 2. Architecture

```
Request: POST /agents/{id}/runs
  Form fields: message, user_id, session_id, ...
        ↓
┌─────────────────────────────────┐
│  MCPInjectionMiddleware         │
│  - peek user_id from Form body  │
│  - load user's active MCPs only │
│    (mcp_servers_user, NOT global)│
│  - decrypt credentials          │
│  - instantiate MCPTools(...)    │
│  - set _mcp_ctx ContextVar      │
└─────────────────────────────────┘
        ↓
┌─────────────────────────────────┐
│  Agno router                    │
│  get_agent_by_id(create_fresh)  │
│  [our patched version]          │
│  deep_copy(update={             │
│    "tools": agent.tools +       │
│             _mcp_ctx.get()      │
│  })                             │
└─────────────────────────────────┘
        ↓
  agent.arun(user_id=...) 
  → agent calls MCP tools as needed
```

---

## 3. Components

### 3.1 `src/mcp_servers/injection.py`

Single file with two responsibilities:

**A. ContextVar**
```python
_mcp_ctx: ContextVar[List[MCPTools]] = ContextVar("_mcp_ctx", default=[])
```

Thread-safe by design — each async task has its own context slot.

**B. `MCPInjectionMiddleware(BaseHTTPMiddleware)`**

Intercepts only `POST /agents/{any}/runs` paths.

Steps:
1. Read the raw body bytes (cache them on `request.state._body` so downstream can still read)
2. Parse `user_id` from URL-encoded form data (the format the proxy sends)
3. If no `user_id` → skip injection, continue normally (user runs without MCPs)
4. Query DB:
   - `mcp_servers_user` WHERE `user_id = ?` AND `is_deleted = false` **only**
   - Global servers are NOT injected — they are catalogue entries, not active connections
5. For each server: instantiate `MCPTools(url=..., transport="streamable-http", headers={"Authorization": f"Bearer {decrypted_credentials}"})`
   - If `auth_type == "none"` → no headers
   - If `auth_type == "api_key"` → Bearer token header
6. Set `_mcp_ctx.set(all_tools)`
7. `await call_next(request)` — rest of the pipeline runs normally
8. After response: `_mcp_ctx.set([])` — cleanup (defensive, ContextVar resets per task anyway)

**Error policy:** If DB is unavailable or decryption fails for a server, log a warning and skip that server. Never fail the entire request because of MCP loading.

**C. `patch_get_agent_by_id()`**

Called once at app startup. Replaces `agno.os.utils.get_agent_by_id` with a wrapper:

```python
def _patched_get_agent_by_id(agent_id, agents, ...):
    agent = _original(agent_id, agents, create_fresh=False, ...)
    if agent is None:
        return None
    user_tools = _mcp_ctx.get()
    if not user_tools or not create_fresh:
        return _original(agent_id, agents, create_fresh=create_fresh, ...)
    # create_fresh=True: do the deep_copy ourselves with extra tools
    existing_tools = list(agent.tools or [])
    return agent.deep_copy(update={"tools": existing_tools + user_tools})
```

This is applied once at import time, not per-request.

---

### 3.2 `src/app.py` changes

Two additions:

```python
# 1. Register middleware (BEFORE AgentOS app is created)
from src.mcp_servers.injection import MCPInjectionMiddleware, patch_get_agent_by_id
patch_get_agent_by_id()   # patch before AgentOS builds routes
app.add_middleware(MCPInjectionMiddleware)

# 2. No other changes needed
```

---

## 4. Data Flow per Request

### User who connected Gmail and Drive (both with their own tokens)

```
1. Front sends: POST /agents/general-assistant/runs
   Form: message="search my gmail", user_id="user_abc"

2. MCPInjectionMiddleware:
   - Reads user_id = "user_abc"
   - DB query: mcp_servers_user WHERE user_id = "user_abc"
     → [{url: "https://gmail.mcp.io", auth_type: "api_key", encrypted_credentials: b"..."},
        {url: "https://drive.mcp.io", auth_type: "api_key", encrypted_credentials: b"..."}]
   - Decrypt each → "gmail_token_xyz", "drive_token_xyz"
   - Instantiate:
     MCPTools(url="https://gmail.mcp.io", transport="streamable-http",
              headers={"Authorization": "Bearer gmail_token_xyz"})
     MCPTools(url="https://drive.mcp.io", transport="streamable-http",
              headers={"Authorization": "Bearer drive_token_xyz"})
   - _mcp_ctx.set([gmail_tools, drive_tools])

3. Agno router:
   - patched get_agent_by_id("general-assistant", create_fresh=True)
   - agent.deep_copy(update={"tools": [DuckDuckGo, Pandas, ...] + [gmail_tools, drive_tools]})

4. agent.arun("search my gmail", user_id="user_abc")
   - Agent sees Gmail and Drive tools available
   - Calls them as needed
```

### User with no MCP servers

```
1. MCPInjectionMiddleware:
   - user_id = "user_xyz"
   - DB query: global=[], user=[]
   - _mcp_ctx.set([])

2. Patched get_agent_by_id:
   - user_tools = [] → skip injection
   - Falls through to original deep_copy

3. agent.arun() — normal execution, no extra tools
```

---

## 5. MCPTools Instantiation

The Agno `MCPTools` class accepts:
```python
MCPTools(
    url: str,
    transport: str = "streamable-http",   # or "sse"
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 30,
)
```

For auth:
- `auth_type = "none"` → `MCPTools(url=url, transport="streamable-http")`
- `auth_type = "api_key"` → `MCPTools(url=url, transport="streamable-http", headers={"Authorization": f"Bearer {cred}"})`
- `auth_type = "oauth"` → same as api_key (oauth token stored as credential)

---

## 6. Thread Safety

`ContextVar` is the Python stdlib mechanism for per-async-task context. Each request in an async FastAPI app runs in its own asyncio task — the ContextVar is automatically isolated between concurrent requests. No locking required.

Reference: [PEP 567 — Context Variables](https://peps.python.org/pep-0567/)

---

## 7. Error Handling

| Failure | Behavior |
|---------|----------|
| DB unavailable at middleware | Log warning, `_mcp_ctx.set([])`, continue request |
| Decryption fails for one server | Log warning, skip that server, continue with others |
| MCPTools instantiation fails | Log warning, skip that server |
| MCP server unreachable at run time | Agno handles it — tool call returns error, agent adapts |
| `user_id` missing from body | Skip injection entirely, agent runs without MCP tools |

---

## 8. Testing

- **Unit:** `MCPInjectionMiddleware` with mocked DB session — verify ContextVar is set correctly
- **Unit:** patched `get_agent_by_id` — verify tools are injected when ContextVar has values
- **Unit:** error paths — DB down, decryption fail, no user_id
- **Integration (manual):** Start server, create user MCP via `POST /api/mcp-servers`, run agent — verify MCP tools appear in agent's tool list

---

## 9. What the Frontend Already Does (No Changes Needed)

The `agno-proxy` in Next.js already injects `user_id` into every run request body:
```typescript
params.append("user_id", auth.dbUserId);
```

No frontend changes required. The injection is fully transparent to the frontend.

---

## 10. Limitations

- **MCP servers are loaded per request** — no caching. For users with many MCPs, this adds a small DB round-trip per run (~1-5ms on Neon). Acceptable for now.
- **MCPTools connections are short-lived** — opened and closed per request (Agno's default). Persistent MCP sessions are a future concern.
- **OAuth flow** (full redirect-based auth) is out of scope — credentials stored as bearer tokens work for now.

---

**Status:** Ready for implementation
