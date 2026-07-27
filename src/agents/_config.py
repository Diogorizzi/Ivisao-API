"""
Carrega e valida configurações de agentes e empresa.
"""
from __future__ import annotations
from pathlib import Path
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, validator
import yaml


class AgentFeatures(BaseModel):
    """Features do Agno habilitadas para o agente"""
    memory: bool = True
    rag: bool = True
    web_search: bool = False
    add_datetime: bool = True
    add_history: bool = True
    num_history_runs: int = 10
    num_documents: int = 5  # Número de documentos retornados pelo RAG
    markdown: bool = True
    debug_mode: bool = False


class ToolConfig(BaseModel):
    """Configuração de uma tool"""
    name: str
    kwargs: Dict[str, Any] = Field(default_factory=dict)


class MCPConfig(BaseModel):
    """Configuração de uma ferramenta baseada no Model Context Protocol"""
    url: str
    transport: str = "streamable-http"


class AgentConfig(BaseModel):
    """Configuração completa de um agente"""
    name: str
    department: Optional[str] = None  # None = Super Admin (acessa tudo)
    description: str = ""
    model: Optional[str] = None  # None = usa default
    features: AgentFeatures
    tools: List[ToolConfig] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    mcps: List[MCPConfig] = Field(default_factory=list)
    instructions: List[str] = Field(default_factory=list)

    @validator('skills')
    def validate_skills_exist(cls, skills):
        """Valida se as skills referenciadas existem"""
        skills_dir = Path("src/skills")
        for skill_path in skills:
            full_path = skills_dir / skill_path / "SKILL.md"
            if not full_path.exists():
                raise ValueError(
                    f"Skill não encontrada: {skill_path}\n"
                    f"Esperado em: {full_path}\n"
                    f"Dica: Rode 'python scripts/generate_skills_catalog.py' "
                    f"para ver skills disponíveis"
                )
        return skills


class SystemConfig(BaseModel):
    """Configuração completa do sistema"""
    company: CompanyConfig
    agents: List[AgentConfig]


class CompanyConfig(BaseModel):
    """Configuração da empresa"""
    company_name: str
    company_description: str
    default_model: str = "gpt-4o-mini"
    default_temperature: float = 0.7
    company_values: List[str] = Field(default_factory=list)
    company_tone: str = "profissional e amigável"


def load_company_config() -> CompanyConfig:
    """Carrega config/company.yaml"""
    config_path = Path("config/company.yaml")
    if not config_path.exists():
        raise FileNotFoundError("config/company.yaml não encontrado")

    with open(config_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    return CompanyConfig(**data)


def load_agents_config() -> List[AgentConfig]:
    """Carrega config/agents.yaml"""
    config_path = Path("config/agents.yaml")
    if not config_path.exists():
        raise FileNotFoundError("config/agents.yaml não encontrado")

    with open(config_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)

    # Merge globals com cada agente
    globals_config = data.get("globals", {})
    default_features = globals_config.get("default_features", {})

    agents = []
    for agent_data in data.get("agents", []):
        # Merge features (agent override > defaults)
        if "features" not in agent_data:
            agent_data["features"] = default_features
        else:
            merged_features = {**default_features, **agent_data["features"]}
            agent_data["features"] = merged_features

        # Model default
        if "model" not in agent_data or agent_data["model"] is None:
            agent_data["model"] = globals_config.get("default_model")

        agents.append(AgentConfig(**agent_data))

    return agents


def interpolate_template(text: str, variables: Dict[str, str]) -> str:
    """Substitui variáveis {{var}} no template"""
    for key, value in variables.items():
        text = text.replace(f"{{{{{key}}}}}", str(value))
    return text


def load_system_config() -> SystemConfig:
    """Carrega configuração completa do sistema"""
    company = load_company_config()
    agents = load_agents_config()

    # Interpola variáveis nos prompts
    template_vars = {
        "company_name": company.company_name,
        "company_description": company.company_description,
        "COMPANY_NAME": company.company_name,
        "COMPANY_DESCRIPTION": company.company_description,
    }

    for agent in agents:
        agent.instructions = [
            interpolate_template(instr, template_vars)
            for instr in agent.instructions
        ]

    return SystemConfig(company=company, agents=agents)
