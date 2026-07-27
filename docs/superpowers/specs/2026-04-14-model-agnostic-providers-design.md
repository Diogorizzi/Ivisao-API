# Model-Agnostic Provider System

**Date:** 2026-04-14
**Status:** Approved
**Branch:** feat/multi-agent-system

## Problem

The current `llm_providers.py` is a flat `if/elif` function that only supports OpenAI, Anthropic, Google (Gemini), and Groq. Model IDs in `agents.yaml` are bare strings without provider prefix (e.g. `"gpt-4o-mini"`), making the active provider implicit and controlled solely by `LLM_PROVIDER` in `.env`. There is no support for AWS Bedrock or Google Vertex AI, no startup visibility into which providers are available, and no clear error when a provider is misconfigured.

## Goal

Allow the project leader to connect any of the following providers by setting the appropriate credentials in `.env`:
- OpenAI
- Anthropic
- Google Gemini (native API)
- AWS Bedrock
- Google Vertex AI
- Groq
- OpenRouter

If a provider's credentials are not present, it does not appear as available. Switching providers is explicit: the agent's `model:` field in `agents.yaml` uses `provider:model_id` format. The system logs available providers at startup and raises clear errors when credentials are missing.

## Design Decisions

**Model string format:** `provider:model_id` — explicit, no inference. Every `model:` field in `agents.yaml` must use this format. Bare strings without a `:` raise an error with a helpful message.

**Provider registry pattern:** Each provider is a class with `is_available()`, `build_model()`, and `missing_vars()` methods. The registry is a dict keyed by provider ID string. `get_model()` parses the string, looks up the provider, validates availability, and delegates instantiation.

**Credential resolution for Bedrock and Vertex:** Project-prefixed variables (`BEDROCK_AWS_*`, `VERTEX_*`) take priority over SDK standard variables (`AWS_*`, `GOOGLE_CLOUD_*`). Both are checked in `is_available()` — either set is sufficient.

**No silent fallbacks:** `get_model()` raises `ValueError` with actionable messages rather than falling back to a default provider.

## Architecture

```
config/agents.yaml
  model: "anthropic:claude-3-5-haiku-20241022"
          │           │
     provider_id   model_id
          │
  src/config/llm_providers.py
          │
  PROVIDER_REGISTRY["anthropic"]
          │
  AnthropicProvider
    .is_available()  → checks ANTHROPIC_API_KEY
    .build_model()   → Claude(id=model_id, api_key=...)
          │
  agno.models.anthropic.Claude instance
          │
  src/agents/_factory.py  (unchanged interface)
    get_model(agent_config.model)
```

## Provider Registry Interface

```python
class BaseProvider:
    name: str           # "openai", "bedrock", etc.
    display_name: str   # "OpenAI", "AWS Bedrock", etc.

    def is_available(self) -> bool:
        """True if all required credentials are present."""

    def build_model(self, model_id: str):
        """Return instantiated Agno model object with credentials."""

    def missing_vars(self) -> list[str]:
        """Return list of missing env var names for error messages."""
```

## Provider Credential Mapping

| Provider ID | Primary vars (project-prefixed) | Fallback (SDK standard) |
|---|---|---|
| `openai` | `OPENAI_API_KEY` | — |
| `anthropic` | `ANTHROPIC_API_KEY` | — |
| `google` | `GOOGLE_API_KEY` | — |
| `groq` | `GROQ_API_KEY` | — |
| `openrouter` | `OPENROUTER_API_KEY` | — |
| `bedrock` | `BEDROCK_AWS_ACCESS_KEY_ID`<br>`BEDROCK_AWS_SECRET_ACCESS_KEY`<br>`BEDROCK_AWS_REGION` | `AWS_ACCESS_KEY_ID`<br>`AWS_SECRET_ACCESS_KEY`<br>`AWS_DEFAULT_REGION` |
| `vertex` | `VERTEX_PROJECT_ID`<br>`VERTEX_CREDENTIALS_FILE`<br>`VERTEX_LOCATION` | `GOOGLE_CLOUD_PROJECT`<br>`GOOGLE_APPLICATION_CREDENTIALS` |

`VERTEX_LOCATION` defaults to `"us-east5"` if not set.

## Public API

### `get_model(model_string: str)`

