"""
Router FastAPI para o painel admin de gestão de knowledge.
Prefixo: /admin  —  montado em src/app.py
"""
import os
import re
import unicodedata
from pathlib import Path
from typing import Annotated, Optional, List, Dict, Any
import json as json_module
import sqlite3

from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, Form, HTTPException, Request, UploadFile, File, BackgroundTasks, Query
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates

from src.admin import db as admin_db
from src.admin.auth import (
    COOKIE_NAME,
    check_credentials,
    create_token,
    get_current_admin,
)
from src.admin.queue import process_document, sse_generator
from src.knowledge.base import CHROMA_HOST, CHROMA_PORT, CHROMA_COLLECTION
from src.config.settings import settings

router = APIRouter(tags=["Admin"])

_templates_dir = Path(__file__).parent / "templates"
templates = Jinja2Templates(directory=str(_templates_dir))
templates.env.globals["company_name"] = settings.COMPANY_NAME

RAG_DATA_DIR = Path("data/RAG")
ALLOWED_EXTENSIONS = {
    "pdf", "docx", "doc", "xlsx", "xls", "pptx", "ppt",
    "csv", "txt", "md", "png", "jpg", "jpeg",
}


def _load_departments() -> dict:
    """Retorna {slug: display_name} carregado do banco de dados."""
    return {d.slug: d.display_name for d in admin_db.get_all_departments()}


def _slugify(text: str) -> str:
    """Converte texto para slug URL-safe sem acentos. Ex: 'Tributário' → 'tributario'."""
    normalized = unicodedata.normalize("NFD", text.lower().strip())
    ascii_text = "".join(c for c in normalized if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9]+", "-", ascii_text).strip("-") or "setor"


# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: str = ""):
    return templates.TemplateResponse("login.html", {"request": request, "error": error})


@router.post("/login")
async def login(
    request: Request,
    username: Annotated[str, Form()],
    password: Annotated[str, Form()],
):
    if not check_credentials(username, password):
        return RedirectResponse("/admin/login?error=Credenciais+inv%C3%A1lidas", status_code=303)

    token = create_token()
    response = RedirectResponse("/admin", status_code=303)
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="strict",
        max_age=int(os.getenv("ADMIN_SESSION_TTL", "28800")),
    )
    return response


@router.get("/logout")
async def logout():
    response = RedirectResponse("/admin/login", status_code=303)
    response.delete_cookie(COOKIE_NAME)
    return response


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------

@router.get("", response_class=HTMLResponse)
async def dashboard(request: Request, admin: str = Depends(get_current_admin)):
    depts = admin_db.get_all_departments()
    counts = admin_db.count_by_department()
    dept_data = []
    for d in depts:
        c = counts.get(d.display_name, {})
        dept_data.append({
            "slug": d.slug,
            "name": d.display_name,
            "total": c.get("total", 0),
            "indexed": c.get("indexed", 0),
            "processing": c.get("processing", 0),
            "error": c.get("error", 0),
            "pending": c.get("pending", 0),
        })
    sectors = [
        {"slug": d.slug, "display_name": d.display_name, "is_system": d.is_system}
        for d in depts
    ]
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request, "departments": dept_data, "sectors": sectors, "admin": admin},
    )


# ---------------------------------------------------------------------------
# Sector management (CRUD de setores)
# — rotas registradas ANTES de /{dept} para evitar conflito de parâmetro
# ---------------------------------------------------------------------------

@router.post("/sectors")
async def create_sector(
    display_name: Annotated[str, Form()],
    admin: str = Depends(get_current_admin),
):
    display_name = display_name.strip()
    if not display_name:
        raise HTTPException(status_code=400, detail="Nome não pode ser vazio")

    if admin_db.get_department_by_display_name(display_name):
        return {"ok": False, "error": f"Já existe um setor com o nome '{display_name}'"}

    # Gera slug único
    base_slug = _slugify(display_name)
    slug = base_slug
    counter = 2
    while admin_db.get_department_by_slug(slug):
        slug = f"{base_slug}-{counter}"
        counter += 1

    dept = admin_db.create_department(slug, display_name)
    return {"ok": True, "slug": dept.slug, "display_name": dept.display_name}


