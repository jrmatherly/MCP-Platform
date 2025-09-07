# Multi-stage build using official uv base image
FROM ghcr.io/astral-sh/uv:python3.11-bookworm as builder

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install system dependencies if needed for building
#RUN apt-get update && apt-get install -y \
#    --no-install-recommends \
#    gcc \
#    g++ \
#    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml uv.lock ./

# Install dependencies with caching
RUN --mount=type=cache,target=/root/.cache/uv \
  uv sync --frozen --no-dev --no-install-project

# Runtime stage - using same base as builder for consistency
FROM python:3.11-bookworm-slim as runtime

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Create non-root user for security
RUN groupadd -r mcpuser && useradd -r -g mcpuser mcpuser

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Copy application code
COPY . .

# Create directories for credentials and data
RUN mkdir -p /app/credentials /app/data && \
  chown -R mcpuser:mcpuser /app

# Switch to non-root user
USER mcpuser

# Expose the default port
EXPOSE 7090

# Health check
HEALTHCHECK --interval=30s --timeout=5s --retries=3 CMD \
  python -c "import sys, urllib.request; \
  sys.exit(0) if urllib.request.urlopen('http://127.0.0.1:7090/health').getcode() == 200 else sys.exit(1)"


# Default command - can be overridden
CMD ["python", "server.py"]

# Labels for metadata
LABEL maintainer="Data Everything <tooling@dataeverything.com>"
LABEL description="Production-ready BigQuery MCP server with secure authentication and access controls"
LABEL version="1.0.0"
LABEL org.opencontainers.image.title="BigQuery MCP Server"
LABEL org.opencontainers.image.description="Secure BigQuery MCP server for dataset querying and exploration"
LABEL org.opencontainers.image.vendor="Data Everything"
LABEL org.opencontainers.image.source="https://github.com/jrmatherly/MCP-Platform"
LABEL org.opencontainers.image.documentation="https://data-everything.github.io/MCP-Platform"