```python
# Usage
model = get_model("anthropic:claude-3-5-haiku-20241022")
model = get_model("bedrock:anthropic.claude-3-5-haiku-20241022-v1:0")
model = get_model("openai:gpt-4o-mini")

# Error: no provider prefix
get_model("gpt-4o-mini")
# → ValueError: Modelo "gpt-4o-mini" não tem prefixo de provider.
#   Use o formato "provider:model_id". Ex: "openai:gpt-4o-mini"

# Error: unknown provider
get_model("cohere:command-r")
# → ValueError: Provider "cohere" não reconhecido.
#   Disponíveis: ['openai', 'anthropic', 'google', 'groq', 'openrouter', 'bedrock', 'vertex']

# Error: missing credentials
get_model("bedrock:anthropic.claude-3-5-haiku-20241022-v1:0")
# → ValueError: Provider "bedrock" não está disponível.
#   Variáveis ausentes: BEDROCK_AWS_ACCESS_KEY_ID, BEDROCK_AWS_SECRET_ACCESS_KEY
#   Dica: Configure essas variáveis no .env ou use as variáveis padrão da AWS:
#         AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_DEFAULT_REGION
```

### `get_available_providers() -> dict[str, bool]`

```python
# Returns availability status for all registered providers
{
  "openai": True,
  "anthropic": True,
  "google": False,
  "groq": False,
  "openrouter": False,
  "bedrock": False,
  "vertex": False,
}
```

## Startup Logging (`src/app.py`)

```python
from src.config.llm_providers import get_available_providers

available = get_available_providers()
print("\n[LLM Providers]")
for name, ok in available.items():
    status = "✓ disponível" if ok else "✗ sem credenciais"
    print(f"  {name}: {status}")
print()
```

Output example:
```
[LLM Providers]
  openai:     ✓ disponível
  anthropic:  ✓ disponível
  google:     ✗ sem credenciais
  groq:       ✗ sem credenciais
  openrouter: ✗ sem credenciais
  bedrock:    ✗ sem credenciais
  vertex:     ✗ sem credenciais
```

## agents.yaml — Model String Updates

All `model:` fields updated to use `provider:model_id` format. Placeholder names (`gpt-5.4`, `gpt-5.4-mini`) replaced with real OpenAI model IDs:

```yaml
# Before
globals:
  default_model: "gpt-4o-mini"

agents:
  - name: "Super Admin Assistant"
    model: "gpt-5.4"
  - name: "General Assistant"
    model: "gpt-5.4-mini"

# After
globals:
  default_model: "openai:gpt-4o-mini"

agents:
  - name: "Super Admin Assistant"
    model: "openai:gpt-4o"
  - name: "General Assistant"
    model: "openai:gpt-4o-mini"
```

## Settings Changes (`src/config/settings.py`)

New optional variables added:

```python
# Bedrock
BEDROCK_AWS_ACCESS_KEY_ID: Optional[str] = None
BEDROCK_AWS_SECRET_ACCESS_KEY: Optional[str] = None
BEDROCK_AWS_REGION: Optional[str] = None

# Vertex AI
VERTEX_PROJECT_ID: Optional[str] = None
VERTEX_LOCATION: str = "us-east5"
VERTEX_CREDENTIALS_FILE: Optional[str] = None
```

`LLM_PROVIDER` and `DEFAULT_MODEL_ID` are retained for backward compatibility but no longer drive `get_model()` behavior.

## .env.example Changes

New sections added with inline documentation on the `provider:model_id` format and example model IDs for each provider.

## Files Modified

| File | Change |
|---|---|
| `src/config/llm_providers.py` | Full rewrite — provider registry |
| `src/config/settings.py` | +6 Bedrock/Vertex variables |
| `.env.example` | New Bedrock and Vertex sections with comments |
| `config/agents.yaml` | `provider:` prefix on all `model:` fields |
| `src/app.py` | Startup log of available providers |

## Files Unchanged

`src/agents/_factory.py`, `src/agents/_config.py`, `src/agents/_base.py`, tools, knowledge base — the `get_model(model_string)` interface is identical.

## Agno Model Classes Reference

| Provider | Agno import |
|---|---|
| OpenAI | `agno.models.openai.OpenAIChat` |
| Anthropic | `agno.models.anthropic.Claude` |
| Google Gemini | `agno.models.google.Gemini` |
| Groq | `agno.models.groq.Groq` |
| OpenRouter | `agno.models.openrouter.OpenRouter` |
| AWS Bedrock | `agno.models.aws.bedrock.Bedrock` (verify import path during implementation) |
| Vertex AI | `agno.models.vertexai.claude.Claude` (verify import path during implementation) |

Note: Bedrock and Vertex import paths should be verified against the installed agno version during implementation.
