# Deployment Guide - Dartha API V3

Complete guide for deploying the Dartha API V3 to production environments. This guide covers all stages from prerequisites through maintenance and troubleshooting.

---

## 1. Overview

The Dartha API V3 is a multi-agent intelligent platform powered by various LLM providers (OpenAI, Anthropic, Google, Groq). This guide provides step-by-step instructions for:

- **Local Development**: Running on your machine
- **Staging Environment**: Pre-production testing
- **Production Deployment**: Live environment with proper scaling
- **Monitoring & Maintenance**: Operations in production

### Key Features
- Multi-LLM support (OpenAI, Anthropic, Google, Groq, OpenRouter)
- Agent-based architecture with customizable skills
- Knowledge base (RAG) support
- Memory management system
- Dynamic tool injection
- JWT/RBAC authorization (optional)
- Docker containerization support

---

## 2. Prerequisites

### System Requirements
- **Python**: 3.13 or higher
- **OS**: Windows, macOS, or Linux
- **CPU**: Minimum 2 cores (4+ recommended for production)
- **RAM**: Minimum 4GB (8GB+ recommended for production)
- **Disk Space**: 10GB+ available

### Required Tools

#### Windows
```powershell
# Install Python 3.13+
# From: https://www.python.org/downloads/

# Install uv package manager
irm https://astral.sh/uv/install.ps1 | iex

# Verify installations
python --version
uv --version
```

#### macOS / Linux
```bash
# Install Python 3.13+ (using homebrew on macOS)
brew install python@3.13

# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Verify installations
python3 --version
uv --version
```

### Required Accounts & API Keys
- **OpenAI API Key** (minimum required) - Get from https://platform.openai.com/api-keys
- **Alternative LLM Providers** (optional):
  - Anthropic API Key - https://console.anthropic.com/
  - Google API Key - https://cloud.google.com/
  - Groq API Key - https://console.groq.com/
  - OpenRouter API Key - https://openrouter.ai/

### Optional: Docker Setup
For containerized deployments:
```bash
# Install Docker
# From: https://www.docker.com/products/docker-desktop

# Verify installation
docker --version
docker-compose --version
```

---

## 3. Initial Setup Steps

### 3.1 Local Development Setup

#### Step 1: Clone the Repository
```bash
git clone https://github.com/dartha/dartha-api-v3
cd dartha-api-v3
```

#### Step 2: Create Environment Configuration
```bash
# Copy the example environment file
cp .env.example .env

# Edit .env with your API keys (open in your editor)
# Minimum required: OPENAI_API_KEY
# Example:
# OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxx
# LLM_PROVIDER=openai
# DEFAULT_MODEL_ID=gpt-4o-mini
```

#### Step 3: Create Python Virtual Environment
```bash
# Windows (PowerShell)
uv venv --python 3.13 .venv
.venv\Scripts\Activate.ps1

# macOS / Linux
uv venv --python 3.13 .venv
source .venv/bin/activate
```

#### Step 4: Install Dependencies
```bash
# Install all dependencies
uv sync

# Install package in editable mode
uv pip install -e .
```

#### Step 5: Start Development Server
```bash
# Windows
.\start.ps1

# macOS / Linux
python -m src.app
```

Server will be available at: **http://localhost:7777**

---

## 4. Configuration

### 4.1 Environment Variables

Create a `.env` file in the project root with the following variables:

```env
# =====================
# PROJECT IDENTITY
# =====================
PROJECT_NAME="Dartha API V3"
COMPANY_NAME="Your Company"
COMPANY_DESCRIPTION="Description of your company"

# =====================
# SERVER CONFIGURATION
# =====================
PORT=7777
AGENT_OS_PORT=7777
AGENT_OS_HOST=localhost

# =====================
# LLM CONFIGURATION
# =====================
# Options: openai, anthropic, google, groq, openrouter
LLM_PROVIDER="openai"
DEFAULT_MODEL_ID="gpt-4o-mini"

# =====================
# API KEYS
# =====================
OPENAI_API_KEY="sk-proj-xxxxxxxxxxxxx"
ANTHROPIC_API_KEY="sk-ant-xxxxxxxxxxxxx"
GOOGLE_API_KEY="AIzaxxxxxxxxxxxx"
GROQ_API_KEY="gsk_xxxxxxxxxxxxx"
OPENROUTER_API_KEY="sk-or-xxxxxxxxxxxxx"

# =====================
# DATABASE CONFIGURATION
# =====================
# Development (SQLite)
DATABASE_URL="sqlite:///agno.db"

# Production (PostgreSQL)
# DATABASE_URL="postgresql+psycopg://user:pass@host:5432/dbname"

# =====================
# NEO4J CONFIGURATION (optional)
# =====================
NEO4J_URI="bolt://localhost:7687"
NEO4J_USER="neo4j"
NEO4J_PASSWORD="password"

# =====================
# MCP CONFIGURATION
# =====================
MCP_SERVERS_JSON='["https://docs.agno.com/mcp"]'

# =====================
# JWT CONFIGURATION (for authentication)
# =====================
# JWT_SECRET_KEY="your-secret-key-here"
# JWT_ALGORITHM="HS256"
```

