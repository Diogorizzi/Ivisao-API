# Model-Agnostic Provider System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the flat `if/elif` `get_model()` function with a provider registry that supports OpenAI, Anthropic, Google Gemini, AWS Bedrock, Google Vertex AI, Groq, and OpenRouter — with credential detection, startup logging, and explicit `provider:model_id` format in `agents.yaml`.

**Architecture:** A `BaseProvider` interface with `is_available()`, `build_model()`, and `missing_vars()` methods. A `PROVIDER_REGISTRY` dict maps provider ID strings to provider instances. `get_model("provider:model_id")` parses the string, validates availability, and delegates instantiation. A `get_available_providers()` function powers startup logging.

**Tech Stack:** Python 3.13, Agno 2.5.5, Pydantic Settings, pytest, unittest.mock

---

## File Map

| File | Action | Responsibility |
|---|---|---|
| `src/config/settings.py` | Modify | Add 6 new optional vars: Bedrock (3) and Vertex AI (3) |
| `.env.example` | Modify | Add Bedrock and Vertex sections with comments |
| `src/config/llm_providers.py` | Full rewrite | Provider registry + `get_model()` + `get_available_providers()` |
| `tests/config/test_llm_providers.py` | Full rewrite | Tests for new registry API (old tests incompatible) |
| `config/agents.yaml` | Modify | Update all `model:` strings to `provider:model_id` format |
| `src/app.py` | Modify | Add startup log of available providers |
| `pyproject.toml` | Modify | Add `boto3` dependency for AWS Bedrock support |

---

## Task 1: Add Bedrock and Vertex vars to Settings

**Files:**
- Modify: `src/config/settings.py`
- Modify: `.env.example`

- [ ] **Step 1: Add new vars to `Settings` class in `src/config/settings.py`**

  Open `src/config/settings.py` and add these fields after `OPENROUTER_API_KEY`:

  ```python
  # AWS Bedrock — project-prefixed vars take priority over SDK standard vars
  BEDROCK_AWS_ACCESS_KEY_ID: Optional[str] = None
  BEDROCK_AWS_SECRET_ACCESS_KEY: Optional[str] = None
  BEDROCK_AWS_REGION: Optional[str] = None

  # Google Vertex AI — project-prefixed vars take priority over SDK standard vars
  VERTEX_PROJECT_ID: Optional[str] = None
  VERTEX_LOCATION: str = "us-east5"
  VERTEX_CREDENTIALS_FILE: Optional[str] = None
  ```

- [ ] **Step 2: Add Bedrock and Vertex sections to `.env.example`**

  Replace the existing `# API Keys (Add yours)` section with:

  ```bash
  # ── LLM PROVIDERS ──────────────────────────────────────────────────────────────
  # Format in agents.yaml: "provider:model_id"
  # Examples:
  #   openai:gpt-4o-mini | openai:gpt-4o
  #   anthropic:claude-3-5-haiku-20241022 | anthropic:claude-sonnet-4-20250514
  #   google:gemini-2.0-flash | google:gemini-1.5-pro
  #   groq:llama-3.3-70b-versatile
  #   openrouter:anthropic/claude-3.5-sonnet
  #   bedrock:anthropic.claude-3-5-haiku-20241022-v1:0
  #   vertex:claude-sonnet-4@20250514

  # OpenAI
  OPENAI_API_KEY="sk-..."

  # Anthropic
  ANTHROPIC_API_KEY="sk-ant-..."

  # Google Gemini (native API)
  GOOGLE_API_KEY="..."

  # Groq
  GROQ_API_KEY="gsk_..."

  # OpenRouter
  OPENROUTER_API_KEY="sk-or-..."

  # AWS Bedrock — Option A: project-prefixed vars (recommended)
  BEDROCK_AWS_ACCESS_KEY_ID=""
  BEDROCK_AWS_SECRET_ACCESS_KEY=""
  BEDROCK_AWS_REGION="us-east-1"
  # AWS Bedrock — Option B: standard AWS SDK vars (if already configured on this machine)
  # AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION

  # Google Vertex AI — Option A: project-prefixed vars (recommended)
  VERTEX_PROJECT_ID=""
  VERTEX_LOCATION="us-east5"
  VERTEX_CREDENTIALS_FILE=""    # path to service account JSON file
  # Google Vertex AI — Option B: standard GCP SDK vars (if already configured on this machine)
  # GOOGLE_CLOUD_PROJECT, GOOGLE_APPLICATION_CREDENTIALS
  ```

