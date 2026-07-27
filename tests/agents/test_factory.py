import pytest
from unittest.mock import Mock, patch
from src.agents._factory import create_agent_from_config
from src.agents._config import AgentConfig, AgentFeatures, ToolConfig


def test_create_agent_from_config():
    """Test creating agent from config"""
    config = AgentConfig(
        name="Test Agent",
        department="test",
        model="openai:gpt-4o-mini",
        features=AgentFeatures(rag=False),
        tools=[
            ToolConfig(name="DuckDuckGoTools")
        ],
        skills=[],
        instructions=["Test instruction"]
    )

    with patch('src.agents._factory.get_model') as mock_model, \
         patch('src.agents._factory.load_dynamic_tools') as mock_tools, \
         patch('src.agents._factory.create_base_agent') as mock_create:

        mock_model.return_value = Mock()
        mock_tools.return_value = []
        mock_create.return_value = Mock()

        agent = create_agent_from_config(config)

        assert agent is not None
        mock_model.assert_called_once_with("openai:gpt-4o-mini")
        mock_create.assert_called_once()


def test_load_all_agents(tmp_path, monkeypatch):
    """Test loading all agents from YAML"""
    from src.agents._factory import load_all_agents

    monkeypatch.chdir(tmp_path)
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    # Create company.yaml
    company_yaml = """
company_name: "Test Co"
company_description: "Test company"
"""
    (config_dir / "company.yaml").write_text(company_yaml)

    # Create agents.yaml
    agents_yaml = """
globals:
  default_model: "gpt-4o-mini"
  default_features:
    memory: true
    rag: false

agents:
  - name: "Test Agent 1"
    department: "test1"
    features: {}
    instructions:
      - "Test 1"

  - name: "Test Agent 2"
    department: "test2"
    features: {}
    instructions:
      - "Test 2"
"""
    (config_dir / "agents.yaml").write_text(agents_yaml)

    with patch('src.agents._factory.create_agent_from_config') as mock_create:
        mock_create.return_value = Mock()

        agents = load_all_agents()

        assert len(agents) == 2
        assert mock_create.call_count == 2


def test_rag_agents_have_search_knowledge_instruction(tmp_path, monkeypatch):
    """
    Agentes com rag: true devem ter a instrução guia que orienta
    o LLM a usar search_knowledge apenas para informações internas.
    """
    from src.agents._config import load_agents_config

    monkeypatch.chdir(tmp_path)
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    agents_yaml = """
globals:
  default_model: "gpt-4o-mini"
  default_features:
    memory: true
    rag: false

agents:
  - name: "Agente Com RAG"
    department: "marketing"
    features:
      rag: true
    instructions:
      - "Instrução existente"
      - "Use a ferramenta search_knowledge apenas quando a pergunta envolver informações internas da empresa, documentos, políticas ou dados específicos do departamento."

  - name: "Agente Sem RAG"
    department: "geral"
    features:
      rag: false
    instructions:
      - "Instrução sem RAG"
"""
    (config_dir / "agents.yaml").write_text(agents_yaml, encoding="utf-8")

    agents = load_agents_config()

    rag_agent = next(a for a in agents if a.name == "Agente Com RAG")
    no_rag_agent = next(a for a in agents if a.name == "Agente Sem RAG")

    rag_instruction = "Use a ferramenta search_knowledge apenas quando a pergunta envolver informações internas"
    assert any(rag_instruction in instr for instr in rag_agent.instructions), (
        "Agente com RAG deve ter instrução guia para search_knowledge"
    )
    assert not any(rag_instruction in instr for instr in no_rag_agent.instructions), (
        "Agente sem RAG não deve ter instrução de search_knowledge"
    )
