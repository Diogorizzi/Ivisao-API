"""
Provider registry for LLM model instantiation.

Usage:
    model = get_model("openai:gpt-4o-mini")
    model = get_model("anthropic:claude-3-5-haiku-20241022")
    model = get_model("bedrock:anthropic.claude-3-5-haiku-20241022-v1:0")
    model = get_model("vertex:claude-sonnet-4@20250514")

Available providers:
    openai, anthropic, google, groq, openrouter, bedrock, vertex
"""
from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import Any


class BaseProvider(ABC):
    """Interface that every provider must implement."""

    name: str = ""
    display_name: str = ""

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if all required credentials are present."""

    @abstractmethod
    def build_model(self, model_id: str) -> Any:
        """Return an instantiated Agno model object with credentials."""

    @abstractmethod
    def missing_vars(self) -> list[str]:
        """Return list of missing env var names for error messages."""


# ── Simple API-key providers ───────────────────────────────────────────────────

class OpenAIProvider(BaseProvider):
    name = "openai"
    display_name = "OpenAI"
    _var = "OPENAI_API_KEY"

    def is_available(self) -> bool:
        return bool(os.environ.get(self._var))

    def missing_vars(self) -> list[str]:
        return [] if self.is_available() else [self._var]

    def build_model(self, model_id: str) -> Any:
        from agno.models.openai import OpenAIChat
        return OpenAIChat(id=model_id, api_key=os.environ[self._var])


class AnthropicProvider(BaseProvider):
    name = "anthropic"
    display_name = "Anthropic"
    _var = "ANTHROPIC_API_KEY"

    def is_available(self) -> bool:
        return bool(os.environ.get(self._var))

    def missing_vars(self) -> list[str]:
        return [] if self.is_available() else [self._var]

    def build_model(self, model_id: str) -> Any:
        from agno.models.anthropic import Claude
        return Claude(id=model_id, api_key=os.environ[self._var])


class GoogleProvider(BaseProvider):
    name = "google"
    display_name = "Google Gemini"
    _var = "GOOGLE_API_KEY"

    def is_available(self) -> bool:
        return bool(os.environ.get(self._var))

    def missing_vars(self) -> list[str]:
        return [] if self.is_available() else [self._var]

    def build_model(self, model_id: str) -> Any:
        from agno.models.google import Gemini
        return Gemini(id=model_id, api_key=os.environ[self._var])


class GroqProvider(BaseProvider):
    name = "groq"
    display_name = "Groq"
    _var = "GROQ_API_KEY"

    def is_available(self) -> bool:
        return bool(os.environ.get(self._var))

    def missing_vars(self) -> list[str]:
        return [] if self.is_available() else [self._var]

    def build_model(self, model_id: str) -> Any:
        from agno.models.groq import Groq
        return Groq(id=model_id, api_key=os.environ[self._var])


class OpenRouterProvider(BaseProvider):
    name = "openrouter"
    display_name = "OpenRouter"
    _var = "OPENROUTER_API_KEY"

    def is_available(self) -> bool:
        return bool(os.environ.get(self._var))

    def missing_vars(self) -> list[str]:
        return [] if self.is_available() else [self._var]

    def build_model(self, model_id: str) -> Any:
        from agno.models.openrouter import OpenRouter
        return OpenRouter(id=model_id, api_key=os.environ[self._var])


# ── AWS Bedrock ────────────────────────────────────────────────────────────────

class BedrockProvider(BaseProvider):
    """
    Supports two credential sources (project-prefixed takes priority):
      Project vars: BEDROCK_AWS_ACCESS_KEY_ID, BEDROCK_AWS_SECRET_ACCESS_KEY, BEDROCK_AWS_REGION
      SDK standard: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION
    """
    name = "bedrock"
    display_name = "AWS Bedrock"

    _project_vars = ("BEDROCK_AWS_ACCESS_KEY_ID", "BEDROCK_AWS_SECRET_ACCESS_KEY", "BEDROCK_AWS_REGION")
    _sdk_vars = ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_DEFAULT_REGION")

    def _project_credentials(self) -> tuple[str, str, str] | None:
        key = os.environ.get("BEDROCK_AWS_ACCESS_KEY_ID")
        secret = os.environ.get("BEDROCK_AWS_SECRET_ACCESS_KEY")
        region = os.environ.get("BEDROCK_AWS_REGION")
        if key and secret and region:
            return key, secret, region
        return None

    def _sdk_credentials(self) -> tuple[str, str, str] | None:
        key = os.environ.get("AWS_ACCESS_KEY_ID")
        secret = os.environ.get("AWS_SECRET_ACCESS_KEY")
        region = os.environ.get("AWS_DEFAULT_REGION")
        if key and secret and region:
            return key, secret, region
        return None

    def is_available(self) -> bool:
        return self._project_credentials() is not None or self._sdk_credentials() is not None

    def missing_vars(self) -> list[str]:
        if self.is_available():
            return []
        # Report project-prefixed vars as the canonical missing set
        return [v for v in self._project_vars if not os.environ.get(v)]

    def build_model(self, model_id: str) -> Any:
        try:
            from agno.models.aws.bedrock import AwsBedrock
        except ImportError:
            raise ImportError(
                "boto3 não está instalado. Instale com: uv add boto3"
            )

        creds = self._project_credentials() or self._sdk_credentials()
        key, secret, region = creds
        return AwsBedrock(
            id=model_id,
            aws_access_key_id=key,
            aws_secret_access_key=secret,
            aws_region=region,
        )


# ── Google Vertex AI ───────────────────────────────────────────────────────────

class VertexProvider(BaseProvider):
    """
    Supports two credential sources (project-prefixed takes priority):
      Project vars: VERTEX_PROJECT_ID, VERTEX_CREDENTIALS_FILE, VERTEX_LOCATION
      SDK standard: GOOGLE_CLOUD_PROJECT, GOOGLE_APPLICATION_CREDENTIALS
    """
    name = "vertex"
    display_name = "Google Vertex AI"

    def _project_id(self) -> str | None:
        return os.environ.get("VERTEX_PROJECT_ID") or os.environ.get("GOOGLE_CLOUD_PROJECT")

    def _credentials_file(self) -> str | None:
        return os.environ.get("VERTEX_CREDENTIALS_FILE") or os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")

    def _region(self) -> str:
        return os.environ.get("VERTEX_LOCATION") or "us-east5"

    def is_available(self) -> bool:
        return bool(self._project_id() and self._credentials_file())

    def missing_vars(self) -> list[str]:
        if self.is_available():
            return []
        missing = []
        if not self._project_id():
            missing.append("VERTEX_PROJECT_ID")
        if not self._credentials_file():
            missing.append("VERTEX_CREDENTIALS_FILE")
        return missing

    def build_model(self, model_id: str) -> Any:
        creds_file = self._credentials_file()
        if creds_file:
            # Intentional: VertexClaude reads GOOGLE_APPLICATION_CREDENTIALS at
            # call time via the Anthropic SDK. We set it here so the SDK picks up
            # our project-prefixed VERTEX_CREDENTIALS_FILE value.
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = creds_file

        from agno.models.vertexai.claude import Claude as VertexClaude
        return VertexClaude(
            id=model_id,
            project_id=self._project_id(),
            region=self._region(),
        )


# ── Registry ───────────────────────────────────────────────────────────────────

PROVIDER_REGISTRY: dict[str, BaseProvider] = {
    "openai": OpenAIProvider(),
    "anthropic": AnthropicProvider(),
    "google": GoogleProvider(),
    "groq": GroqProvider(),
    "openrouter": OpenRouterProvider(),
    "bedrock": BedrockProvider(),
    "vertex": VertexProvider(),
}


# ── Public API ─────────────────────────────────────────────────────────────────

def get_model(model_string: str) -> Any:
    """
    Parse "provider:model_id" and return an instantiated Agno model object.

    Args:
        model_string: A string in "provider:model_id" format.
                      Example: "openai:gpt-4o-mini"
                      Example: "bedrock:anthropic.claude-3-5-haiku-20241022-v1:0"

    Raises:
        ValueError: If the string has no provider prefix, the provider is
                    unknown, or the provider credentials are not configured.
    """
    if ":" not in model_string:
        raise ValueError(
            f'Modelo "{model_string}" não tem prefixo de provider. '
            f'Use o formato "provider:model_id". Exemplo: "openai:gpt-4o-mini"'
        )

    provider_id, model_id = model_string.split(":", 1)
    provider = PROVIDER_REGISTRY.get(provider_id)

    if provider is None:
        available = list(PROVIDER_REGISTRY.keys())
        raise ValueError(
            f'Provider "{provider_id}" não reconhecido. '
            f'Disponíveis: {available}'
        )

    if not provider.is_available():
        missing = provider.missing_vars()
        hint = _build_hint(provider_id)
        raise ValueError(
            f'Provider "{provider_id}" não está disponível.\n'
            f'Variáveis ausentes: {missing}\n'
            f'{hint}'
        )

    return provider.build_model(model_id)


def get_available_providers() -> dict[str, bool]:
    """Return availability status for every registered provider."""
    return {name: p.is_available() for name, p in PROVIDER_REGISTRY.items()}


def _build_hint(provider_id: str) -> str:
    hints = {
        "bedrock": (
            "Dica: Configure BEDROCK_AWS_ACCESS_KEY_ID, BEDROCK_AWS_SECRET_ACCESS_KEY, "
            "BEDROCK_AWS_REGION no .env\n"
            "      Ou use as variáveis padrão da AWS: AWS_ACCESS_KEY_ID, "
            "AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION"
        ),
        "vertex": (
            "Dica: Configure VERTEX_PROJECT_ID e VERTEX_CREDENTIALS_FILE no .env\n"
            "      Ou use as variáveis padrão do GCP: GOOGLE_CLOUD_PROJECT, "
            "GOOGLE_APPLICATION_CREDENTIALS"
        ),
    }
    return hints.get(provider_id, "Dica: Configure a variável correspondente no arquivo .env")
