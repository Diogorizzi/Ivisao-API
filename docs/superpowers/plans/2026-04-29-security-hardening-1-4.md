# Security Hardening (Items 1–4) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the four most critical security gaps in Dartha API V3 without breaking any existing feature.

**Architecture:** Four independent, low-coupling changes: (1) remove dangerous tools from the dynamic endpoint loader, (2) gate `/v1/dynamic-run` behind an API-key header, (3) add CORS allowlist middleware, (4) sanitize admin upload filenames and assert a non-default secret key on startup.

**Tech Stack:** FastAPI, Starlette middleware, python-jose (already installed), pydantic-settings, pytest + httpx for tests.

**Constraint:** AGUI routes (`/agui/*`) are currently disabled/hidden — do not touch them.

---

## File Map

| File | Change |
|---|---|
| `src/tools/dynamic_loader.py` | Remove `PythonTools` and `FileTools` from the whitelist |
| `src/config/settings.py` | Add `API_SECRET_KEY`, `CORS_ALLOWED_ORIGINS`, `MAX_UPLOAD_MB` |
| `src/middleware/api_key.py` | New — FastAPI dependency that enforces `X-API-Key` |
| `src/app.py` | Add CORSMiddleware, startup secret-key assertion, wire API-key dep on `/v1/dynamic-run` |
| `src/admin/routes.py` | Sanitize `file.filename`, validate resolved path, enforce size limit |
| `src/admin/auth.py` | No change (assertion lives in app.py startup) |
| `tests/test_security.py` | New — covers all four changes |

---

## Task 1 — Remove PythonTools / FileTools from dynamic_loader

**Risk of RCE today:** `POST /v1/dynamic-run` with `tools=[{"name":"PythonTools"}]` lets any caller execute arbitrary shell commands on the server. Removing these two entries from the whitelist is zero-impact on real agents (they are configured via `agents.yaml` → `_factory.py`, not via this loader).

**Files:**
- Modify: `src/tools/dynamic_loader.py`
- Test: `tests/test_security.py`

- [ ] **Step 1: Write the failing test**

Create `tests/test_security.py`:

```python
"""Security regression tests."""
from src.tools.dynamic_loader import load_dynamic_tools


def test_dynamic_loader_rejects_python_tools():
    tools = load_dynamic_tools([{"name": "PythonTools"}])
    assert tools == [], "PythonTools must not be instantiated via dynamic loader"


def test_dynamic_loader_rejects_file_tools():
    tools = load_dynamic_tools([{"name": "FileTools"}])
    assert tools == [], "FileTools must not be instantiated via dynamic loader"


def test_dynamic_loader_still_allows_safe_tools():
    tools = load_dynamic_tools([{"name": "DuckDuckGoTools"}])
    assert len(tools) == 1
```

- [ ] **Step 2: Run test to verify it fails**

```
cd d:/Documentos/Projetos/AgnoAgents/Dartha-API-V3
uv run pytest tests/test_security.py -v
```

Expected: first two tests FAIL (tools are currently returned), third PASSES.

- [ ] **Step 3: Remove PythonTools and FileTools from the loader**

Replace the entire `src/tools/dynamic_loader.py`:

```python
from typing import List, Dict, Any
from agno.tools.duckduckgo import DuckDuckGoTools
from src.tools.smart_pandas import SmartPandasTools
from src.tools.interactive import emit_interactive_state

# PythonTools and FileTools are intentionally absent — they allow arbitrary
# filesystem access / code execution and must never be instantiated via an
# unauthenticated HTTP payload.
_SAFE_TOOLS = {"DuckDuckGoTools", "SmartPandasTools", "InteractiveTools"}


def load_dynamic_tools(tools_json: List[Dict[str, Any]]) -> List[Any]:
    """
    Instantiates Agno tools from a JSON list.
    Only tools in _SAFE_TOOLS are allowed; all others are silently skipped.
    """
    agent_tools = []
    for tool_config in tools_json:
        name = tool_config.get("name")
        kwargs = tool_config.get("kwargs", {})

        if name == "DuckDuckGoTools":
            agent_tools.append(DuckDuckGoTools(**kwargs))
        elif name == "SmartPandasTools":
            agent_tools.append(SmartPandasTools(**kwargs))
        elif name == "InteractiveTools":
            agent_tools.append(emit_interactive_state)

    return agent_tools
```

