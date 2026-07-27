"""Integration tests for the complete multi-agent system"""
import pytest
from pathlib import Path
from unittest.mock import patch, Mock

def test_full_system_loads(tmp_path, monkeypatch):
    """Test that the entire system loads successfully"""
    monkeypatch.chdir(tmp_path)

    # Setup config
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    (config_dir / "company.yaml").write_text("""
company_name: "Test Co"
company_description: "Test company"
""")

    (config_dir / "agents.yaml").write_text("""
globals:
  default_model: "gpt-4o-mini"
  default_features:
    memory: true
    rag: false

agents:
  - name: "Test Agent"
    department: "test"
    features: {}
    tools: []
    skills: []
    instructions:
      - "Test instruction"
""")

    # Create minimal skills dir
    skills_dir = tmp_path / "src" / "skills"
    skills_dir.mkdir(parents=True)

    # Mock Agno dependencies
    with patch('src.agents._factory.get_model') as mock_model, \
         patch('src.agents._factory.load_dynamic_tools') as mock_tools, \
         patch('src.agents._factory.create_base_agent') as mock_create, \
         patch('src.agents._factory.Skills') as mock_skills:

        mock_model.return_value = Mock()
        mock_tools.return_value = []
        mock_create.return_value = Mock()
        mock_skills.return_value = Mock()

        from src.agents._factory import load_all_agents

        agents = load_all_agents()

        assert len(agents) == 1
        assert agents[0] is not None


def test_agent_isolation():
    """Test that department isolation works"""
    # Test department filtering logic in get_knowledge_base
    with patch('src.knowledge.base.GeminiEmbedder'), \
         patch('src.knowledge.base.SqliteDb'), \
         patch('src.knowledge.base.MarkItDownReader'), \
         patch('src.knowledge.base.Knowledge'), \
         patch('src.knowledge.base.DarthaHttpChromaDb') as mock_chroma:

        from src.knowledge.base import get_knowledge_base

        # Reset the global instance to test fresh calls
        import src.knowledge.base as kb_module
        kb_module._knowledge_instance = None

        # Call with marketing department
        knowledge_marketing = get_knowledge_base(department="marketing")
        assert knowledge_marketing is not None

        # Verify the department was passed to DarthaHttpChromaDb
        mock_chroma.assert_called()
        call_kwargs = mock_chroma.call_args[1]
        assert call_kwargs["department"] == "marketing"

        # Reset for next test
        kb_module._knowledge_instance = None

        # Call with juridico department
        knowledge_juridico = get_knowledge_base(department="juridico")
        assert knowledge_juridico is not None

        # Verify different department was passed
        last_call_kwargs = mock_chroma.call_args[1]
        assert last_call_kwargs["department"] == "juridico"
