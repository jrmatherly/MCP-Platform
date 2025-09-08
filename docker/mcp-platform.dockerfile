# MCP Platform CLI Container
# Multi-stage build using official uv base image for efficient dependency management

# Stage 1: Builder with dependencies
FROM ghcr.io/astral-sh/uv:python3.11-alpine as builder

WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install dependencies with caching
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Stage 2: Runtime with Podman for container management
FROM mgoltzsche/podman:5.5.2 as runtime

# Metadata
LABEL maintainer="Jason Matherly <jason@matherly.net>"
LABEL tool="mcp-platform"
LABEL tool-shorthand="mcpp"
LABEL backend="docker"
LABEL description="MCP Platform for rapid deployment and management of AI servers with Docker, Kubernetes, or Mock backends."

# Install Python and cleanup to keep image size small
RUN apk add --no-cache \
    python3 \
    py3-pip \
    curl \
    && rm -rf /var/cache/apk/* \
    && ln -sf python3 /usr/bin/python

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy application code (excluding templates which are handled separately)
COPY mcp_platform /app/mcp_platform
COPY pyproject.toml /app/
COPY README.md /app/

# Create non-root user for security
RUN adduser -D -s /bin/sh mcp && \
    mkdir -p /data /config && \
    chown -R mcp:mcp /app /data /config

# Switch to non-root user
USER mcp

# Environment variables
ENV PYTHONPATH="/app" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    MCP_DATA_DIR="/data" \
    MCP_CONFIG_DIR="/config" \
    MCP_LOG_LEVEL="INFO"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD mcpp list || exit 1

# Expose common ports (can be overridden)
EXPOSE 7071

# Set the entrypoint to the CLI tool
ENTRYPOINT ["mcpp"]

# Default command shows help
CMD ["--help"]