@router.patch("/sectors/{slug}")
async def rename_sector(
    slug: str,
    new_name: Annotated[str, Form()],
    admin: str = Depends(get_current_admin),
):
    new_name = new_name.strip()
    if not new_name:
        raise HTTPException(status_code=400, detail="Nome não pode ser vazio")

    dept = admin_db.get_department_by_slug(slug)
    if not dept:
        raise HTTPException(status_code=404, detail="Setor não encontrado")
    if dept.is_system:
        raise HTTPException(status_code=403, detail="Setor do sistema não pode ser renomeado")

    existing = admin_db.get_department_by_display_name(new_name)
    if existing and existing.slug != slug:
        return {"ok": False, "error": f"Já existe um setor com o nome '{new_name}'"}

    # Atualiza DB (e knowledge_documents em cascata)
    admin_db.rename_department(slug, new_name)

    # Atualiza metadata no ChromaDB para os docs afetados
    try:
        import chromadb as _chromadb
        client = _chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
        collection = client.get_collection(CHROMA_COLLECTION)

        # Coleta todos os chroma_ids dos docs deste departamento (já renomeado no DB)
        docs = admin_db.get_documents_by_department(new_name)
        all_ids = [cid for doc in docs for cid in doc.chroma_ids_list()]

        if all_ids:
            results = collection.get(ids=all_ids, include=["metadatas"])
            updated_metadatas = [
                {**meta, "department": new_name}
                for meta in results["metadatas"]
            ]
            collection.update(ids=results["ids"], metadatas=updated_metadatas)
    except Exception as e:
        print(f"[Admin] Aviso ao atualizar ChromaDB metadata no rename: {e}")

    return {"ok": True}


@router.delete("/sectors/{slug}")
async def delete_sector(
    slug: str,
    admin: str = Depends(get_current_admin),
):
    dept = admin_db.get_department_by_slug(slug)
    if not dept:
        raise HTTPException(status_code=404, detail="Setor não encontrado")
    if dept.is_system:
        raise HTTPException(status_code=403, detail="Setor do sistema não pode ser removido")

    # Remove todos os documentos do setor (ChromaDB + disco + DB)
    docs = admin_db.get_documents_by_department(dept.display_name)
    for doc in docs:
        _delete_document_data(doc)

    # Remove o diretório data/RAG/{slug}/ se existir
    try:
        import shutil
        dept_dir = RAG_DATA_DIR / slug.capitalize()
        if dept_dir.exists():
            shutil.rmtree(dept_dir, ignore_errors=True)
    except Exception:
        pass

    admin_db.delete_department_record(slug)
    return {"ok": True}


# ---------------------------------------------------------------------------
# Department detail
# ---------------------------------------------------------------------------

@router.get("/{dept}", response_class=HTMLResponse)
async def department_detail(dept: str, request: Request, admin: str = Depends(get_current_admin)):
    departments = _load_departments()
    if dept not in departments:
        raise HTTPException(status_code=404, detail="Departamento não encontrado")
    display_name = departments[dept]
    docs = admin_db.get_documents_by_department(display_name)
    # Converte dataclasses para dicts para o tojson do Jinja2
    import dataclasses
    docs_data = [dataclasses.asdict(doc) for doc in docs]
    return templates.TemplateResponse(
        "department.html",
        {
            "request": request,
            "dept_slug": dept,
            "dept_name": display_name,
            "documents": docs_data,
            "admin": admin,
            "allowed_extensions": ", ".join(f".{e}" for e in sorted(ALLOWED_EXTENSIONS)),
        },
    )


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------

@router.post("/{dept}/upload")
async def upload_document(
    dept: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    replace: bool = False,
    admin: str = Depends(get_current_admin),
):
    departments = _load_departments()
    if dept not in departments:
        raise HTTPException(status_code=404, detail="Departamento não encontrado")

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

    doc = admin_db.create_document(
        department=display_name,
        filename=safe_filename,
        file_path=str(file_path),
        file_size=len(content),
        file_type=ext,
    )

    background_tasks.add_task(process_document, doc.id)
    return {"doc_id": doc.id, "filename": safe_filename, "status": "pending"}


# ---------------------------------------------------------------------------
# Delete document
# ---------------------------------------------------------------------------