- [ ] **Step 4: Run tests to verify they pass**

```
uv run pytest tests/test_security.py -v
```

Expected: all three tests PASS.

- [ ] **Step 5: Commit**

```bash
git add src/tools/dynamic_loader.py tests/test_security.py
git commit -m "security: remove PythonTools/FileTools from dynamic loader (RCE fix)"
```

---

## Task 2 — Add `Authorization: Bearer` authentication to `/v1/dynamic-run`

The Next.js proxy already fetches `agno_auth_token` from the database and sends it as
`Authorization: Bearer <token>`. This task makes the Agno side validate that token.
Any caller without a valid token gets `403 Forbidden`. If the env var is unset the
endpoint returns `503` (fail-closed, not fail-open).

The token value on the Agno side is `API_SECRET_KEY` in `.env`. The Next.js proxy
stores the same value as `agno_auth_token` in the origins table — they must match.

**Files:**
- Create: `src/middleware/api_key.py`
- Modify: `src/config/settings.py`
- Modify: `src/app.py`
- Test: `tests/test_security.py`

- [ ] **Step 1: Add `API_SECRET_KEY` to settings**

Open `src/config/settings.py`. Inside the `Settings` class, after `ADMIN_SESSION_TTL`, add:

```python
    # Bearer token for /v1/* endpoints — must match agno_auth_token stored in
    # the Next.js origins table. Leave empty to disable the endpoint entirely.
    API_SECRET_KEY: Optional[str] = None
```

Also add at the bottom of the file (after the `settings = Settings()` block):

```python
if settings.API_SECRET_KEY:
    os.environ["API_SECRET_KEY"] = settings.API_SECRET_KEY
```

- [ ] **Step 2: Create the Bearer-token dependency**

Create `src/middleware/api_key.py`:

```python
"""
FastAPI dependency: validates Authorization: Bearer <token> on protected endpoints.
The token must match API_SECRET_KEY from the environment.
"""
import os
from fastapi import Header, HTTPException
from typing import Optional


async def require_bearer_token(authorization: Optional[str] = Header(None)) -> None:
    """
    Raises 403 if the Bearer token is missing or wrong.
    Raises 503 if API_SECRET_KEY is not configured on this server.
    """
    secret = os.getenv("API_SECRET_KEY", "")
    if not secret:
        raise HTTPException(
            status_code=503,
            detail="Endpoint disabled: API_SECRET_KEY is not configured on this server.",
        )

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=403, detail="Missing or malformed Authorization header.")

    token = authorization.removeprefix("Bearer ").strip()
    if token != secret:
        raise HTTPException(status_code=403, detail="Invalid bearer token.")
```

- [ ] **Step 3: Wire dependency onto `/v1/dynamic-run`**

In `src/app.py`, add imports after the existing ones:

```python
from src.middleware.api_key import require_bearer_token
from fastapi import Depends
```

Change the route decorator from:

```python
@app.post("/v1/dynamic-run")
def dynamic_agent_run(payload: DynamicRunRequest):
```

To:

```python
@app.post("/v1/dynamic-run", dependencies=[Depends(require_bearer_token)])
def dynamic_agent_run(payload: DynamicRunRequest):
```

- [ ] **Step 4: Write tests for the Bearer token**

Add to `tests/test_security.py` (append at the bottom):

