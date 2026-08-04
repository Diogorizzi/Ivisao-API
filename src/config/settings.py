from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional
import json

class Settings(BaseSettings):
    # Project Identity
    PROJECT_NAME: str = "Dartha API V3"
    COMPANY_NAME: str = "Minha Empresa"
    COMPANY_DESCRIPTION: str = "Uma empresa focada em soluções inteligentes com agentes AI."

    # Server Configuration
    HOST: str = "0.0.0.0"  # "0.0.0.0" aceita conexões de outros computadores da rede local; "localhost" restringe só a esta máquina
    PORT: int = 7777
    ENVIRONMENT: str = "production"  # "production" desabilita /docs e /redoc; "development" habilita

    # LLM Configuration
    LLM_PROVIDER: str = "openai"  # openai, anthropic, google, groq, openrouter
    DEFAULT_MODEL_ID: str = "gpt-4o-mini"
    
    # API Keys
    OPENAI_API_KEY: Optional[str] = None
    ANTHROPIC_API_KEY: Optional[str] = None
    GOOGLE_API_KEY: Optional[str] = None
    GROQ_API_KEY: Optional[str] = None
    OPENROUTER_API_KEY: Optional[str] = None

    # AWS Bedrock — project-prefixed vars take priority over SDK standard vars
    BEDROCK_AWS_ACCESS_KEY_ID: Optional[str] = None
    BEDROCK_AWS_SECRET_ACCESS_KEY: Optional[str] = None
    BEDROCK_AWS_REGION: Optional[str] = None

    # Google Vertex AI — project-prefixed vars take priority over SDK standard vars
    VERTEX_PROJECT_ID: Optional[str] = None
    VERTEX_LOCATION: str = "us-east5"
    VERTEX_CREDENTIALS_FILE: Optional[str] = None

    # Database Configuration
    DATABASE_URL: str = "sqlite:///agno.db"  # sqlite:///agno.db or postgresql+psycopg://user:pass@host/db
    
    # Neo4j Configuration
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "password"

    # MCP Servers — separate Neon DB + encryption key
    MCP_DB_URL: Optional[str] = None  # postgresql+psycopg://...
    MCP_ENCRYPTION_KEY: Optional[str] = None  # Fernet key (base64, 32 bytes)

    # Nango OAuth-as-a-service
    NANGO_SECRET_KEY: Optional[str] = None
    NANGO_PUBLIC_KEY: Optional[str] = None

    # MCP Configuration
    # Example: ["https://docs.agno.com/mcp", "http://localhost:8080/mcp"]
    MCP_SERVERS_JSON: str = "[]"

    # Admin Panel
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD_HASH: str = ""
    ADMIN_SECRET_KEY: str = "change-me-in-production-32chars!!"
    ADMIN_SESSION_TTL: int = 28800

    # Bearer token for /v1/* endpoints — must match agno_auth_token stored in
    # the Next.js origins table. Leave empty to disable the endpoint entirely.
    API_SECRET_KEY: Optional[str] = None

    # CORS: comma-separated list of allowed origins.
    # Example: "https://app.liderandocomia.com,https://admin.liderandocomia.com"
    # Leave empty to block all browser cross-origin requests.
    CORS_ALLOWED_ORIGINS: str = ""

    # Maximum file size (MB) accepted by the admin upload endpoint.
    MAX_UPLOAD_MB: int = 50

    @property
    def MCP_SERVERS(self) -> List[str]:
        try:
            return json.loads(self.MCP_SERVERS_JSON)
        except:
            return []

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()

# Sincroniza com as variáveis de ambiente do sistema para ferramentas do Agno que buscam diretamente no os.environ
import os
# API Keys
if settings.OPENAI_API_KEY:
    os.environ["OPENAI_API_KEY"] = settings.OPENAI_API_KEY
if settings.ANTHROPIC_API_KEY:
    os.environ["ANTHROPIC_API_KEY"] = settings.ANTHROPIC_API_KEY
if settings.GOOGLE_API_KEY:
    os.environ["GOOGLE_API_KEY"] = settings.GOOGLE_API_KEY
if settings.GROQ_API_KEY:
    os.environ["GROQ_API_KEY"] = settings.GROQ_API_KEY
if settings.OPENROUTER_API_KEY:
    os.environ["OPENROUTER_API_KEY"] = settings.OPENROUTER_API_KEY
if settings.BEDROCK_AWS_ACCESS_KEY_ID:
    os.environ["BEDROCK_AWS_ACCESS_KEY_ID"] = settings.BEDROCK_AWS_ACCESS_KEY_ID
if settings.BEDROCK_AWS_SECRET_ACCESS_KEY:
    os.environ["BEDROCK_AWS_SECRET_ACCESS_KEY"] = settings.BEDROCK_AWS_SECRET_ACCESS_KEY
if settings.BEDROCK_AWS_REGION:
    os.environ["BEDROCK_AWS_REGION"] = settings.BEDROCK_AWS_REGION
if settings.VERTEX_PROJECT_ID:
    os.environ["VERTEX_PROJECT_ID"] = settings.VERTEX_PROJECT_ID
if settings.VERTEX_LOCATION:
    os.environ["VERTEX_LOCATION"] = settings.VERTEX_LOCATION
if settings.VERTEX_CREDENTIALS_FILE:
    os.environ["VERTEX_CREDENTIALS_FILE"] = settings.VERTEX_CREDENTIALS_FILE
# Server port: Agno's serve() reads AGENT_OS_PORT via os.getenv()
os.environ["AGENT_OS_PORT"] = str(settings.PORT)
# Admin panel vars (lidos por src/admin/auth.py via os.getenv)
os.environ["ADMIN_USERNAME"] = settings.ADMIN_USERNAME
os.environ["ADMIN_PASSWORD_HASH"] = settings.ADMIN_PASSWORD_HASH
os.environ["ADMIN_SECRET_KEY"] = settings.ADMIN_SECRET_KEY
os.environ["ADMIN_SESSION_TTL"] = str(settings.ADMIN_SESSION_TTL)
if settings.API_SECRET_KEY:
    os.environ["API_SECRET_KEY"] = settings.API_SECRET_KEY