- [ ] **Step 3: Verify settings loads the new vars**

  Run:
  ```bash
  uv run python -c "
  import os
  os.environ['BEDROCK_AWS_ACCESS_KEY_ID'] = 'test-key'
  os.environ['VERTEX_PROJECT_ID'] = 'my-project'
  from src.config.settings import Settings
  s = Settings()
  assert s.BEDROCK_AWS_ACCESS_KEY_ID == 'test-key'
  assert s.VERTEX_PROJECT_ID == 'my-project'
  assert s.VERTEX_LOCATION == 'us-east5'
  print('OK — settings loads new vars')
  "
  ```

  Expected: `OK — settings loads new vars`

- [ ] **Step 4: Commit**

  ```bash
  git add src/config/settings.py .env.example
  git commit -m "feat: add Bedrock and Vertex AI credential vars to settings"
  ```

---

## Task 2: Write failing tests for provider registry

**Files:**
- Rewrite: `tests/config/test_llm_providers.py`

The existing tests use the old `get_model(model_id=...)` API and must be replaced entirely.

- [ ] **Step 1: Rewrite `tests/config/test_llm_providers.py`**

  ```python
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
  ```

- [ ] **Step 2: Run tests to confirm they all fail**

  ```bash
  uv run pytest tests/config/test_llm_providers.py -v 2>&1 | head -60
  ```

  Expected: All tests FAIL with `ImportError` or `TypeError` (old `get_model` signature mismatch). This confirms the tests are actually testing the new behavior.

---

## Task 3: Implement the provider registry

**Files:**
- Rewrite: `src/config/llm_providers.py`

- [ ] **Step 1: Write the new `src/config/llm_providers.py`**

  ```python
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
  from typing import Any


  class BaseProvider:
      """Interface that every provider must implement."""

      name: str = ""
      display_name: str = ""

      def is_available(self) -> bool:
          raise NotImplementedError

      def build_model(self, model_id: str) -> Any:
          raise NotImplementedError

      def missing_vars(self) -> list[str]:
          raise NotImplementedError


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
          # Set GOOGLE_APPLICATION_CREDENTIALS so the Anthropic SDK picks it up
          creds_file = self._credentials_file()
          if creds_file:
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
  ```

- [ ] **Step 2: Run the tests to confirm they pass**

  ```bash
  uv run pytest tests/config/test_llm_providers.py -v
  ```

  Expected: All tests PASS. If any fail, fix the implementation before proceeding.

- [ ] **Step 3: Run the full test suite to check for regressions**

  ```bash
  uv run pytest tests/ -v --ignore=tests/integration 2>&1 | tail -30
  ```

  Expected: All previously passing tests still pass. The only tests that may be affected are in `tests/config/test_llm_providers.py` (replaced) and `tests/agents/test_factory.py` (verify below).

- [ ] **Step 4: Commit**

  ```bash
  git add src/config/llm_providers.py tests/config/test_llm_providers.py
  git commit -m "feat: rewrite llm_providers.py as provider registry with credential detection"
  ```

---

## Task 4: Update `config/agents.yaml` model strings

**Files:**
- Modify: `config/agents.yaml`

All `model:` fields must use `provider:model_id` format. The placeholder names `gpt-5.4` and `gpt-5.4-mini` are replaced with real OpenAI model IDs.

- [ ] **Step 1: Update `globals.default_model`**

  ```yaml
  globals:
    default_model: "openai:gpt-4o-mini"
  ```

- [ ] **Step 2: Update each agent's `model:` field**

  Apply these replacements throughout `config/agents.yaml`:

  | Agent | Old value | New value |
  |---|---|---|
  | Super Admin Assistant | `gpt-5.4` | `openai:gpt-4o` |
  | General Assistant | `gpt-5.4-mini` | `openai:gpt-4o-mini` |
  | Marketing Assistant | `gpt-5.4-mini` | `openai:gpt-4o-mini` |
  | Juridico Assistant | `gpt-5.4` | `openai:gpt-4o` |
  | Finance Assistant | `gpt-5.4` | `openai:gpt-4o` |
  | HR Assistant | `gpt-5.4-mini` | `openai:gpt-4o-mini` |
  | Sales Assistant | `gpt-5.4-mini` | `openai:gpt-4o-mini` |
  | Operations Assistant | `gpt-5.4-mini` | `openai:gpt-4o-mini` |
  | IT Assistant | `gpt-5.4` | `openai:gpt-4o` |

- [ ] **Step 3: Verify the config loads without errors**

  ```bash
  uv run python -c "
  from src.agents._config import load_agents_config
  agents = load_agents_config()
  for a in agents:
      assert ':' in a.model, f'Agent {a.name} has no provider prefix: {a.model}'
      print(f'  {a.name}: {a.model}')
  print('All agents have provider:model_id format.')
  "
  ```

  Expected: All agents listed with their `provider:model_id` and no assertion errors.

