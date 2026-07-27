"""
CRUD SQLite para as tabelas knowledge_documents e departments.
"""
import json
import os
import sqlite3
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

DB_PATH = Path(os.getenv("SQLITE_DB_PATH", "agno.db"))


@dataclass
class KnowledgeDocument:
    id: str
    department: str
    filename: str
    file_path: str
    file_size: Optional[int] = None
    file_type: Optional[str] = None
    status: str = "pending"
    error_msg: Optional[str] = None
    chunk_count: Optional[int] = None
    chroma_ids: Optional[str] = None  # JSON array string
    uploaded_at: Optional[str] = None
    indexed_at: Optional[str] = None

    def chroma_ids_list(self) -> List[str]:
        if self.chroma_ids:
            return json.loads(self.chroma_ids)
        return []


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def create_document(
    department: str,
    filename: str,
    file_path: str,
    file_size: int,
    file_type: str,
) -> KnowledgeDocument:
    doc_id = str(uuid.uuid4())
    with _conn() as conn:
        conn.execute(
            """INSERT INTO knowledge_documents
               (id, department, filename, file_path, file_size, file_type, status)
               VALUES (?, ?, ?, ?, ?, ?, 'pending')""",
            (doc_id, department, filename, file_path, file_size, file_type),
        )
    return get_document(doc_id)


def get_document(doc_id: str) -> Optional[KnowledgeDocument]:
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM knowledge_documents WHERE id = ?", (doc_id,)
        ).fetchone()
    if not row:
        return None
    return KnowledgeDocument(**dict(row))


def get_documents_by_department(department: str) -> List[KnowledgeDocument]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM knowledge_documents WHERE department = ? ORDER BY uploaded_at DESC",
            (department,),
        ).fetchall()
    return [KnowledgeDocument(**dict(r)) for r in rows]


def get_document_by_filename(department: str, filename: str) -> Optional[KnowledgeDocument]:
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM knowledge_documents WHERE department = ? AND filename = ?",
            (department, filename),
        ).fetchone()
    if not row:
        return None
    return KnowledgeDocument(**dict(row))


def count_by_department() -> dict:
    """Retorna contagens por departamento para o dashboard."""
    with _conn() as conn:
        rows = conn.execute(
            """SELECT department,
                      COUNT(*) as total,
                      SUM(CASE WHEN status='indexed' THEN 1 ELSE 0 END) as indexed,
                      SUM(CASE WHEN status='processing' THEN 1 ELSE 0 END) as processing,
                      SUM(CASE WHEN status='error' THEN 1 ELSE 0 END) as error,
                      SUM(CASE WHEN status='pending' THEN 1 ELSE 0 END) as pending
               FROM knowledge_documents
               GROUP BY department"""
        ).fetchall()
    return {r["department"]: dict(r) for r in rows}


def update_status(
    doc_id: str,
    status: str,
    error_msg: str = None,
    chunk_count: int = None,
    chroma_ids: List[str] = None,
) -> None:
    now = datetime.now(timezone.utc).isoformat()
    with _conn() as conn:
        conn.execute(
            """UPDATE knowledge_documents
               SET status = ?,
                   error_msg = ?,
                   chunk_count = ?,
                   chroma_ids = ?,
                   indexed_at = CASE WHEN ? = 'indexed' THEN ? ELSE indexed_at END
               WHERE id = ?""",
            (
                status,
                error_msg,
                chunk_count,
                json.dumps(chroma_ids) if chroma_ids is not None else None,
                status,
                now,
                doc_id,
            ),
        )


def delete_document(doc_id: str) -> None:
    with _conn() as conn:
        conn.execute("DELETE FROM knowledge_documents WHERE id = ?", (doc_id,))


# ---------------------------------------------------------------------------
# Departments
# ---------------------------------------------------------------------------

@dataclass
class Department:
    slug: str
    display_name: str
    is_system: int  # 1 = não pode ser deletado/renomeado
    created_at: str


