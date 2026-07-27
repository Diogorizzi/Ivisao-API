"""Tests for the provider registry in llm_providers.py."""
import os
import pytest
from unittest.mock import patch, MagicMock


# ── Helpers ──────────────────────────────────────────────────────────────────

def _env(**kwargs):
    """Patch os.environ with the given vars, clearing all provider keys first."""
    clear = {
        "OPENAI_API_KEY": "",
        "ANTHROPIC_API_KEY": "",
        "GOOGLE_API_KEY": "",
        "GROQ_API_KEY": "",
        "OPENROUTER_API_KEY": "",
        "BEDROCK_AWS_ACCESS_KEY_ID": "",
        "BEDROCK_AWS_SECRET_ACCESS_KEY": "",
        "BEDROCK_AWS_REGION": "",
        "AWS_ACCESS_KEY_ID": "",
        "AWS_SECRET_ACCESS_KEY": "",
        "AWS_DEFAULT_REGION": "",
        "VERTEX_PROJECT_ID": "",
        "VERTEX_CREDENTIALS_FILE": "",
        "GOOGLE_CLOUD_PROJECT": "",
        "GOOGLE_APPLICATION_CREDENTIALS": "",
    }
    clear.update(kwargs)
    return patch.dict(os.environ, clear, clear=False)


# ── get_model: format validation ──────────────────────────────────────────────

def test_get_model_raises_when_no_provider_prefix():
    """Bare model ID without provider prefix raises ValueError."""
    from src.config.llm_providers import get_model
    with pytest.raises(ValueError, match="provider:model_id"):
        get_model("gpt-4o-mini")


def test_get_model_raises_on_unknown_provider():
    """Unregistered provider name raises ValueError listing available providers."""
    from src.config.llm_providers import get_model
    with pytest.raises(ValueError, match="cohere"):
        get_model("cohere:command-r")


def test_get_model_raises_when_provider_not_available():
    """Provider with missing credentials raises ValueError naming missing vars."""
    from src.config.llm_providers import get_model
    with _env(OPENAI_API_KEY=""):
        with pytest.raises(ValueError, match="OPENAI_API_KEY"):
            get_model("openai:gpt-4o-mini")


# ── get_model: successful instantiation ──────────────────────────────────────

def test_get_model_openai_returns_openai_chat():
    """get_model with openai: prefix returns an OpenAIChat instance."""
    from src.config.llm_providers import get_model
    with _env(OPENAI_API_KEY="sk-test"):
        with patch("agno.models.openai.OpenAIChat") as MockChat:
            MockChat.return_value = MagicMock()
            result = get_model("openai:gpt-4o-mini")
            MockChat.assert_called_once()
            call_kwargs = MockChat.call_args[1]
            assert call_kwargs["id"] == "gpt-4o-mini"
            assert call_kwargs["api_key"] == "sk-test"


def test_get_model_anthropic_returns_claude():
    """get_model with anthropic: prefix returns a Claude instance."""
    from src.config.llm_providers import get_model
    with _env(ANTHROPIC_API_KEY="sk-ant-test"):
        with patch("agno.models.anthropic.Claude") as MockClaude:
            MockClaude.return_value = MagicMock()
            get_model("anthropic:claude-3-5-haiku-20241022")
            call_kwargs = MockClaude.call_args[1]
            assert call_kwargs["id"] == "claude-3-5-haiku-20241022"
            assert call_kwargs["api_key"] == "sk-ant-test"


def test_get_model_google_returns_gemini():
    """get_model with google: prefix returns a Gemini instance."""
    from src.config.llm_providers import get_model
    with _env(GOOGLE_API_KEY="gkey-test"):
        with patch("agno.models.google.Gemini") as MockGemini:
            MockGemini.return_value = MagicMock()
            get_model("google:gemini-2.0-flash")
            call_kwargs = MockGemini.call_args[1]
            assert call_kwargs["id"] == "gemini-2.0-flash"
            assert call_kwargs["api_key"] == "gkey-test"


def test_get_model_groq_returns_groq():
    """get_model with groq: prefix returns a Groq instance."""
    from src.config.llm_providers import get_model
    with _env(GROQ_API_KEY="gsk-test"):
        with patch("agno.models.groq.Groq") as MockGroq:
            MockGroq.return_value = MagicMock()
            get_model("groq:llama-3.3-70b-versatile")
            call_kwargs = MockGroq.call_args[1]
            assert call_kwargs["id"] == "llama-3.3-70b-versatile"


def test_get_model_openrouter_returns_openrouter():
    """get_model with openrouter: prefix returns an OpenRouter instance."""
    from src.config.llm_providers import get_model
    with _env(OPENROUTER_API_KEY="sk-or-test"):
        with patch("agno.models.openrouter.OpenRouter") as MockOR:
            MockOR.return_value = MagicMock()
            get_model("openrouter:anthropic/claude-3.5-sonnet")
            call_kwargs = MockOR.call_args[1]
            assert call_kwargs["id"] == "anthropic/claude-3.5-sonnet"