@router.delete("/{dept}/docs/{doc_id}")
async def delete_document(
    dept: str,
    doc_id: str,
    admin: str = Depends(get_current_admin),
):
    departments = _load_departments()
    if dept not in departments:
        raise HTTPException(status_code=404, detail="Departamento não encontrado")

    doc = admin_db.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Documento não encontrado")

    _delete_document_data(doc)
    return {"ok": True}


def _delete_document_data(doc: admin_db.KnowledgeDocument) -> None:
    """Remove vetores do ChromaDB, arquivo em disco e registro no DB."""
    chroma_ids = doc.chroma_ids_list()
    if chroma_ids:
        try:
            import chromadb as _chromadb
            client = _chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
            collection = client.get_collection(CHROMA_COLLECTION)
            collection.delete(ids=chroma_ids)
        except Exception as e:
            print(f"[Admin] Aviso ao deletar do ChromaDB: {e}")

    try:
        Path(doc.file_path).unlink(missing_ok=True)
    except Exception:
        pass

    admin_db.delete_document(doc.id)


# ---------------------------------------------------------------------------
# SSE — progresso em tempo real
# ---------------------------------------------------------------------------

@router.get("/queue/events")
async def queue_events(doc_id: str, admin: str = Depends(get_current_admin)):
    return StreamingResponse(
        sse_generator(doc_id),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ---------------------------------------------------------------------------
# Skills Management (Database-backed)
# ---------------------------------------------------------------------------

class SkillFileInput(BaseModel):
    path: str = Field(..., description="Relative path, e.g. 'scripts/analyze.py' or 'references/guide.md'")
    content: str


_VALID_FILE_PREFIX = re.compile(r"^(scripts|references)/[a-zA-Z0-9_\-\.]+$")


def _validate_skill_files(files: List[SkillFileInput]) -> Optional[str]:
    """Return error string if any file path is invalid, else None."""
    for f in files:
        if not _VALID_FILE_PREFIX.match(f.path):
            return f"Invalid file path '{f.path}'. Must start with 'scripts/' or 'references/' and use safe characters."
    return None


class SkillCreateRequest(BaseModel):
    name: str = Field(..., max_length=64)
    description: str = Field(..., max_length=1024)
    instructions: str
    department: Optional[str] = None
    license: Optional[str] = None
    compatibility: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    allowed_tools: Optional[List[str]] = None
    files: Optional[List[SkillFileInput]] = None


class SkillUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, max_length=64)
    description: Optional[str] = Field(None, max_length=1024)
    instructions: Optional[str] = None
    department: Optional[str] = None
    license: Optional[str] = None
    compatibility: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    allowed_tools: Optional[List[str]] = None
    version: Optional[int] = None
    files: Optional[List[SkillFileInput]] = None  # If provided, replaces all existing files


def _reload_agent_skills():
    """Trigger reload of skills in all agents after CRUD operations."""
    try:
        from src.app import agents
        for agent in agents:
            if hasattr(agent, 'skills') and agent.skills:
                try:
                    agent.skills.reload()
                except Exception as e:
                    print(f"[Warning] Failed to reload skills for agent {agent.name}: {e}")
    except Exception as e:
        print(f"[Warning] Could not reload agent skills: {e}")


