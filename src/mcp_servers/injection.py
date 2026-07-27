import logging
import re
from contextvars import ContextVar
from typing import Any, Dict, List, Optional
from urllib.parse import parse_qs

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

log = logging.getLogger(__name__)

# Stores raw server records (not connected MCPTools) — safe to pass across tasks
_mcp_server_ctx: ContextVar[List[Any]] = ContextVar("_mcp_server_ctx", default=[])

_RUNS_PATH_RE = re.compile(r"/(agents|teams|workflows)/[^/]+/runs$")


def _load_user_servers(user_id: str) -> List[Any]:
    """
    Load user's active MCP server records from DB.
    Pure sync — intended for run_in_executor.
    """
    try:
        from src.mcp_servers.crud import get_user_servers
        from src.mcp_servers.db import get_session
    except Exception as e:
        log.warning(f"[MCP] Import error — skipping injection: {e}")
        return []

    db = None
    try:
        db = get_session()
        return get_user_servers(db, user_id)
    except Exception as e:
        log.warning(f"[MCP] DB unavailable for user {user_id} — skipping: {e}")
        return []
    finally:
        if db is not None:
            db.close()


def _extract_user_id(body: bytes, content_type: str) -> Optional[str]:
    """Extract user_id from request body across all common content types."""
    try:
        if "application/x-www-form-urlencoded" in content_type:
            parsed = parse_qs(body.decode("utf-8", errors="replace"))
            ids = parsed.get("user_id", [])
            return ids[0] if ids else None

        if "multipart/form-data" in content_type:
            text = body.decode("utf-8", errors="replace")
            m = re.search(r'name="user_id"\r\n\r\n([^\r\n]+)', text)
            return m.group(1) if m else None

        if "application/json" in content_type:
            import json
            data = json.loads(body.decode("utf-8", errors="replace"))
            return data.get("user_id") if isinstance(data, dict) else None

    except Exception as e:
        log.warning(f"[MCP] Could not parse user_id from body: {e}")

    return None


class MCPInjectionMiddleware(BaseHTTPMiddleware):
    """
    Reads user_id from request body, loads MCP server records from DB,
    and stores them in a ContextVar.

    MCPTools are NOT instantiated or connected here. Connection happens inside
    the agent's run task via patch_connect_mcp_tools(), which runs in the same
    asyncio Task as the agent — required by anyio's cancel scope model.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.method != "POST" or not _RUNS_PATH_RE.search(request.url.path):
            return await call_next(request)

        body = await request.body()
        content_type = request.headers.get("content-type", "")
        user_id = _extract_user_id(body, content_type)

        if user_id:
            import asyncio
            loop = asyncio.get_running_loop()
            servers = await loop.run_in_executor(None, _load_user_servers, user_id)
            log.debug(f"[MCP] Loaded {len(servers)} server(s) for user {user_id}")
        else:
            servers = []

        token = _mcp_server_ctx.set(servers)
        try:
            return await call_next(request)
        finally:
            _mcp_server_ctx.reset(token)


def patch_connect_mcp_tools() -> None:
    """
    Monkey-patch agno.agent._init.connect_mcp_tools to inject and connect
    the user's MCPTools inside the agent's run task.

    This is the only correct place to connect MCPTools: anyio cancel scopes
    are bound to the asyncio Task where they're created.  The agent runs in
    a sub-task spawned by StreamingResponse — so tools connected here live
    and die in the same task context as the agent.

    Called once at app startup.
    """
    import agno.agent._init as _agno_init

    _original = _agno_init.connect_mcp_tools

    async def _patched(agent) -> None:
        # Connect tools already on the agent (original behaviour)
        await _original(agent)

        # Inject user's MCP servers from context
        servers = _mcp_server_ctx.get()
        if not servers:
            return

        try:
            from agno.tools.mcp import MCPTools
            from agno.tools.mcp.params import StreamableHTTPClientParams
            from src.mcp_servers.encryption import decrypt_credentials
        except Exception as e:
            log.warning(f"[MCP] Import error in connect patch: {e}")
            return

        for server in servers:
            try:
                headers: Dict[str, str] = {}
                if server.auth_type in ("api_key", "oauth") and server.encrypted_credentials:
                    token = decrypt_credentials(server.encrypted_credentials)
                    headers["Authorization"] = f"Bearer {token}"
                elif server.auth_type == "nango":
                    from src.config.settings import settings as _settings
                    if _settings.NANGO_SECRET_KEY:
                        headers["Authorization"] = f"Bearer {_settings.NANGO_SECRET_KEY}"
                    if server.nango_connection_id:
                        headers["Nango-Connection-Id"] = server.nango_connection_id

                params = StreamableHTTPClientParams(
                    url=server.url,
                    headers=headers or None,
                )
                tool = MCPTools(transport="streamable-http", server_params=params)

                try:
                    import anyio
                    with anyio.fail_after(10):
                        await tool.connect()
                except Exception as connect_err:
                    log.warning(f"[MCP] Could not connect to {server.url}: {connect_err}")
                    try:
                        await tool.close()
                    except Exception:
                        pass
                    continue

                if not tool.initialized:
                    log.warning(f"[MCP] Tool not initialized after connect: {server.url}")
                    try:
                        await tool.close()
                    except Exception:
                        pass
                    continue

                # Add to agent.tools so aget_tools includes it in the model call
                existing = list(agent.tools or [])
                agent.tools = existing + [tool]

                # Register for disconnect at run end (agno calls disconnect_mcp_tools)
                agent._mcp_tools_initialized_on_run.append(tool)
                log.info(f"[MCP] Injected {server.url} for agent {agent.id}")

            except Exception as e:
                log.warning(f"[MCP] Failed to connect {server.url}: {e}")

    _agno_init.connect_mcp_tools = _patched
    log.info("[MCP] Patched agno.agent._init.connect_mcp_tools for per-user injection")
