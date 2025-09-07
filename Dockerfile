# Multi-stage build using official uv base image
FROM ghcr.io/astral-sh/uv:python3.11-alpine as builder

WORKDIR /app
COPY pyproject.toml uv.lock ./

# Install dependencies with caching
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Runtime stage
FROM mgoltzsche/podman:5.5.2 as runtime

LABEL maintainer="dataeverything"
LABEL tool="mcp-platform"
LABEL tool-shorthand="mcpp"
LABEL backend="docker"
LABEL description="MCP Platform for rapid deployment and management of AI servers with Docker, Kubernetes, or Mock backends."
LABEL original-backend="podman"

# Install Python and cleanup to keep image size small
RUN apk add --no-cache python3 && \
    rm -rf /var/cache/apk/* && \
    ln -sf python3 /usr/bin/python

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

WORKDIR /app
COPY mcp_platform /app/mcp_platform
COPY pyproject.toml /app/
COPY README.md /app/

# Set the entrypoint to the CLI tool
ENTRYPOINT ["mcpp"]