@router.get("/skills")
async def list_skills(
    department: Optional[str] = Query(None),
    admin: str = Depends(get_current_admin)
):
    """List all active skills, optionally filtered by department."""
    try:
        skills = admin_db.get_all_skills(department=department, include_global=True)
        return {
            "ok": True,
            "data": [
                {
                    "id": s.id,
                    "name": s.name,
                    "description": s.description,
                    "department": s.department,
                    "created_at": s.created_at,
                    "updated_at": s.updated_at,
                    "version": s.version,
                }
                for s in skills
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/skills/{skill_id}")
async def get_skill_detail(
    skill_id: str,
    admin: str = Depends(get_current_admin)
):
    """Get detailed skill information."""
    skill = admin_db.get_skill(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    files = admin_db.get_skill_files(skill.id)
    return {
        "ok": True,
        "data": {
            "id": skill.id,
            "name": skill.name,
            "description": skill.description,
            "instructions": skill.instructions,
            "department": skill.department,
            "license": skill.license,
            "compatibility": skill.compatibility,
            "metadata": json_module.loads(skill.metadata) if skill.metadata else None,
            "allowed_tools": json_module.loads(skill.allowed_tools) if skill.allowed_tools else None,
            "created_by": skill.created_by,
            "created_at": skill.created_at,
            "updated_at": skill.updated_at,
            "version": skill.version,
            "is_active": bool(skill.is_active),
            "files": [{"path": f.path, "content": f.content} for f in files],
        }
    }


@router.post("/skills")
async def create_skill(
    payload: SkillCreateRequest,
    admin: str = Depends(get_current_admin)
):
    """Create a new skill."""
    # Validate name format using Agno's validator
    try:
        from agno.skills.validator import _validate_name, _validate_description
        errors = []
        errors.extend(_validate_name(payload.name))
        errors.extend(_validate_description(payload.description))

        if errors:
            return {"ok": False, "error": "; ".join(errors)}
    except ImportError:
        # If validators not available, just check basic rules
        if not payload.name or len(payload.name) > 64:
            return {"ok": False, "error": "Invalid skill name"}

    # Check for name conflict
    existing = admin_db.get_skill_by_name(payload.name)
    if existing:
        return {"ok": False, "error": f"Skill with name '{payload.name}' already exists"}

    if payload.files:
        err = _validate_skill_files(payload.files)
        if err:
            return {"ok": False, "error": err}

    try:
        skill = admin_db.create_skill(
            name=payload.name,
            description=payload.description,
            instructions=payload.instructions,
            department=payload.department,
            license=payload.license,
            compatibility=payload.compatibility,
            metadata=payload.metadata,
            allowed_tools=payload.allowed_tools,
            created_by=admin,
        )

        if payload.files:
            admin_db.replace_skill_files(
                skill.id,
                [{"path": f.path, "content": f.content} for f in payload.files],
            )

        # Trigger hot-reload of skills in agents
        _reload_agent_skills()

        return {
            "ok": True,
            "data": {"id": skill.id, "name": skill.name, "version": skill.version}
        }
    except sqlite3.IntegrityError as e:
        return {"ok": False, "error": f"Database constraint violation: {str(e)}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/skills/{skill_id}")
async def update_skill(
    skill_id: str,
    payload: SkillUpdateRequest,
    admin: str = Depends(get_current_admin)
):
    """Update an existing skill."""
    skill = admin_db.get_skill(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    # Validate updated fields
    try:
        from agno.skills.validator import _validate_name, _validate_description
        errors = []
        if payload.name is not None:
            errors.extend(_validate_name(payload.name))
            # Check for name conflict with other skills
            existing = admin_db.get_skill_by_name(payload.name)
            if existing and existing.id != skill_id:
                return {"ok": False, "error": f"Another skill with name '{payload.name}' already exists"}

        if payload.description is not None:
            errors.extend(_validate_description(payload.description))

        if errors:
            return {"ok": False, "error": "; ".join(errors)}
    except ImportError:
        # If validators not available, just check basic rules
        if payload.name is not None and len(payload.name) > 64:
            return {"ok": False, "error": "Invalid skill name"}

    if payload.files is not None:
        err = _validate_skill_files(payload.files)
        if err:
            return {"ok": False, "error": err}

    try:
        updated = admin_db.update_skill(
            skill_id=skill_id,
            name=payload.name,
            description=payload.description,
            instructions=payload.instructions,
            department=payload.department,
            license=payload.license,
            compatibility=payload.compatibility,
            metadata=payload.metadata,
            allowed_tools=payload.allowed_tools,
            expected_version=payload.version,
        )

        if payload.files is not None:
            admin_db.replace_skill_files(
                skill_id,
                [{"path": f.path, "content": f.content} for f in payload.files],
            )

        # Trigger hot-reload
        _reload_agent_skills()

        return {
            "ok": True,
            "data": {"id": updated.id, "name": updated.name, "version": updated.version}
        }
    except ValueError as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/skills/{skill_id}")
async def delete_skill(
    skill_id: str,
    hard: bool = Query(False),
    admin: str = Depends(get_current_admin)
):
    """Delete a skill. By default soft-deletes (archives). Use ?hard=true for permanent deletion."""
    skill = admin_db.get_skill(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    try:
        admin_db.delete_skill(skill_id, soft=not hard)

        # Trigger hot-reload
        _reload_agent_skills()

        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