### 4.2 Agent Configuration

Configure agents in `config/agents.yaml`. Example structure:

```yaml
globals:
  company_name: "Your Company"
  company_description: "Company description"
  default_model: "gpt-4o-mini"

  default_features:
    memory: true
    rag: true
    web_search: false
    add_datetime: true
    add_history: true
    num_history_runs: 10
    markdown: true
    debug_mode: false

agents:
  - name: "General Assistant"
    department: "geral"
    model: "gpt-4o-mini"
    description: "General purpose assistant"

    features:
      memory: true
      rag: false
      web_search: true
      add_history: true

    tools:
      - name: "DuckDuckGoTools"
      - name: "SmartPandasTools"
      - name: "FileTools"

    instructions:
      - "You are the general assistant"
      - "Provide helpful and accurate responses"
```

See `config/agents.example.yaml` for complete examples.

### 4.3 Production Environment Variables

For production deployments, use these additional configurations:

```env
# Database with SSL/TLS
DATABASE_URL="postgresql+psycopg://user:pass@prod-host:5432/dartha?sslmode=require"

# Server
AGENT_OS_HOST="0.0.0.0"
PORT=8000

# Enable authentication
JWT_SECRET_KEY="your-secure-random-key-here"
JWT_ALGORITHM="HS256"

# Logging
DEBUG_MODE=false
LOG_LEVEL="INFO"
```

---

## 5. Testing & Verification

### 5.1 Local Testing

#### Test 1: API Health Check
```bash
curl http://localhost:7777/api/v1/health
```

Expected response: `{"status": "healthy"}`

#### Test 2: Swagger Documentation
Open in browser: `http://localhost:7777/docs`

You should see the full API documentation.

#### Test 3: Simple Agent Request
```bash
curl -X POST http://localhost:7777/v1/dynamic-run \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "test-user-1",
    "message": "Hello, how are you?",
    "session_id": "session-123"
  }'
```

#### Test 4: Use Agno UI
1. Visit https://os.agno.com
2. Click "Add Local OS"
3. Enter: `http://localhost:7777`
4. Select any agent and test conversation

### 5.2 Pre-Production Testing Checklist

Before deploying to production, verify:

- [ ] All environment variables are set correctly
- [ ] Database connectivity works
- [ ] All API keys are valid and have sufficient credits
- [ ] Memory and storage usage are within acceptable limits
- [ ] Response times are acceptable (< 5s for most queries)
- [ ] Error handling works correctly
- [ ] Logging is configured properly
- [ ] Authentication is enabled and working
- [ ] CORS is properly configured for your domain
- [ ] Rate limiting is in place

---

## 6. Production Deployment

### 6.1 Docker Deployment

#### Step 1: Create Dockerfile
If not present, create `Dockerfile` in project root:

```dockerfile
FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Copy project files
COPY . .

# Create virtual environment
RUN uv venv --python 3.13 .venv
RUN . .venv/bin/activate && uv sync && uv pip install -e .

# Expose port
EXPOSE 8000

# Start application
ENV PATH="/app/.venv/bin:$PATH"
CMD ["python", "-m", "uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "8000"]
```

#### Step 2: Build Docker Image
```bash
docker build -t dartha-api-v3:latest .
```

#### Step 3: Run Container
```bash
docker run -d \
  --name dartha-api \
  -p 8000:8000 \
  --env-file .env.prod \
  dartha-api-v3:latest
```

#### Step 4: Verify Running Container
```bash
docker logs dartha-api
curl http://localhost:8000/api/v1/health
```

### 6.2 Docker Compose with Services

For full stack deployment with ChromaDB:

```bash
# Start all services
docker-compose -f docker-compose.yml up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f dartha-api
```

The `docker-compose.yml` includes:
- **dartha-api**: Main application
- **chromadb**: Vector database for RAG (port 8000)

### 6.3 Cloud Deployment

#### AWS ECS
1. Push Docker image to ECR
2. Create ECS task definition
3. Create ECS service with load balancer
4. Configure RDS for PostgreSQL database
5. Set environment variables in task definition