def ensure_knowledge_documents_table() -> None:
    with _conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_documents (
                id          TEXT PRIMARY KEY,
                department  TEXT NOT NULL,
                filename    TEXT NOT NULL,
                file_path   TEXT NOT NULL,
                file_size   INTEGER,
                file_type   TEXT,
                status      TEXT DEFAULT 'pending',
                error_msg   TEXT,
                chunk_count INTEGER,
                chroma_ids  TEXT,
                uploaded_at TEXT DEFAULT (datetime('now')),
                indexed_at  TEXT
            )
        """)


def ensure_departments_table() -> None:
    with _conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS departments (
                slug         TEXT PRIMARY KEY,
                display_name TEXT UNIQUE NOT NULL,
                is_system    INTEGER DEFAULT 0,
                created_at   TEXT DEFAULT (datetime('now'))
            )
        """)


def seed_departments(mapping: dict) -> None:
    """Popula a tabela departments a partir do DEPARTMENT_MAPPING se estiver vazia."""
    with _conn() as conn:
        count = conn.execute("SELECT COUNT(*) FROM departments").fetchone()[0]
        if count == 0:
            for slug, display_name in mapping.items():
                if display_name is not None:  # Ignora 'geral' (sem filtro)
                    conn.execute(
                        "INSERT OR IGNORE INTO departments (slug, display_name) VALUES (?, ?)",
                        (slug, display_name),
                    )


def get_all_departments() -> List[Department]:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT slug, display_name, is_system, created_at FROM departments ORDER BY display_name"
        ).fetchall()
    return [Department(slug=r[0], display_name=r[1], is_system=r[2], created_at=r[3]) for r in rows]


def get_department_by_slug(slug: str) -> Optional[Department]:
    with _conn() as conn:
        row = conn.execute(
            "SELECT slug, display_name, is_system, created_at FROM departments WHERE slug = ?",
            (slug,),
        ).fetchone()
    if not row:
        return None
    return Department(slug=row[0], display_name=row[1], is_system=row[2], created_at=row[3])


def get_department_by_display_name(display_name: str) -> Optional[Department]:
    with _conn() as conn:
        row = conn.execute(
            "SELECT slug, display_name, is_system, created_at FROM departments WHERE display_name = ?",
            (display_name,),
        ).fetchone()
    if not row:
        return None
    return Department(slug=row[0], display_name=row[1], is_system=row[2], created_at=row[3])


def create_department(slug: str, display_name: str) -> Department:
    with _conn() as conn:
        conn.execute(
            "INSERT INTO departments (slug, display_name) VALUES (?, ?)",
            (slug, display_name),
        )
    return get_department_by_slug(slug)


def rename_department(slug: str, new_display_name: str) -> str:
    """Renomeia um departamento e atualiza os registros de documentos.
    Retorna o display_name antigo para que o caller possa atualizar o ChromaDB."""
    dept = get_department_by_slug(slug)
    if not dept:
        raise ValueError(f"Department '{slug}' not found")
    old_display_name = dept.display_name
    with _conn() as conn:
        conn.execute(
            "UPDATE departments SET display_name = ? WHERE slug = ?",
            (new_display_name, slug),
        )
        conn.execute(
            "UPDATE knowledge_documents SET department = ? WHERE department = ?",
            (new_display_name, old_display_name),
        )
    return old_display_name


def delete_department_record(slug: str) -> None:
    with _conn() as conn:
        conn.execute("DELETE FROM departments WHERE slug = ?", (slug,))


# ---------------------------------------------------------------------------
# Skills (Database-backed)
# ---------------------------------------------------------------------------

@dataclass
class SkillRecord:
    """Database representation of a skill."""
    id: str
    name: str
    description: str
    instructions: str
    department: Optional[str]
    license: Optional[str]
    compatibility: Optional[str]
    metadata: Optional[str]
    allowed_tools: Optional[str]
    created_by: str
    created_at: str
    updated_at: str
    version: int
    is_active: int

    def to_skill_dict(self) -> dict:
        """Convert to format compatible with Agno's Skill.from_dict().
        Scripts/references lists are populated by DatabaseSkillLoader after materializing files."""
        return {
            "name": self.name,
            "description": self.description,
            "instructions": self.instructions,
            "source_path": f"db://{self.id}",  # Replaced by real path in db_loader
            "license": self.license,
            "compatibility": self.compatibility,
            "metadata": json.loads(self.metadata) if self.metadata else None,
            "allowed_tools": json.loads(self.allowed_tools) if self.allowed_tools else None,
            "scripts": [],     # Populated by DatabaseSkillLoader
            "references": [],  # Populated by DatabaseSkillLoader
        }


