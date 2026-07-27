"""
REST API for skills management — authenticated via Bearer token (API_SECRET_KEY).
Prefix: /skills  —  mounted in src/app.py
"""
import json as json_module
import re
import sqlite3
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from src.admin import db as admin_db
from src.middleware.api_key import require_bearer_token

router = APIRouter(tags=["Skills"], dependencies=[Depends(require_bearer_token)])

_VALID_FILE_PREFIX = re.compile(r"^(scripts|references)/[a-zA-Z0-9_\-\.]+$")


class SkillFileInput(BaseModel):
    path: str
    content: str


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
    is_active: Optional[bool] = None
    files: Optional[List[SkillFileInput]] = None


def _validate_files(files: List[SkillFileInput]) -> Optional[str]:
    for f in files:
        if not _VALID_FILE_PREFIX.match(f.path):
            return f"Invalid path '{f.path}'. Must be scripts/<name> or references/<name>."
    return None


def _reload_skills():
    try:
        from src.app import agents
        reloaded = 0
        for agent in agents:
            if hasattr(agent, "skills") and agent.skills:
                try:
                    agent.skills.reload()
                    reloaded += 1
                except Exception as e:
                    print(f"[Skills] ERROR reloading agent '{getattr(agent, 'name', '?')}': {e}")
        print(f"[Skills] Reloaded {reloaded}/{len(agents)} agents.")
    except Exception as e:
        print(f"[Skills] ERROR in _reload_skills: {e}")


@router.get("/")
async def list_skills(department: Optional[str] = Query(None)):
    """List all active skills, optionally filtered by department."""
    skills = admin_db.get_all_skills(department=department, include_global=True)
    return {
        "ok": True,
        "data": [
            {
                "id": s.id,
                "name": s.name,
                "description": s.description,
                "department": s.department,
                "is_active": bool(s.is_active),
                "version": s.version,
                "created_at": s.created_at,
                "updated_at": s.updated_at,
            }
            for s in skills
        ],
    }


@router.get("/{skill_id}")
async def get_skill(skill_id: str):
    """Get full skill details including files."""
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
        },
    }


@router.post("/")
async def create_skill(payload: SkillCreateRequest):
    """Create a new skill."""
    try:
        from agno.skills.validator import _validate_name, _validate_description
        errors = []
        errors.extend(_validate_name(payload.name))
        errors.extend(_validate_description(payload.description))
        if errors:
            return {"ok": False, "error": "; ".join(errors)}
    except ImportError:
        if not payload.name or len(payload.name) > 64:
            return {"ok": False, "error": "Invalid skill name"}

    existing = admin_db.get_skill_by_name(payload.name)
    if existing:
        return {"ok": False, "error": f"Skill '{payload.name}' already exists"}

    if payload.files:
        err = _validate_files(payload.files)
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
            created_by="api",
        )

        if payload.files:
            admin_db.replace_skill_files(
                skill.id,
                [{"path": f.path, "content": f.content} for f in payload.files],
            )

        _reload_skills()

        return {"ok": True, "data": {"id": skill.id, "name": skill.name, "version": skill.version}}
    except sqlite3.IntegrityError as e:
        return {"ok": False, "error": f"Database constraint: {e}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{skill_id}")
async def update_skill(skill_id: str, payload: SkillUpdateRequest):
    """Update an existing skill."""
    skill = admin_db.get_skill(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    # Handle is_active toggle separately (soft-delete / re-activate)
    if payload.is_active is not None:
        try:
            import sqlite3 as _sqlite3
            from src.admin.db import DB_PATH
            with _sqlite3.connect(DB_PATH) as conn:
                conn.execute(
                    "UPDATE skills SET is_active = ?, updated_at = ? WHERE id = ?",
                    (1 if payload.is_active else 0, _now(), skill_id),
                )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    # Validate name/description if being updated
    if payload.name is not None or payload.description is not None:
        try:
            from agno.skills.validator import _validate_name, _validate_description
            errors = []
            if payload.name is not None:
                errors.extend(_validate_name(payload.name))
                existing = admin_db.get_skill_by_name(payload.name)
                if existing and existing.id != skill_id:
                    return {"ok": False, "error": f"Skill '{payload.name}' already exists"}
            if payload.description is not None:
                errors.extend(_validate_description(payload.description))
            if errors:
                return {"ok": False, "error": "; ".join(errors)}
        except ImportError:
            pass

    if payload.files is not None:
        err = _validate_files(payload.files)
        if err:
            return {"ok": False, "error": err}

    try:
        # Only call update_skill if there are fields beyond is_active to update
        fields = {k: v for k, v in payload.model_dump(exclude_none=True).items() if k != "is_active"}
        if fields:
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
        else:
            updated = admin_db.get_skill(skill_id)

        if payload.files is not None:
            admin_db.replace_skill_files(
                skill_id,
                [{"path": f.path, "content": f.content} for f in payload.files],
            )

        _reload_skills()

        return {"ok": True, "data": {"id": updated.id, "name": updated.name, "version": updated.version}}
    except ValueError as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{skill_id}")
async def delete_skill(skill_id: str, hard: bool = Query(False)):
    """Delete a skill. Default: soft-delete. ?hard=true for permanent."""
    skill = admin_db.get_skill(skill_id)
    if not skill:
        raise HTTPException(status_code=404, detail="Skill not found")

    try:
        admin_db.delete_skill(skill_id, soft=not hard)
        _reload_skills()
        return {"ok": True}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()
