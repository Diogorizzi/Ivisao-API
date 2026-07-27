# Agno Agent API

Multi-tenant AI agent platform built on [Agno](https://github.com/agno-agi/agno). Supports multiple LLM providers, per-department RAG knowledge bases, per-user MCP server injection, and a skill system.

---

## Prerequisites

- [Python 3.13+](https://www.python.org/downloads/)
- [uv](https://docs.astral.sh/uv/#installation) — Python package manager

```bash
# Install uv (Linux/macOS)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install uv (Windows PowerShell)
irm https://astral.sh/uv/install.ps1 | iex
```

---

## Quick Start

**1. Clone and configure:**
```bash
git clone <your-repo-url>
cd <repo-name>
cp .env.example .env
# Edit .env — at minimum set OPENAI_API_KEY and ADMIN_SECRET_KEY
```

**2. Install dependencies:**
```bash
uv sync
```

**3. Start the server:**
```bash
# Linux/macOS
uv run python -m src.app

# Windows
.\start.ps1
```

The server will be available at **http://localhost:7777**

> **RAG (knowledge base):** requires ChromaDB running separately. Without it, agents start normally but return no knowledge results. Start ChromaDB with Docker: `docker run -p 8000:8000 chromadb/chroma:latest`

| URL | Description |
|-----|-------------|
| `http://localhost:7777/docs` | Swagger UI |
| `http://localhost:7777/redoc` | ReDoc |
| [os.agno.com](https://os.agno.com) | Visual UI → Add Local OS → `http://localhost:7777` |

---

## Environment Variables

Copy `.env.example` to `.env` and fill in your values.

**Minimum required to start:**
- One LLM API key (e.g. `OPENAI_API_KEY`)
- `ADMIN_SECRET_KEY` set to any random string (the server refuses to start with the default value)

Everything else is optional — ChromaDB (RAG), MCP servers, and Neo4j degrade gracefully if not configured.

### LLM Providers

At least one provider must be configured. The server detects which are available at startup and logs their status.

| Provider | Variable(s) | Example model ID |
|----------|-------------|------------------|
| OpenAI | `OPENAI_API_KEY` | `openai:gpt-4o-mini` |
| Anthropic | `ANTHROPIC_API_KEY` | `anthropic:claude-3-5-haiku-20241022` |
| Google Gemini | `GOOGLE_API_KEY` | `google:gemini-2.0-flash` |
| Groq | `GROQ_API_KEY` | `groq:llama-3.3-70b-versatile` |
| OpenRouter | `OPENROUTER_API_KEY` | `openrouter:anthropic/claude-3.5-sonnet` |
| AWS Bedrock | `BEDROCK_AWS_ACCESS_KEY_ID` + `BEDROCK_AWS_SECRET_ACCESS_KEY` + `BEDROCK_AWS_REGION` | `bedrock:anthropic.claude-3-5-haiku-20241022-v1:0` |
| Google Vertex AI | `VERTEX_PROJECT_ID` + `VERTEX_CREDENTIALS_FILE` | `vertex:claude-sonnet-4@20250514` |

### MCP Servers (per-user injection)

Allows users to connect their own MCP servers. These tools are injected automatically into agent requests.

```env
MCP_DB_URL=postgresql+psycopg://user:pass@host/dbname?sslmode=require
```

That's it. On first startup, an encryption key is generated automatically and stored in the database — no manual step required. Each deployment gets its own isolated key.

If `MCP_DB_URL` is not set, MCP injection is silently disabled and the rest of the platform works normally.

### Admin Panel

The admin panel manages RAG knowledge documents.

```bash
# Generate the password hash:
uv run python -c "from passlib.context import CryptContext; print(CryptContext(schemes=['bcrypt']).hash('your-password'))"
```

```env
ADMIN_USERNAME=admin
ADMIN_PASSWORD_HASH=<output from command above>
ADMIN_SECRET_KEY=<random 32+ character string>
```

Generate a random secret key:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

---

## Agents

Agents are configured in `config/agents.yaml`. Each agent has an optional LLM model, knowledge base (RAG), tools, and skills.

```yaml
agents:
  - name: "General Assistant"
    department: "general"
    model: "openai:gpt-4o-mini"   # format: provider:model_id
    description: "General purpose assistant"

    features:
      memory: true
      rag: true
      web_search: false
      add_history: true
      num_history_runs: 10

    tools:
      - name: "DuckDuckGoTools"

    skills:
      - "shared/data-analysis"
      - "shared/web-research"
```

**To add a new agent:**
1. Add an entry in `config/agents.yaml`
2. Optionally create a custom Python file in `src/agents/` for advanced logic

**To change a model:**
Edit the `model:` field in `config/agents.yaml` using the `provider:model_id` format.

---

## Knowledge Base (RAG)

Each agent with `rag: true` gets its own isolated knowledge base. Documents live in `data/{department}/`:

```
data/
├── marketing/
├── finance/
├── hr/
├── sales/
├── operations/
└── it/
```

Upload documents via the admin panel at `/admin` or drop files directly into the department folder. An agent with `department: null` (Super Admin) sees all data.

---

## MCP Servers

Users can connect their own MCP servers. When a user sends a message, their connected MCP tools are automatically injected into the agent for that request only — transparent and thread-safe.

### API Endpoints

All endpoints require an `X-User-Id` header identifying the user.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/mcp-servers` | List user's connected servers + global catalogue |
| `POST` | `/api/mcp-servers` | Connect a new MCP server |
| `PATCH` | `/api/mcp-servers/{id}` | Update a connected server |
| `DELETE` | `/api/mcp-servers/{id}` | Disconnect (soft delete) |
| `GET` | `/api/mcp-servers/global` | Browse the global server catalogue |

### Connecting a Server

```bash
curl -X POST http://localhost:7777/api/mcp-servers \
  -H "X-User-Id: user_123" \
  -H "Authorization: Bearer <api-key>" \
  -H "Content-Type: application/json" \
  -d '{
    "label": "My MCP Server",
    "url": "https://my-mcp-server.example.com",
    "auth_type": "api_key",
    "credentials": "my-token"
  }'
```

`auth_type` options: `none`, `api_key`, `oauth`. Credentials are encrypted at rest using Fernet symmetric encryption.

### How Injection Works

1. The frontend sends a `POST /agents/{id}/runs` request with `user_id` in the form body (the existing `agno-proxy` already does this)
2. `MCPInjectionMiddleware` intercepts the request and loads the user's connected MCP servers from the database
3. `MCPTools` instances are stored in a `ContextVar` (per-request isolated, thread-safe)
4. A monkey-patch on `agno.os.utils.get_agent_by_id` injects the tools into the agent's `deep_copy` before execution
5. After the request completes, the context is reset — tools never leak between requests

---

## Project Structure

```
src/
├── app.py              # FastAPI app entry point
├── agents/             # Agent definitions and factory
│   ├── _factory.py     # Loads agents from config/agents.yaml
│   └── *.py            # Custom agent implementations
├── config/             # Settings and LLM provider resolution
├── knowledge/          # RAG knowledge base setup
├── mcp_servers/        # Per-user MCP server management
│   ├── models.py       # SQLAlchemy models
│   ├── schemas.py      # Pydantic request/response schemas
│   ├── crud.py         # Database operations
│   ├── routes.py       # REST API endpoints
│   ├── injection.py    # Middleware + agent patch for tool injection
│   ├── encryption.py   # Fernet credential encryption
│   └── db.py           # Database session factory
├── middleware/         # HTTP middleware (API key auth)
├── skills/             # Agent skill system
└── tools/              # Custom tool implementations
config/
└── agents.yaml         # Agent configuration
data/
└── {department}/       # RAG knowledge documents per department
```

---

## Running Tests

```bash
uv run pytest tests/ -v
```

---

## Deployment

### Docker (recommended for production)

```bash
# Build and start
docker compose -f docker-compose.prod.yml up -d --build

# Restart without rebuilding (e.g., after config/agents.yaml changes)
docker compose -f docker-compose.prod.yml restart api
```

The production compose file includes PostgreSQL, ChromaDB, Nginx, and Certbot for TLS.

### Environment Variables in Production

All variables from `.env` apply in production. Make sure to set:
- A strong `ADMIN_SECRET_KEY`
- `MCP_ENCRYPTION_KEY` (if using MCP servers) — **never change this after users have connected servers**, as it will make existing credentials unreadable
- `DATABASE_URL` pointing to your production PostgreSQL instance
- `MCP_DB_URL` pointing to a separate PostgreSQL database for MCP server records

---

## Common Errors

**`Could not import module src.app`**
```bash
uv pip install -e .
```

**`No module named X`**
```bash
uv add X && uv sync
```

**`ADMIN_SECRET_KEY is set to the default value`**
Generate a new key: `python -c "import secrets; print(secrets.token_urlsafe(32))"`

**`MCP_ENCRYPTION_KEY is not set`**
Generate: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`

**ChromaDB connection error on startup**
ChromaDB must be running. In development, either start it with Docker (`docker run -p 8000:8000 chromadb/chroma`) or set `CHROMA_HOST` and `CHROMA_PORT` in `.env`.

**PowerShell execution policy error**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```