#### Google Cloud Run
```bash
# Build and push image
gcloud builds submit --tag gcr.io/PROJECT-ID/dartha-api-v3

# Deploy
gcloud run deploy dartha-api \
  --image gcr.io/PROJECT-ID/dartha-api-v3 \
  --platform managed \
  --region us-central1 \
  --set-env-vars OPENAI_API_KEY=sk-xxx \
  --allow-unauthenticated
```

#### Heroku
```bash
# Create app
heroku create dartha-api

# Set environment variables
heroku config:set OPENAI_API_KEY=sk-xxx

# Deploy
git push heroku main

# View logs
heroku logs --tail
```

### 6.4 Reverse Proxy & SSL/TLS

#### Nginx Configuration Example
```nginx
server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;

    ssl_certificate /path/to/certificate.crt;
    ssl_certificate_key /path/to/key.key;

    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts for long-running requests
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}

server {
    listen 80;
    server_name api.yourdomain.com;
    return 301 https://$server_name$request_uri;
}
```

---

## 7. Maintenance & Updates

### 7.1 Regular Maintenance Tasks

#### Daily
- Monitor error logs
- Check API response times
- Verify database connectivity
- Monitor resource usage (CPU, RAM, disk)

#### Weekly
- Review and archive logs
- Check for available updates
- Backup database
- Verify backup restoration

#### Monthly
- Update dependencies: `uv sync`
- Review and optimize slow queries
- Audit API usage and costs
- Review security logs

### 7.2 Updating Dependencies

```bash
# Check for outdated packages
uv pip list --outdated

# Update all packages
uv sync --upgrade

# Update specific package
uv add package-name@latest

# Commit changes
git add pyproject.toml uv.lock
git commit -m "chore: update dependencies"
```

### 7.3 Database Backups

#### SQLite Backup
```bash
# Simple copy
cp agno.db agno.db.backup-$(date +%Y%m%d)

# Compressed backup
tar -czf backups/agno-$(date +%Y%m%d-%H%M%S).tar.gz agno.db
```

#### PostgreSQL Backup
```bash
# Full backup
pg_dump -U user -h host database_name > backup-$(date +%Y%m%d).sql

# Compressed backup
pg_dump -U user -h host database_name | gzip > backup-$(date +%Y%m%d).sql.gz

# Restore
psql -U user -h host database_name < backup-2024-03-30.sql
```

### 7.4 Scaling Considerations

#### Horizontal Scaling
- Use load balancer (nginx, HAProxy, or cloud provider)
- Deploy multiple API instances
- Ensure shared database
- Use Redis for session management

#### Vertical Scaling
- Increase CPU and RAM
- Optimize agent models (use faster models for common tasks)
- Cache frequently used responses
- Optimize database queries

### 7.5 Health Checks & Monitoring

#### Implement Health Check Endpoint
```bash
# Check API health
curl http://localhost:8000/api/v1/health

# Check database
curl http://localhost:8000/api/v1/health/db

# Check ChromaDB (if using RAG)
curl http://chromadb:8000/api/v1/heartbeat
```

---

## 8. Troubleshooting

### 8.1 Common Issues and Solutions

#### Issue: "ModuleNotFoundError: No module named 'src'"

**Solution:**
```bash
# Reinstall in editable mode
uv pip install -e .

# Or activate virtual environment and try again
.venv\Scripts\Activate.ps1  # Windows
source .venv/bin/activate    # macOS/Linux
```

#### Issue: "OPENAI_API_KEY not found"

**Solution:**
```bash
# Check .env file exists
cat .env  # macOS/Linux
type .env # Windows

# Add key if missing
echo "OPENAI_API_KEY=sk-proj-xxxxx" >> .env

# Restart server
```

#### Issue: "Address already in use (port 7777)"

**Solution:**
```bash
# Windows: Find and kill process on port 7777
netstat -ano | findstr :7777
taskkill /PID <PID> /F

# macOS/Linux: Kill process on port 7777
lsof -i :7777
kill -9 <PID>

# Or use different port
AGENT_OS_PORT=7778 python -m src.app
```

#### Issue: "Connection refused (ChromaDB)"

**Solution:**
```bash
# Make sure ChromaDB container is running
docker-compose ps

# Start ChromaDB if not running
docker-compose up -d chromadb

# Check ChromaDB health
curl http://localhost:8000/api/v1/heartbeat
```

#### Issue: "Out of memory" errors

**Solution:**
- Reduce model size (use gpt-4o-mini instead of gpt-4o)
- Enable memory cleanup: set appropriate `num_history_runs`
- Increase container/server RAM
- Use database connection pooling
- Monitor and profile memory usage

#### Issue: "Slow API responses"