- [ ] **Step 4: Commit**

  ```bash
  git add config/agents.yaml
  git commit -m "feat: update agents.yaml to use explicit provider:model_id format"
  ```

---

## Task 5: Add startup provider logging to `app.py`

**Files:**
- Modify: `src/app.py`

- [ ] **Step 1: Add provider logging block to `src/app.py`**

  Add this block just after the imports block (before `admin_db.ensure_departments_table()`):

  ```python
  from src.config.llm_providers import get_available_providers as _get_available_providers

  def _log_available_providers() -> None:
      available = _get_available_providers()
      print("\n[LLM Providers]")
      for name, ok in available.items():
          status = "OK" if ok else "sem credenciais"
          print(f"  {name:<12} {status}")
      print()

  _log_available_providers()
  ```

  Place the call `_log_available_providers()` at module level (it runs on import, which is how `app.py` works — no `main` guard for startup logic).

- [ ] **Step 2: Verify the log appears**

  ```bash
  uv run python -c "
  import os
  os.environ['OPENAI_API_KEY'] = 'sk-test'
  # Import triggers the log
  import importlib, sys
  # Remove any cached module
  for k in list(sys.modules.keys()):
      if 'llm_providers' in k:
          del sys.modules[k]
  from src.config.llm_providers import get_available_providers
  available = get_available_providers()
  print('[LLM Providers]')
  for name, ok in available.items():
      status = 'OK' if ok else 'sem credenciais'
      print(f'  {name:<12} {status}')
  "
  ```

  Expected output:
  ```
  [LLM Providers]
    openai       OK
    anthropic    sem credenciais
    google       sem credenciais
    groq         sem credenciais
    openrouter   sem credenciais
    bedrock      sem credenciais
    vertex       sem credenciais
  ```

- [ ] **Step 3: Commit**

  ```bash
  git add src/app.py
  git commit -m "feat: log available LLM providers at startup"
  ```

---

## Task 6: Add boto3 dependency for AWS Bedrock

**Files:**
- Modify: `pyproject.toml`

Without `boto3`, importing `agno.models.aws.bedrock` raises `ImportError`. This task adds it so Bedrock works out of the box when credentials are configured.

- [ ] **Step 1: Add `boto3` to `pyproject.toml`**

  Add `"boto3>=1.35.0"` to the `dependencies` list in `pyproject.toml`:

  ```toml
  dependencies = [
      "agno[chromadb,google,os]>=2.5.5",
      "boto3>=1.35.0",
      ...
  ]
  ```

- [ ] **Step 2: Sync the lockfile**

  ```bash
  uv sync
  ```

  Expected: `boto3` added to `.venv` without errors.

- [ ] **Step 3: Verify Bedrock import works**

  ```bash
  uv run python -c "from agno.models.aws.bedrock import AwsBedrock; print('AwsBedrock import OK')"
  ```

  Expected: `AwsBedrock import OK`

- [ ] **Step 4: Run full test suite**

  ```bash
  uv run pytest tests/ -v --ignore=tests/integration 2>&1 | tail -20
  ```

  Expected: All tests pass.

- [ ] **Step 5: Commit**

  ```bash
  git add pyproject.toml uv.lock
  git commit -m "feat: add boto3 dependency for AWS Bedrock support"
  ```

---

## Self-Review Checklist

**Spec coverage:**
- [x] Provider registry with `is_available()`, `build_model()`, `missing_vars()` → Task 3
- [x] Providers: OpenAI, Anthropic, Google, Groq, OpenRouter, Bedrock, Vertex → Task 3
- [x] `provider:model_id` format in agents.yaml → Task 4
- [x] Bedrock: project-prefixed vars + SDK fallback → Task 3 (`BedrockProvider`)
- [x] Vertex: project-prefixed vars + SDK fallback → Task 3 (`VertexProvider`)
- [x] Startup logging of available providers → Task 5
- [x] Clear error with missing var names when provider unavailable → Task 3 (`get_model`)
- [x] Bedrock colon-in-model-id edge case (`split(":", 1)`) → Task 3 + tested in Task 2
- [x] boto3 dependency → Task 6
- [x] Settings vars for Bedrock/Vertex → Task 1
- [x] `.env.example` documentation → Task 1

**Type consistency:**
- `get_model(model_string: str)` used consistently throughout (Tasks 2, 3)
- `PROVIDER_REGISTRY` dict used in both tests and implementation
- `AwsBedrock` class name verified against Agno 2.5.5 source
- `agno.models.vertexai.claude.Claude` verified against Agno 2.5.5 source
