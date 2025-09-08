# Multi-stage build using official uv base image
FROM ghcr.io/astral-sh/uv:python3.11-bookworm as builder

WORKDIR /app
COPY pyproject.toml uv.lock ./

# Install dependencies with caching
RUN --mount=type=cache,target=/root/.cache/uv \
  uv sync --frozen --no-dev --no-install-project

# Runtime stage - using same base as builder for consistency
FROM python:3.11-bookworm-slim as runtime

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

LABEL maintainer="Jason Matherly <jason@matherly.net>"
LABEL description="Demo MCP Server using FastMCP"
LABEL version="1.0.0"

WORKDIR /app

# Copy demo template source code
COPY . .

# Create non-root user
RUN useradd --create-home --shell /bin/bash mcp
RUN chown -R mcp:mcp /app
USER mcp

ENV MCP_PORT=7071

# Expose the default HTTP port
EXPOSE ${MCP_PORT}

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD \
  python -c "import sys, urllib.request; \
  sys.exit(0) if urllib.request.urlopen('http://127.0.0.1:${MCP_PORT}/health').getcode() == 200 else sys.exit(1)"

# Set environment variables
ENV MCP_LOG_LEVEL=info
ENV MCP_HELLO_FROM="MCP Platform"

RUN chmod +x script.sh

# Default command
ENTRYPOINT ["/app/script.sh"]
