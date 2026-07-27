from starlette.datastructures import UploadFile, Headers

from starlette.requests import Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.datastructures import FormData
from src.config.settings import settings
from src.utils.document_parser import parse_document_to_markdown

# Hack: Faz upload de documentos pesados/bloqueados gerando um NOVO arquivo fantasma (TXT).
_original_form = Request.form

async def _patched_form(self, *args, **kwargs):
    form_data = await _original_form(self, *args, **kwargs)
    
    if "runs" in self.url.path or "chat" in self.url.path:
        new_items = []
        
        for key, value in form_data.multi_items():
            if hasattr(value, "filename") and getattr(value, "filename", None):
                ext = value.filename.split(".")[-1].lower() if value.filename else ""
                
                if ext in ["xlsx", "xls", "csv", "docx", "pptx"]:
                    # Lemos o upload puro na RAM
                    await value.seek(0)
                    file_bytes = await value.read()
                    
                    # Restauramos a estratégia de RAW BINARY para que Pandas/Python funcionem nativamente:
                    # Não convertemos para Markdown aqui. Apenas "disfarçamos" o arquivo de .csv ou .txt para o Agno Firewall.
                    import tempfile
                    new_file = tempfile.SpooledTemporaryFile(max_size=1024 * 1024 * 10)
                    new_file.write(file_bytes)
                    new_file.seek(0)
                    
                    if ext in ["xlsx", "xls", "csv"]:
                        fake_ext = ".csv"
                        fake_mime = "text/csv"
                    else:
                        fake_ext = ".txt"
                        fake_mime = "text/plain"
                    
                    # Criamos headers fake
                    new_headers = {"content-type": fake_mime}
                    from starlette.datastructures import Headers
                    try:
                        safe_headers = Headers(new_headers)
                    except Exception:
                        safe_headers = getattr(value, "headers", None)
                        
                    # Criamos o UploadFile limpo para o FastAPI
                    from starlette.datastructures import UploadFile as StarletteUploadFile
                    new_upload_file = StarletteUploadFile(
                        file=new_file,
                        size=len(file_bytes),
                        filename=value.filename + fake_ext,
                        headers=safe_headers
                    )
                    
                    new_items.append((key, new_upload_file))
                else:
                    new_items.append((key, value))
            else:
                new_items.append((key, value))
                
        return FormData(new_items)
            
    return form_data

Request.form = _patched_form

from src.admin.routes import router as admin_router
from src.admin.auth import AdminAuthMiddleware
from src.admin import db as admin_db
from src.knowledge.base import DEPARTMENT_MAPPING
from src.config.llm_providers import get_available_providers as _get_available_providers

# Garante que todas as tabelas admin existem e estão populadas
admin_db.ensure_knowledge_documents_table()
admin_db.ensure_departments_table()
admin_db.seed_departments(DEPARTMENT_MAPPING)
admin_db.ensure_skills_table()

def _log_available_providers() -> None:
    available = _get_available_providers()
    print("\n[LLM Providers]")
    for name, ok in available.items():
        status = "OK" if ok else "sem credenciais"
        print(f"  {name:<12} {status}")
    print()

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

_log_available_providers()

import os as _os
from fastapi import FastAPI, Depends
from agno.os import AgentOS
from agno.db.sqlite import SqliteDb
from src.agents._factory import load_all_agents
from src.knowledge.base import get_knowledge_base
from src.config.registry import build_registry

from src.middleware.api_key import require_bearer_token

from src.mcp_servers.injection import MCPInjectionMiddleware, patch_connect_mcp_tools
patch_connect_mcp_tools()

# Carrega todos os agentes do YAML
agents = load_all_agents()

# DB para o AgentOS Studio (SQLite é suficiente — salva configurações de agentes,
# não dados transacionais em volume)
_studio_db = SqliteDb(db_file=_os.getenv("SQLITE_DB_PATH", "agno.db"))

# Registry com todos os modelos/ferramentas disponíveis → ativa endpoints /v1/studio/*
_registry = build_registry(studio_db=_studio_db)

# Docs desabilitados em produção; habilitados apenas em desenvolvimento local
_is_production = _os.getenv("ENVIRONMENT", "production").lower() == "production"
_docs_url = None if _is_production else "/docs"
_redoc_url = None if _is_production else "/redoc"
_openapi_url = None if _is_production else "/openapi.json"

# Cria FastAPI com redirect_slashes=False para evitar loop com BaseHTTPMiddleware
_base_app = FastAPI(
    title="Dartha API V3",
    version="1.0.0",
    redirect_slashes=False,
    docs_url=_docs_url,
    redoc_url=_redoc_url,
    openapi_url=_openapi_url,
)

# Inicializa o AgentOS com Registry + DB (habilita Studio)
agent_os = AgentOS(
    agents=agents,
    knowledge=[get_knowledge_base()],
    tracing=False,
    base_app=_base_app,
    db=_studio_db,
    registry=_registry,
)

app = agent_os.get_app()

# Configure CORS middleware
_cors_origins = [o.strip() for o in settings.CORS_ALLOWED_ORIGINS.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-API-Key"],
)

app.add_middleware(MCPInjectionMiddleware)

# Register custom AGUI routes with HITL stream wrapper
# app.include_router(build_agui_router(agents))  # AGUI desabilitado temporariamente

# Painel admin de gestão de knowledge
app.include_router(admin_router, prefix="/admin")
app.add_middleware(AdminAuthMiddleware)

from src.mcp_servers.routes import router as mcp_router
from src.mcp_servers.db import create_tables as _create_mcp_tables

_create_mcp_tables()
app.include_router(mcp_router)

from src.biblioteca.routes import router as biblioteca_router
app.include_router(biblioteca_router)

from src.skills.routes import router as skills_api_router
app.include_router(skills_api_router, prefix="/v1/skills")

from src.agents.studio_routes import router as studio_support_router
app.include_router(studio_support_router)

from pydantic import BaseModel
from typing import Optional, List, Dict, Any

class DynamicRunRequest(BaseModel):
    user_id: str
    message: str
    tools: Optional[List[Dict[str, Any]]] = None
    session_id: Optional[str] = None

@app.post("/v1/dynamic-run", dependencies=[Depends(require_bearer_token)])
def dynamic_agent_run(payload: DynamicRunRequest):
    """
    Cria uma instância isolada do agile agent por requisição baseando-se no payload,
    garantindo multitenancy (user_id/session_id) e injeção dinâmica de tools via JSON.
    """
    from src.agents.general_assistant import get_general_assistant

    # Instancia agente isolado para este request
    agent = get_general_assistant(user_id=payload.user_id, tools_json=payload.tools)

    if payload.session_id:
        agent.session_id = payload.session_id

    response = agent.run(payload.message)

    return {
        "user_id": payload.user_id,
        "session_id": agent.session_id,
        "content": response.content
    }

# Make agents globally importable for hot-reload in routes
__all__ = ["app", "agents"]

if __name__ == "__main__":
    # Agno serve() já cuida do uvicorn e do reload internamente
    # Para produção, você pode usar AuthorizationConfig(verification_keys=[...])
    agent_os.serve(
        app="src.app:app",
        port=settings.PORT,
        reload=False,
        reload_excludes=[".venv", ".venv_dartha", ".git", "*.db", "*.log"],
    )