# ── Bedrock colon-in-model-id edge case ──────────────────────────────────────

def test_get_model_bedrock_model_id_with_colon():
    """Bedrock model IDs containing colons are parsed correctly (split on first : only)."""
    from src.config.llm_providers import get_model
    with _env(BEDROCK_AWS_ACCESS_KEY_ID="k", BEDROCK_AWS_SECRET_ACCESS_KEY="s", BEDROCK_AWS_REGION="us-east-1"):
        with patch("agno.models.aws.bedrock.AwsBedrock") as MockBedrock:
            MockBedrock.return_value = MagicMock()
            get_model("bedrock:anthropic.claude-3-5-haiku-20241022-v1:0")
            call_kwargs = MockBedrock.call_args[1]
            assert call_kwargs["id"] == "anthropic.claude-3-5-haiku-20241022-v1:0"


# ── Bedrock credential resolution ────────────────────────────────────────────

def test_bedrock_available_with_project_vars():
    """BedrockProvider.is_available() returns True when BEDROCK_* vars are set."""
    from src.config.llm_providers import PROVIDER_REGISTRY
    provider = PROVIDER_REGISTRY["bedrock"]
    with _env(
        BEDROCK_AWS_ACCESS_KEY_ID="key",
        BEDROCK_AWS_SECRET_ACCESS_KEY="secret",
        BEDROCK_AWS_REGION="us-east-1",
    ):
        assert provider.is_available() is True


def test_bedrock_available_with_sdk_vars():
    """BedrockProvider.is_available() returns True when standard AWS_* vars are set."""
    from src.config.llm_providers import PROVIDER_REGISTRY
    provider = PROVIDER_REGISTRY["bedrock"]
    with _env(
        AWS_ACCESS_KEY_ID="key",
        AWS_SECRET_ACCESS_KEY="secret",
        AWS_DEFAULT_REGION="us-east-1",
    ):
        assert provider.is_available() is True


def test_bedrock_not_available_without_credentials():
    """BedrockProvider.is_available() returns False when no AWS vars are set."""
    from src.config.llm_providers import PROVIDER_REGISTRY
    provider = PROVIDER_REGISTRY["bedrock"]
    with _env():
        assert provider.is_available() is False


def test_bedrock_missing_vars_lists_project_vars():
    """BedrockProvider.missing_vars() lists project-prefixed vars when nothing is set."""
    from src.config.llm_providers import PROVIDER_REGISTRY
    provider = PROVIDER_REGISTRY["bedrock"]
    with _env():
        missing = provider.missing_vars()
        assert "BEDROCK_AWS_ACCESS_KEY_ID" in missing


# ── Vertex credential resolution ──────────────────────────────────────────────

def test_vertex_available_with_project_vars():
    """VertexProvider.is_available() returns True when VERTEX_PROJECT_ID and VERTEX_CREDENTIALS_FILE are set."""
    from src.config.llm_providers import PROVIDER_REGISTRY
    provider = PROVIDER_REGISTRY["vertex"]
    with _env(VERTEX_PROJECT_ID="my-project", VERTEX_CREDENTIALS_FILE="/path/creds.json"):
        assert provider.is_available() is True


def test_vertex_available_with_sdk_vars():
    """VertexProvider.is_available() returns True when GOOGLE_CLOUD_PROJECT and GOOGLE_APPLICATION_CREDENTIALS are set."""
    from src.config.llm_providers import PROVIDER_REGISTRY
    provider = PROVIDER_REGISTRY["vertex"]
    with _env(GOOGLE_CLOUD_PROJECT="my-project", GOOGLE_APPLICATION_CREDENTIALS="/path/creds.json"):
        assert provider.is_available() is True


def test_vertex_not_available_without_credentials():
    """VertexProvider.is_available() returns False when no GCP vars are set."""
    from src.config.llm_providers import PROVIDER_REGISTRY
    provider = PROVIDER_REGISTRY["vertex"]
    with _env():
        assert provider.is_available() is False


# ── get_available_providers ───────────────────────────────────────────────────

def test_get_available_providers_returns_all_providers():
    """get_available_providers() returns a key for every registered provider."""
    from src.config.llm_providers import get_available_providers, PROVIDER_REGISTRY
    with _env():
        result = get_available_providers()
    assert set(result.keys()) == set(PROVIDER_REGISTRY.keys())


def test_get_available_providers_openai_true_when_key_set():
    """get_available_providers() shows openai as available when OPENAI_API_KEY is set."""
    from src.config.llm_providers import get_available_providers
    with _env(OPENAI_API_KEY="sk-test"):
        result = get_available_providers()
    assert result["openai"] is True


def test_get_available_providers_all_false_when_no_keys():
    """get_available_providers() shows all providers as unavailable when no keys set."""
    from src.config.llm_providers import get_available_providers
    with _env():
        result = get_available_providers()
    assert all(v is False for v in result.values())
