FROM python:3.13-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Install dependencies first (cached layer)
COPY pyproject.toml uv.lock README.md ./
RUN uv sync --frozen --no-dev

# Copy source
COPY src/ ./src/
COPY config/ ./config/

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app"

EXPOSE 7777

CMD ["uvicorn", "src.app:app", "--host", "0.0.0.0", "--port", "7777"]