```python
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient


def _make_test_app():
    """Build a minimal FastAPI app with the bearer dependency wired up."""
    from fastapi import FastAPI, Depends
    from src.middleware.api_key import require_bearer_token

    app = FastAPI()

    @app.post("/v1/dynamic-run", dependencies=[Depends(require_bearer_token)])
    def _dummy():
        return {"ok": True}

    return app


def test_dynamic_run_rejects_missing_auth_header():
    client = TestClient(_make_test_app(), raise_server_exceptions=False)
    with patch.dict("os.environ", {"API_SECRET_KEY": "secret123"}):
        resp = client.post("/v1/dynamic-run", json={})
    assert resp.status_code == 403


def test_dynamic_run_rejects_wrong_token():
    client = TestClient(_make_test_app(), raise_server_exceptions=False)
    with patch.dict("os.environ", {"API_SECRET_KEY": "secret123"}):
        resp = client.post(
            "/v1/dynamic-run", json={},
            headers={"Authorization": "Bearer wrongtoken"}
        )
    assert resp.status_code == 403


def test_dynamic_run_rejects_non_bearer_scheme():
    client = TestClient(_make_test_app(), raise_server_exceptions=False)
    with patch.dict("os.environ", {"API_SECRET_KEY": "secret123"}):
        resp = client.post(
            "/v1/dynamic-run", json={},
            headers={"Authorization": "Basic secret123"}
        )
    assert resp.status_code == 403


def test_dynamic_run_accepts_correct_bearer_token():
    client = TestClient(_make_test_app(), raise_server_exceptions=False)
    with patch.dict("os.environ", {"API_SECRET_KEY": "secret123"}):
        resp = client.post(
            "/v1/dynamic-run", json={},
            headers={"Authorization": "Bearer secret123"}
        )
    # 422 = past auth but missing payload fields — that is expected
    assert resp.status_code in (200, 422)


def test_dynamic_run_returns_503_when_key_not_configured():
    client = TestClient(_make_test_app(), raise_server_exceptions=False)
    with patch.dict("os.environ", {}, clear=True):
        resp = client.post(
            "/v1/dynamic-run", json={},
            headers={"Authorization": "Bearer anything"}
        )
    assert resp.status_code == 503
```

- [ ] **Step 5: Run tests**

```
uv run pytest tests/test_security.py -v
```

Expected: all tests PASS. (The three from Task 1 should still pass too.)

- [ ] **Step 6: Add `API_SECRET_KEY` to `.env`**

Generate a strong random token and add to `.env`:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Add to `.env`:

```
API_SECRET_KEY=<generated-value>
```

Then store this **same value** as `agno_auth_token` in the Next.js origins table for this server's origin record.

- [ ] **Step 7: Commit**

```bash
git add src/middleware/api_key.py src/config/settings.py src/app.py tests/test_security.py .env
git commit -m "security: add Authorization Bearer validation to /v1/dynamic-run"
```

---

## Task 3 — Add CORS allowlist

Without `CORSMiddleware`, the browser will respect the same-origin policy by default, **but** the API itself will still serve all origins when called server-to-server (e.g., scripted attacks, Postman). CORS restricts the browser. Combined with Task 2 (API key), the API is now protected end-to-end.

**Files:**
- Modify: `src/config/settings.py`
- Modify: `src/app.py`
- Test: `tests/test_security.py`

- [ ] **Step 1: Add `CORS_ALLOWED_ORIGINS` to settings**

In `src/config/settings.py`, inside the `Settings` class, add after `API_SECRET_KEY`:

```python
    # CORS: comma-separated list of allowed origins.
    # Example: "https://app.liderandocomia.com,https://admin.liderandocomia.com"
    # Set to "*" only for local development (never in production).
    CORS_ALLOWED_ORIGINS: str = ""
```

No need to sync to `os.environ` — it is read directly from `settings`.

- [ ] **Step 2: Add CORSMiddleware in app.py**

In `src/app.py`, after the line `from starlette.requests import Request`, add:

```python
from fastapi.middleware.cors import CORSMiddleware
```

Then, immediately after the line `app = agent_os.get_app()` (and **before** `app.include_router(...)` calls), add:

```python
_cors_origins = [o.strip() for o in settings.CORS_ALLOWED_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)
```

> **Important:** `allow_origins=["*"]` with `allow_credentials=True` is rejected by browsers. Always use an explicit list in production.

- [ ] **Step 3: Write CORS test**

Add to `tests/test_security.py`:

```python
def test_cors_blocks_unlisted_origin():
    """A request from an unlisted origin must not receive ACAO header."""
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware

    app = FastAPI()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["https://allowed.example.com"],
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    @app.get("/ping")
    def ping():
        return {"ok": True}

    client = TestClient(app)
    resp = client.get("/ping", headers={"Origin": "https://evil.example.com"})
    assert "access-control-allow-origin" not in resp.headers


def test_cors_allows_listed_origin():
    """A request from a listed origin receives the ACAO header."""
    from fastapi import FastAPI
    from fastapi.middleware.cors import CORSMiddleware

    app = FastAPI()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["https://allowed.example.com"],
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )

    @app.get("/ping")
    def ping():
        return {"ok": True}

    client = TestClient(app)
    resp = client.get("/ping", headers={"Origin": "https://allowed.example.com"})
    assert resp.headers.get("access-control-allow-origin") == "https://allowed.example.com"
```

