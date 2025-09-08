# Multi-stage build using official uv base image
FROM ghcr.io/astral-sh/uv:python3.11-bookworm as builder

# Install system dependencies for building
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Clone the repository
RUN git clone https://github.com/Data-Everything/elasticsearch-mcp-server.git .

# Install dependencies using uv with caching
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# Runtime stage - using same base as builder for consistency
FROM python:3.11-bookworm-slim as runtime

LABEL maintainer="Jason Matherly <jason@matherly.net>"
LABEL description="Open Elastic Search MCP Server - Custom implementation supporting both Elasticsearch and OpenSearch"
LABEL version="2.0.11"
LABEL elasticsearch.version="7.x-8.x-9.x"
LABEL opensearch.version="1.x-2.x-3.x"
LABEL origin="custom"
LABEL experimental="true"

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Copy application code and entrypoint
COPY --from=builder /app /app

# Copy our custom entrypoint script
COPY script.sh /usr/local/bin/open-elastic-search-entrypoint.sh

# Make the script executable
RUN chmod +x /usr/local/bin/open-elastic-search-entrypoint.sh

# Set environment defaults
ENV ENGINE_TYPE=elasticsearch
ENV MCP_TRANSPORT=stdio
ENV MCP_HOST=0.0.0.0
ENV MCP_PORT=8000
ENV MCP_PATH=/mcp
ENV ELASTICSEARCH_VERIFY_CERTS=false
ENV OPENSEARCH_VERIFY_CERTS=false

# Health check for HTTP-based transports
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD if [ "$MCP_TRANSPORT" = "sse" ] || [ "$MCP_TRANSPORT" = "streamable-http" ]; then \
    curl -f "http://${MCP_HOST}:${MCP_PORT}${MCP_PATH}" || exit 1; \
    else \
    echo "${MCP_TRANSPORT} mode - health check skipped"; \
    fi

# Use our custom entrypoint
ENTRYPOINT ["/usr/local/bin/open-elastic-search-entrypoint.sh"]