@dataclass
class SkillFile:
    """A script or reference file attached to a skill."""
    id: str
    skill_id: str
    path: str      # Relative path, e.g. "scripts/analyze.py" or "references/guide.md"
    content: str
    created_at: str
    updated_at: str


def ensure_skills_table() -> None:
    """Create skills and skill_files tables if not exists."""
    with _conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS skills (
                id              TEXT PRIMARY KEY,
                name            TEXT UNIQUE NOT NULL,
                description     TEXT NOT NULL,
                instructions    TEXT NOT NULL,
                department      TEXT,
                license         TEXT,
                compatibility   TEXT,
                metadata        TEXT,
                allowed_tools   TEXT,
                created_by      TEXT NOT NULL,
                created_at      TEXT NOT NULL,
                updated_at      TEXT NOT NULL,
                version         INTEGER DEFAULT 1,
                is_active       INTEGER DEFAULT 1,
                CONSTRAINT valid_name CHECK (
                    length(name) <= 64 AND
                    name = lower(name) AND
                    name NOT LIKE '-%' AND
                    name NOT LIKE '%-' AND
                    name NOT LIKE '%---%'
                )
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_skills_department ON skills(department)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_skills_active ON skills(is_active)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_skills_created_at ON skills(created_at DESC)")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS skill_files (
                id          TEXT PRIMARY KEY,
                skill_id    TEXT NOT NULL REFERENCES skills(id) ON DELETE CASCADE,
                path        TEXT NOT NULL,
                content     TEXT NOT NULL,
                created_at  TEXT NOT NULL,
                updated_at  TEXT NOT NULL,
                UNIQUE(skill_id, path)
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_skill_files_skill_id ON skill_files(skill_id)")
        conn.execute("PRAGMA foreign_keys = ON")


def create_skill(
    name: str,
    description: str,
    instructions: str,
    department: Optional[str],
    created_by: str,
    license: Optional[str] = None,
    compatibility: Optional[str] = None,
    metadata: Optional[dict] = None,
    allowed_tools: Optional[List[str]] = None,
) -> SkillRecord:
    """Create a new skill. Raises sqlite3.IntegrityError if name exists."""
    skill_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()

    with _conn() as conn:
        conn.execute(
            """INSERT INTO skills
               (id, name, description, instructions, department, license, compatibility,
                metadata, allowed_tools, created_by, created_at, updated_at, version, is_active)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 1)""",
            (
                skill_id,
                name,
                description,
                instructions,
                department,
                license,
                compatibility,
                json.dumps(metadata) if metadata else None,
                json.dumps(allowed_tools) if allowed_tools else None,
                created_by,
                now,
                now,
            ),
        )
    return get_skill(skill_id)


def get_skill(skill_id: str) -> Optional[SkillRecord]:
    """Get skill by ID."""
    with _conn() as conn:
        row = conn.execute("SELECT * FROM skills WHERE id = ?", (skill_id,)).fetchone()
    return SkillRecord(**dict(row)) if row else None


def get_skill_by_name(name: str) -> Optional[SkillRecord]:
    """Get active skill by name."""
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM skills WHERE name = ? AND is_active = 1",
            (name,),
        ).fetchone()
    return SkillRecord(**dict(row)) if row else None


def get_all_skills(department: Optional[str] = None, include_global: bool = True) -> List[SkillRecord]:
    """Get all active skills, optionally filtered by department."""
    with _conn() as conn:
        if department is None:
            # No filter: return all active skills
            rows = conn.execute(
                "SELECT * FROM skills WHERE is_active = 1 ORDER BY name"
            ).fetchall()
        elif include_global:
            # Department-specific + global (NULL department)
            rows = conn.execute(
                """SELECT * FROM skills
                   WHERE is_active = 1 AND (department = ? OR department IS NULL)
                   ORDER BY name""",
                (department,),
            ).fetchall()
        else:
            # Department-specific only
            rows = conn.execute(
                "SELECT * FROM skills WHERE is_active = 1 AND department = ? ORDER BY name",
                (department,),
            ).fetchall()
    return [SkillRecord(**dict(r)) for r in rows]


