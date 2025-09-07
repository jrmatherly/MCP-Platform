# Multi-stage build using official uv base image
FROM ghcr.io/astral-sh/uv:python3.11-bookworm as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

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

WORKDIR /app

# Copy source code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 mcpuser && chown -R mcpuser:mcpuser /app
USER mcpuser

# Default environment variables
ENV TRINO_HOST="trino" \
    TRINO_PORT="8080" \
    TRINO_USER="admin" \
    TRINO_SCHEME="https" \
    TRINO_SSL="true" \
    TRINO_SSL_INSECURE="true" \
    TRINO_ALLOW_WRITE_QUERIES="false" \
    TRINO_QUERY_TIMEOUT="300" \
    TRINO_MAX_RESULTS="1000" \
    MCP_TRANSPORT="http" \
    MCP_HOST="0.0.0.0" \
    MCP_PORT="7090"

# Expose the port
EXPOSE 7090

# Run the server
CMD ["python", "-m", "server"]
