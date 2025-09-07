# Multi-stage build for production-ready MCP Platform Gateway
# Using official uv base image for efficient Python dependency management

# Stage 1: Build environment with official uv base image
FROM ghcr.io/astral-sh/uv:python3.11-bookworm as builder

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies using uv with caching
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Stage 2: Production runtime - using consistent base
FROM python:3.11-bookworm-slim as runtime

# Create non-root user for security
RUN groupadd -r mcpgateway && useradd -r -g mcpgateway mcpgateway

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    dumb-init \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Set working directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv

# Copy application code
COPY mcp_platform/ ./mcp_platform/

# Create data directory for SQLite database
RUN mkdir -p /app/data && chown -R mcpgateway:mcpgateway /app/data

# Create directory for registry fallback
RUN mkdir -p /app/registry && chown -R mcpgateway:mcpgateway /app/registry

# Set ownership of application files
RUN chown -R mcpgateway:mcpgateway /app

# Switch to non-root user
USER mcpgateway

# Set environment variables
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    GATEWAY_HOST=0.0.0.0 \
    GATEWAY_PORT=8080 \
    GATEWAY_DATABASE_URL="sqlite:///data/gateway.db" \
    GATEWAY_REGISTRY_FILE="/app/registry/registry.json" \
    GATEWAY_LOG_LEVEL=INFO \
    GATEWAY_WORKERS=1

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8080/gateway/health || exit 1

# Expose port
EXPOSE 8080

# Use dumb-init as PID 1 for proper signal handling
ENTRYPOINT ["dumb-init", "--"]

# Default command to run the gateway
CMD ["python", "-m", "mcp_platform.gateway.cli", "start", \
    "--host", "0.0.0.0", \
    "--port", "8080", \
    "--database", "sqlite:///data/gateway.db", \
    "--registry", "/app/registry/registry.json", \
    "--log-level", "INFO"]