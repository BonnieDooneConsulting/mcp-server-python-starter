# syntax=docker/dockerfile:1

# ---- build: resolve and install dependencies with uv ----
FROM python:3.15-slim AS builder
COPY --from=ghcr.io/astral-sh/uv:0.13.6 /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Dependencies first, so this layer stays cached until the lockfile changes.
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

COPY README.md LICENSE ./
COPY src ./src
RUN uv sync --locked --no-dev --no-editable

# ---- runtime: just the virtualenv, running as a non-root user ----
FROM python:3.15-slim

RUN groupadd --system app && useradd --system --gid app --no-create-home app

COPY --from=builder --chown=app:app /app/.venv /app/.venv

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    MCP_STARTER_TRANSPORT=streamable-http \
    MCP_STARTER_HOST=0.0.0.0 \
    MCP_STARTER_PORT=8000

USER app
EXPOSE 8000

ENTRYPOINT ["mcp-starter"]
