"""
Factory para criar agentes dinamicamente baseado em configuração YAML.
"""
from typing import List
from pathlib import Path
from agno.agent import Agent
from agno.skills import Skills, LocalSkills

from src.agents._config import load_system_config, AgentConfig
from src.agents._base import create_base_agent
from src.config.llm_providers import get_model
from src.knowledge.base import get_knowledge_base
from src.tools.dynamic_loader import load_dynamic_tools
from src.skills.db_loader import DatabaseSkillLoader


def create_agent_from_config(agent_config: AgentConfig) -> Agent:
    """
    Cria um agente Agno baseado na configuração YAML.

    Args:
        agent_config: Configuração validada do agente

    Returns:
        Agent instanciado e pronto para uso
    """
    # Resolve modelo (usa config do agente ou default)
    model = get_model(agent_config.model)

    # Carrega tools dinamicamente
    tools = load_dynamic_tools([t.model_dump() for t in agent_config.tools])

    # Configura e anexa MCP tools se existirem na configuração
    if agent_config.mcps:
        from agno.tools.mcp import MCPTools
        for mcp_cfg in agent_config.mcps:
            try:
                mcp_tool = MCPTools(
                    transport=mcp_cfg.transport,
                    url=mcp_cfg.url
                )
                tools.append(mcp_tool)
            except Exception as e:
                print(f"[ERROR] Falha ao configurar MCP {mcp_cfg.url}: {e}")

    # Configura skills - carrega filesystem + database
    skills = None
    loaders = []

    # Add filesystem loaders
    if agent_config.skills:
        skills_paths = [Path("src/skills") / sp for sp in agent_config.skills]
        loaders.extend([LocalSkills(str(p)) for p in skills_paths if p.exists()])
    elif not agent_config.skills:
        skills_dir = Path("src/skills")
        loaders.append(LocalSkills(str(skills_dir)))

    # ALWAYS add database loader (department-scoped)
    loaders.append(DatabaseSkillLoader(department=agent_config.department))

    if loaders:
        skills = Skills(loaders=loaders)

    # Configura knowledge base com filtro de departamento
    knowledge = None
    if agent_config.features.rag:
        knowledge = get_knowledge_base(
            department=agent_config.department,  # None = sem filtro (Super Admin)
            num_documents=agent_config.features.num_documents,
        )

    # Cria o agente usando a base existente
    agent = create_base_agent(
        name=agent_config.name,
        user_id="system",  # Pode ser sobrescrito depois
        instructions=list(agent_config.instructions or []),
        tools=tools,
        skills=skills,
        knowledge=knowledge,
        model=model,
        markdown=agent_config.features.markdown,
        debug_mode=agent_config.features.debug_mode,
        # Features do Agno
        enable_agentic_memory=agent_config.features.memory,
        add_datetime_to_context=agent_config.features.add_datetime,
        add_history_to_context=agent_config.features.add_history,
        num_history_runs=agent_config.features.num_history_runs,
    )

    return agent


def load_all_agents() -> List[Agent]:
    """
    Carrega todos os agentes definidos em config/agents.yaml

    Returns:
        Lista de agentes instanciados
    """
    system_config = load_system_config()

    agents = []
    for agent_config in system_config.agents:
        try:
            agent = create_agent_from_config(agent_config)
            agents.append(agent)
            print(f"[OK] Agente carregado: {agent_config.name} (dept: {agent_config.department or 'admin'})")
        except Exception as e:
            print(f"[ERROR] Erro ao carregar agente {agent_config.name}: {e}")
            raise

    print(f"\nTotal de {len(agents)} agentes carregados com sucesso!")
    return agents
