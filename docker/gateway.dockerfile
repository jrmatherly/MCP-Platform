# MCP Platform Gateway Container
# Multi-stage build for production-ready MCP Platform Gateway
#
# CONFIGURATION APPROACH:
# - Environment variables provide fallback defaults for standalone usage
# - docker-compose.yml environment section overrides Dockerfile ENV values
# - .env file variables are loaded by docker-compose and override defaults
# - No hardcoded CLI arguments to ensure environment variable precedence works
#
# DEPLOYMENT MODES:
# - Standalone: Uses SQLite database and single worker (development/testing)
# - Docker Compose: Uses PostgreSQL database and multiple workers (production)
#
# ENVIRONMENT VARIABLE PRECEDENCE (highest to lowest):
# 1. docker-compose environment section
# 2. .env file (loaded by docker-compose)
# 3. Dockerfile ENV instruction (fallback defaults)

# Stage 1: Build environment with official uv base image
FROM ghcr.io/astral-sh/uv:python3.11-bookworm as builder

# Install system dependencies for building
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

# Stage 2: Production runtime
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

# Create required directories with proper permissions
RUN mkdir -p /app/data /app/registry /app/logs && \
    chown -R mcpgateway:mcpgateway /app

# Switch to non-root user
USER mcpgateway

# Set environment variables with fallback defaults for standalone usage
# These can be overridden by docker-compose.yml environment section or .env file
# Note: SECRET_KEY and ADMIN_PASSWORD should be provided via docker-compose for security
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    GATEWAY_HOST=0.0.0.0 \
    GATEWAY_PORT=8080 \
    GATEWAY_DATABASE_URL="sqlite:///data/gateway.db" \
    GATEWAY_REGISTRY_FILE="/app/registry/registry.json" \
    GATEWAY_LOG_LEVEL=INFO \
    GATEWAY_WORKERS=2 \
    GATEWAY_CORS_ORIGINS="*"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8080/gateway/health || exit 1

# Expose port
EXPOSE 8080

# Use dumb-init as PID 1 for proper signal handling
ENTRYPOINT ["dumb-init", "--"]

# Default command - CLI reads configuration from environment variables
# No hardcoded arguments to ensure docker-compose/env file overrides work properly
# The gateway CLI will use GATEWAY_* environment variables for configuration
CMD ["python", "-m", "mcp_platform.gateway.cli", "start"]