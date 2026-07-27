import pytest
from pathlib import Path
from src.agents._config import CompanyConfig, load_company_config, AgentConfig, AgentFeatures, ToolConfig


def test_company_config_validation():
    """Test CompanyConfig Pydantic model"""
    config = CompanyConfig(
        company_name="Test Co",
        company_description="A test company"
    )
    assert config.company_name == "Test Co"
    assert config.default_model == "gpt-4o-mini"  # default value


def test_load_company_config_missing_file(tmp_path, monkeypatch):
    """Test error when company.yaml doesn't exist"""
    monkeypatch.chdir(tmp_path)
    with pytest.raises(FileNotFoundError):
        load_company_config()


def test_agent_features_defaults():
    """Test AgentFeatures default values"""
    features = AgentFeatures()
    assert features.memory is True
    assert features.rag is True
    assert features.web_search is False


def test_agent_config_validation():
    """Test AgentConfig model"""
    config = AgentConfig(
        name="Test Agent",
        department="test",
        features=AgentFeatures(),
        instructions=["Test instruction"]
    )
    assert config.name == "Test Agent"
    assert config.department == "test"
    assert config.model is None  # uses default


def test_interpolate_template():
    """Test variable interpolation"""
    from src.agents._config import interpolate_template

    template = "Hello {{name}} from {{company}}"
    variables = {"name": "User", "company": "Acme"}
    result = interpolate_template(template, variables)

    assert result == "Hello User from Acme"


def test_load_agents_config(tmp_path, monkeypatch):
    """Test loading agents.yaml"""
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
  - name: "Test Agent"
    department: "test"
    features:
      web_search: true
    instructions:
      - "Test instruction"
"""
    (config_dir / "agents.yaml").write_text(agents_yaml)

    agents = load_agents_config()
    assert len(agents) == 1
    assert agents[0].name == "Test Agent"
    assert agents[0].features.web_search is True
    assert agents[0].features.memory is True  # from defaults
