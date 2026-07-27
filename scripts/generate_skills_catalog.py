"""
Gera documentação automática de todas as skills disponíveis.
Output: docs/skills-catalog.md
"""
from pathlib import Path
import yaml


def scan_skills():
    """Escaneia src/skills/ e extrai metadata"""
    skills_dir = Path("src/skills")
    catalog = {"shared": [], "departamentos": {}}

    for category_dir in skills_dir.iterdir():
        if not category_dir.is_dir() or category_dir.name.startswith("_"):
            continue

        category = category_dir.name
        skills_list = []

        for skill_dir in category_dir.iterdir():
            if not skill_dir.is_dir():
                continue

            skill_md = skill_dir / "SKILL.md"
            if not skill_md.exists():
                continue

            # Parse frontmatter
            content = skill_md.read_text(encoding='utf-8')
            if content.startswith('---'):
                parts = content.split('---', 2)
                frontmatter = yaml.safe_load(parts[1])

                skills_list.append({
                    "name": frontmatter.get("name", skill_dir.name),
                    "description": frontmatter.get("description", ""),
                    "path": f"{category}/{skill_dir.name}",
                })

        if category == "shared":
            catalog["shared"] = skills_list
        else:
            catalog["departamentos"][category] = skills_list

    return catalog


def generate_markdown(catalog):
    """Gera arquivo markdown do catálogo"""
    md = ["# 📚 Catálogo de Skills Disponíveis\n"]
    md.append("*Auto-gerado - não edite manualmente*\n")

    # Skills compartilhadas
    md.append("## 🌐 Skills Compartilhadas (Shared)\n")
    md.append("Disponíveis para todos os agentes:\n")
    for skill in catalog["shared"]:
        md.append(f"### `{skill['path']}`")
        md.append(f"{skill['description']}\n")

    # Skills por departamento
    md.append("## 🏢 Skills por Departamento\n")
    for dept, skills in sorted(catalog["departamentos"].items()):
        md.append(f"### {dept.upper()}\n")
        for skill in skills:
            md.append(f"- **`{skill['path']}`**: {skill['description']}")
        md.append("")

    return "\n".join(md)


if __name__ == "__main__":
    catalog = scan_skills()
    markdown = generate_markdown(catalog)

    output_path = Path("docs/skills-catalog.md")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding='utf-8')

    print(f"[OK] Catalogo gerado: {output_path}")
    print(f"   - {len(catalog['shared'])} skills compartilhadas")
    print(f"   - {len(catalog['departamentos'])} departamentos")