**Solution:**
```bash
# Enable debug logging
DEBUG_MODE=true

# Check logs for bottlenecks
tail -f app.log

# Reduce RAG context size
# Optimize database indexes
# Use faster models for non-critical tasks
# Enable response caching
```

### 8.2 Performance Troubleshooting

#### Check Resource Usage
```bash
# Memory usage
free -h  # Linux
ps aux | grep python  # All systems

# Disk space
df -h    # Linux/macOS
dir     # Windows

# CPU usage
top     # Linux/macOS
tasklist # Windows
```

#### Enable Detailed Logging
Edit `.env`:
```env
DEBUG_MODE=true
LOG_LEVEL="DEBUG"
```

#### Database Query Optimization
```bash
# For PostgreSQL, check slow queries
SELECT * FROM pg_stat_statements ORDER BY mean_time DESC LIMIT 10;

# Add indexes for frequently queried columns
CREATE INDEX idx_user_id ON runs(user_id);
```

### 8.3 Security Issues

#### Issue: "Unauthorized API access"

**Solution:**
```env
# Enable JWT authentication
JWT_SECRET_KEY="your-secure-key-here"
JWT_ALGORITHM="HS256"

# Add authorization to agents in app.py
# authorization=True
```

#### Issue: "API rate limiting needed"

**Solution:**
- Implement API gateway (Kong, Traefik)
- Use FastAPI middleware for rate limiting
- Set up CloudFlare rate limiting
- Implement request throttling

#### Issue: "CORS errors"

**Solution:**
Configure CORS in application:
```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 8.4 Getting Help

If issues persist:

1. **Check Documentation**
   - Agno docs: https://docs.agno.com
   - FastAPI docs: https://fastapi.tiangolo.com
   - Agent framework docs: Check project README

2. **Review Logs**
   ```bash
   # Application logs
   tail -f src/logs/app.log

   # Docker logs
   docker logs dartha-api

   # System logs
   journalctl -u dartha-api  # Linux
   ```

3. **Enable Debug Mode**
   ```env
   DEBUG_MODE=true
   LOG_LEVEL="DEBUG"
   ```

4. **Test Components Individually**
   - Test LLM API connection
   - Test database connection
   - Test ChromaDB connection
   - Test each agent independently

---

## Appendix A: File Structure

```
dartha-api-v3/
├── src/
│   ├── app.py                 # Main application entry point
│   ├── agents/                # Agent definitions
│   │   ├── _factory.py       # Agent loader
│   │   └── general_assistant.py
│   ├── config/                # Configuration modules
│   ├── knowledge/             # Knowledge base (RAG)
│   ├── memory/                # Memory management
│   ├── middleware/            # HTTP middleware
│   ├── skills/                # Agent skills
│   ├── tools/                 # Agent tools
│   └── utils/                 # Utility functions
├── config/
│   ├── agents.yaml           # Agent configuration
│   ├── company.yaml          # Company settings
│   └── agents.example.yaml   # Configuration template
├── docs/
│   ├── deployment-guide.md   # This file
│   ├── quickstart.md         # Quick start guide
│   └── agent-creation-guide.md
├── docker-compose.yml        # Docker services
├── Dockerfile               # Container definition
├── .env.example             # Environment template
├── README.md                # Project README
└── pyproject.toml          # Python project metadata
```

---

## Appendix B: Useful Commands

```bash
# Development
python -m src.app                    # Start dev server
uv sync                              # Install dependencies
uv add package-name                  # Add new package

# Docker
docker-compose up -d                 # Start services
docker-compose down                  # Stop services
docker logs -f dartha-api            # View container logs

# Database
pg_dump -U user dbname > backup.sql  # PostgreSQL backup
sqlite3 agno.db ".backup backup.db"  # SQLite backup

# Testing
curl http://localhost:7777/docs      # View API docs
curl http://localhost:7777/api/v1/health  # Health check

# Monitoring
ps aux | grep python                 # List Python processes
lsof -i :7777                       # Check port usage
free -h                             # Check memory (Linux)
```

---

## Appendix C: Support & Resources

- **Official Documentation**: https://docs.agno.com
- **FastAPI Documentation**: https://fastapi.tiangolo.com
- **Docker Documentation**: https://docs.docker.com
- **PostgreSQL Documentation**: https://www.postgresql.org/docs/
- **LLM Provider Documentation**:
  - OpenAI: https://platform.openai.com/docs
  - Anthropic: https://docs.anthropic.com
  - Google: https://cloud.google.com/docs
  - Groq: https://console.groq.com/docs

---

**Last Updated**: 2026-03-30
**Version**: 1.0
**Status**: Production Ready