- [ ] **Step 4: Run tests**

```
uv run pytest tests/test_security.py -v
```

Expected: all tests PASS.

- [ ] **Step 5: Add `CORS_ALLOWED_ORIGINS` to `.env`**

Add the frontend domain(s) to `.env`. Replace with your actual production URL(s):

```
CORS_ALLOWED_ORIGINS=https://app.liderandocomia.com,https://admin.liderandocomia.com
```

For local development only (safe because Task 2 guards the API endpoint separately):

```
CORS_ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5173
```

- [ ] **Step 6: Commit**

```bash
git add src/config/settings.py src/app.py tests/test_security.py .env
git commit -m "security: add CORS allowlist middleware"
```

---

## Task 4 — Sanitize admin upload filename + assert non-default ADMIN_SECRET_KEY

Two sub-items handled in one commit because they are both in the admin surface.

**4a — Filename sanitization and path traversal prevention**

A malicious upload `filename=../../etc/passwd` would write outside `data/RAG/`. Fix: strip to basename only and assert the resolved destination is inside the dept directory.

**4b — Startup assertion for ADMIN_SECRET_KEY**

If `ADMIN_SECRET_KEY` equals the hardcoded default, the server refuses to start. This prevents silent misconfiguration in production.

**Files:**
- Modify: `src/admin/routes.py`
- Modify: `src/config/settings.py`
- Modify: `src/app.py`
- Test: `tests/test_security.py`

- [ ] **Step 1: Add `MAX_UPLOAD_MB` to settings**

In `src/config/settings.py`, inside the `Settings` class, add after `CORS_ALLOWED_ORIGINS`:

```python
    # Maximum file size (MB) accepted by the admin upload endpoint.
    MAX_UPLOAD_MB: int = 50
```

- [ ] **Step 2: Write failing tests for filename sanitization**

Add to `tests/test_security.py`:

```python
from pathlib import Path


def test_upload_filename_strips_path_traversal():
    """Path.name should strip directory components from uploaded filenames."""
    malicious = "../../etc/passwd"
    safe_name = Path(malicious).name
    assert safe_name == "passwd"
    assert "/" not in safe_name
    assert "\\" not in safe_name


def test_upload_resolved_path_stays_inside_dept_dir(tmp_path):
    """Resolved destination must be a child of the department directory."""
    dept_dir = tmp_path / "Marketing"
    dept_dir.mkdir()

    safe_filename = Path("../../evil.txt").name  # "evil.txt"
    dest = dept_dir / safe_filename
    assert dest.resolve().is_relative_to(dept_dir.resolve())
```

- [ ] **Step 3: Run tests to verify they pass already (pure logic tests)**

```
uv run pytest tests/test_security.py::test_upload_filename_strips_path_traversal tests/test_security.py::test_upload_resolved_path_stays_inside_dept_dir -v
```

Expected: PASS (these test the fix logic we are about to apply).

- [ ] **Step 4: Apply sanitization to the upload route**

In `src/admin/routes.py`, find the `upload_document` function (line ~251). Replace the filename and path assignment block:

**Before (lines ~263–279):**
```python
    ext = Path(file.filename).suffix.lstrip(".").lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Tipo de arquivo não permitido: .{ext}")

    display_name = departments[dept]

    existing = admin_db.get_document_by_filename(display_name, file.filename)
    if existing and not replace:
        return {"conflict": True, "doc_id": existing.id, "filename": file.filename}

    if existing and replace:
        _delete_document_data(existing)

    dept_dir = RAG_DATA_DIR / dept.capitalize()
    dept_dir.mkdir(parents=True, exist_ok=True)
    file_path = dept_dir / file.filename
    content = await file.read()
    file_path.write_bytes(content)
```