def update_skill(
    skill_id: str,
    name: Optional[str] = None,
    description: Optional[str] = None,
    instructions: Optional[str] = None,
    department: Optional[str] = None,
    license: Optional[str] = None,
    compatibility: Optional[str] = None,
    metadata: Optional[dict] = None,
    allowed_tools: Optional[List[str]] = None,
    expected_version: Optional[int] = None,
) -> SkillRecord:
    """Update skill fields. Uses optimistic locking if expected_version provided.
    Raises ValueError if skill not found or version mismatch."""
    skill = get_skill(skill_id)
    if not skill:
        raise ValueError(f"Skill {skill_id} not found")

    if expected_version is not None and skill.version != expected_version:
        raise ValueError(f"Version conflict: expected {expected_version}, current {skill.version}")

    now = datetime.now(timezone.utc).isoformat()

    # Build dynamic update
    updates = []
    params = []

    if name is not None:
        updates.append("name = ?")
        params.append(name)
    if description is not None:
        updates.append("description = ?")
        params.append(description)
    if instructions is not None:
        updates.append("instructions = ?")
        params.append(instructions)
    if department is not None:
        updates.append("department = ?")
        params.append(department)
    if license is not None:
        updates.append("license = ?")
        params.append(license)
    if compatibility is not None:
        updates.append("compatibility = ?")
        params.append(compatibility)
    if metadata is not None:
        updates.append("metadata = ?")
        params.append(json.dumps(metadata))
    if allowed_tools is not None:
        updates.append("allowed_tools = ?")
        params.append(json.dumps(allowed_tools))

    if not updates:
        return skill  # No changes

    updates.append("updated_at = ?")
    params.append(now)
    updates.append("version = version + 1")

    params.append(skill_id)

    with _conn() as conn:
        conn.execute(
            f"UPDATE skills SET {', '.join(updates)} WHERE id = ?",
            params,
        )

    return get_skill(skill_id)


def delete_skill(skill_id: str, soft: bool = True) -> None:
    """Delete skill. If soft=True, marks as inactive. If soft=False, hard delete."""
    with _conn() as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        if soft:
            conn.execute("UPDATE skills SET is_active = 0 WHERE id = ?", (skill_id,))
        else:
            # ON DELETE CASCADE removes skill_files automatically
            conn.execute("DELETE FROM skills WHERE id = ?", (skill_id,))


# ---------------------------------------------------------------------------
# Skill Files (scripts and references)
# ---------------------------------------------------------------------------

def upsert_skill_file(skill_id: str, path: str, content: str) -> SkillFile:
    """Create or replace a skill file (script or reference)."""
    file_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    with _conn() as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        existing = conn.execute(
            "SELECT id FROM skill_files WHERE skill_id = ? AND path = ?",
            (skill_id, path),
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE skill_files SET content = ?, updated_at = ? WHERE skill_id = ? AND path = ?",
                (content, now, skill_id, path),
            )
            file_id = existing["id"]
        else:
            conn.execute(
                "INSERT INTO skill_files (id, skill_id, path, content, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (file_id, skill_id, path, content, now, now),
            )
    return get_skill_file(skill_id, path)


def get_skill_file(skill_id: str, path: str) -> Optional[SkillFile]:
    """Get a specific skill file by skill_id + path."""
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM skill_files WHERE skill_id = ? AND path = ?",
            (skill_id, path),
        ).fetchone()
    if not row:
        return None
    return SkillFile(**dict(row))


def get_skill_files(skill_id: str) -> List[SkillFile]:
    """Get all files for a skill, ordered by path."""
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM skill_files WHERE skill_id = ? ORDER BY path",
            (skill_id,),
        ).fetchall()
    return [SkillFile(**dict(r)) for r in rows]


def delete_skill_file(skill_id: str, path: str) -> None:
    """Delete a specific skill file."""
    with _conn() as conn:
        conn.execute(
            "DELETE FROM skill_files WHERE skill_id = ? AND path = ?",
            (skill_id, path),
        )


def replace_skill_files(skill_id: str, files: List[dict]) -> None:
    """Replace all files for a skill atomically.

    Args:
        skill_id: The skill UUID.
        files: List of {"path": "scripts/foo.py", "content": "..."} dicts.
    """
    now = datetime.now(timezone.utc).isoformat()
    with _conn() as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("DELETE FROM skill_files WHERE skill_id = ?", (skill_id,))
        for f in files:
            conn.execute(
                "INSERT INTO skill_files (id, skill_id, path, content, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)",
                (str(uuid.uuid4()), skill_id, f["path"], f["content"], now, now),
            )
