"""
Database-backed skill loader for Agno agents.

Loads skills stored in SQLite and materializes their files (scripts/, references/)
to a local cache directory so Agno's get_skill_script/get_skill_reference tools
can read them from the filesystem as expected.
"""
import os
import shutil
from pathlib import Path
from typing import List, Optional

from agno.skills.loaders.base import SkillLoader
from agno.skills.skill import Skill

from src.admin import db as admin_db

# Where DB skill files are materialized on disk
_CACHE_DIR = Path(os.getenv("DB_SKILLS_CACHE_DIR", ".db_skills_cache"))


class DatabaseSkillLoader(SkillLoader):
    """Loads skills from the database.

    Scripts and references are stored as text in the DB and materialized
    to _CACHE_DIR/<skill_name>/ so Agno's filesystem-based tools work correctly.

    Args:
        department: If specified, loads department skills + global (NULL) skills.
                   If None, loads all skills (admin view).
        validate: Whether to validate skill format (default: True).
    """

    def __init__(self, department: Optional[str] = None, validate: bool = True):
        self.department = department
        self.validate = validate

    def load(self) -> List[Skill]:
        """Load skills from database, materializing files to disk cache."""
        if self.department:
            skill_records = admin_db.get_all_skills(
                department=self.department,
                include_global=True,
            )
        else:
            skill_records = admin_db.get_all_skills(department=None)

        skills: List[Skill] = []
        for record in skill_records:
            try:
                skill_dict = record.to_skill_dict()

                if self.validate:
                    self._validate_skill_data(skill_dict)

                # Materialize files and get real source_path + file lists
                source_path, scripts, references = self._materialize(record)
                skill_dict["source_path"] = str(source_path)
                skill_dict["scripts"] = scripts
                skill_dict["references"] = references

                skill = Skill.from_dict(skill_dict)
                skills.append(skill)

            except Exception as e:
                print(f"[Warning] Error loading skill '{record.name}' from DB: {e}")
                continue

        return skills

    def _materialize(self, record: "admin_db.SkillRecord"):
        """Write skill files from DB to a local cache directory.

        Returns:
            (source_path, scripts_list, references_list)
        """
        skill_dir = _CACHE_DIR / record.name
        skill_dir.mkdir(parents=True, exist_ok=True)

        # Write SKILL.md (instructions)
        skill_md = skill_dir / "SKILL.md"
        skill_md.write_text(record.instructions, encoding="utf-8")

        # Get all attached files (scripts + references)
        files = admin_db.get_skill_files(record.id)

        scripts: List[str] = []
        references: List[str] = []

        # Clear old scripts/ and references/ dirs to avoid stale files
        scripts_dir = skill_dir / "scripts"
        refs_dir = skill_dir / "references"
        if scripts_dir.exists():
            shutil.rmtree(scripts_dir)
        if refs_dir.exists():
            shutil.rmtree(refs_dir)

        for f in files:
            file_path = skill_dir / f.path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(f.content, encoding="utf-8")

            # Categorize by prefix
            if f.path.startswith("scripts/"):
                scripts.append(Path(f.path).name)
            elif f.path.startswith("references/"):
                references.append(Path(f.path).name)

        return skill_dir, sorted(scripts), sorted(references)

    def _validate_skill_data(self, skill_dict: dict) -> None:
        """Validate skill data against Agno's rules.

        Raises:
            ValueError: If validation fails.
        """
        try:
            from agno.skills.validator import (
                _validate_name,
                _validate_description,
                _validate_compatibility,
                _validate_license,
                _validate_allowed_tools,
            )
        except ImportError:
            return

        errors = []
        errors.extend(_validate_name(skill_dict.get("name", "")))
        errors.extend(_validate_description(skill_dict.get("description", "")))

        if skill_dict.get("compatibility"):
            errors.extend(_validate_compatibility(skill_dict["compatibility"]))
        if skill_dict.get("license"):
            errors.extend(_validate_license(skill_dict["license"]))
        if skill_dict.get("allowed_tools"):
            errors.extend(_validate_allowed_tools(skill_dict["allowed_tools"]))

        if errors:
            raise ValueError(f"Skill validation failed: {'; '.join(errors)}")