**After:**
```python
    # Strip any directory components — prevents path traversal attacks.
    safe_filename = Path(file.filename).name
    if not safe_filename:
        raise HTTPException(status_code=400, detail="Nome de arquivo inválido.")

    ext = Path(safe_filename).suffix.lstrip(".").lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"Tipo de arquivo não permitido: .{ext}")

    display_name = departments[dept]

    existing = admin_db.get_document_by_filename(display_name, safe_filename)
    if existing and not replace:
        return {"conflict": True, "doc_id": existing.id, "filename": safe_filename}

    if existing and replace:
        _delete_document_data(existing)

    dept_dir = RAG_DATA_DIR / dept.capitalize()
    dept_dir.mkdir(parents=True, exist_ok=True)
    file_path = dept_dir / safe_filename

    # Guard: resolved path must stay inside dept_dir (defence-in-depth).
    if not file_path.resolve().is_relative_to(dept_dir.resolve()):
        raise HTTPException(status_code=400, detail="Nome de arquivo inválido.")

    content = await file.read()

    from src.config.settings import settings as _settings
    max_bytes = _settings.MAX_UPLOAD_MB * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"Arquivo muito grande. Limite: {_settings.MAX_UPLOAD_MB} MB.",
        )

    file_path.write_bytes(content)
```

Also update the `admin_db.create_document` call two lines below to use `safe_filename` instead of `file.filename`:

```python
    doc = admin_db.create_document(
        department=display_name,
        filename=safe_filename,
        file_path=str(file_path),
        file_size=len(content),
        file_type=ext,
    )
```

- [ ] **Step 5: Add startup assertion for ADMIN_SECRET_KEY**

In `src/app.py`, find the line `_log_available_providers()` near the top (around line 86). Immediately **before** it, add:

```python
_DEFAULT_SECRET = "change-me-in-production-32chars!!"
if settings.ADMIN_SECRET_KEY == _DEFAULT_SECRET:
    import sys
    print(
        "\n[SECURITY] FATAL: ADMIN_SECRET_KEY is set to the default value.\n"
        "           Set a strong random key in your .env file:\n"
        "           python -c \"import secrets; print(secrets.token_urlsafe(32))\"\n",
        file=sys.stderr,
    )
    sys.exit(1)
```

- [ ] **Step 6: Add ADMIN_SECRET_KEY and ADMIN_PASSWORD_HASH to `.env`**

Generate values if not already present:

```bash
# Generate secret key
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Generate bcrypt hash for admin password
uv run python -c "from passlib.context import CryptContext; print(CryptContext(schemes=['bcrypt']).hash('your_password_here'))"
```

Add to `.env`:
```
ADMIN_SECRET_KEY=<generated-secret-key>
ADMIN_PASSWORD_HASH=<bcrypt-hash>
```

- [ ] **Step 7: Run all security tests**

```
uv run pytest tests/test_security.py -v
```

Expected: all tests PASS.

- [ ] **Step 8: Verify server still starts**

```bash
uv run python -c "from src.config.settings import settings; print('Settings OK:', settings.PORT)"
```

Expected: prints `Settings OK: 7777` (or your configured port) without error.

- [ ] **Step 9: Commit**

```bash
git add src/admin/routes.py src/config/settings.py src/app.py tests/test_security.py .env
git commit -m "security: sanitize upload filename, enforce ADMIN_SECRET_KEY, add upload size limit"
```

---

## Final Verification

- [ ] Run the full test suite:

```
uv run pytest tests/ -v
```

Expected: all existing tests still pass, all new security tests pass.

- [ ] Smoke test the admin panel manually — upload a file, confirm it lands in the correct folder.

- [ ] Confirm the server refuses to start if `ADMIN_SECRET_KEY` is the default (temporarily remove it from `.env`, start the server, restore it).

---

## Environment Variables Added (summary for ops)

| Variable | Required | Description |
|---|---|---|
| `API_SECRET_KEY` | Yes (production) | Bearer token for `/v1/dynamic-run`. Must match `agno_auth_token` in the Next.js origins table. Generate with `secrets.token_urlsafe(32)`. |
| `CORS_ALLOWED_ORIGINS` | Yes (production) | Comma-separated list of allowed browser origins. |
| `MAX_UPLOAD_MB` | No (default: 50) | Max upload size in MB for admin panel. |
| `ADMIN_SECRET_KEY` | Yes | JWT signing key for admin session. Must not be the default. |
| `ADMIN_PASSWORD_HASH` | Yes | bcrypt hash of the admin password. |
