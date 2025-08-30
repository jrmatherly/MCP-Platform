FROM python:3.12-slim

LABEL org.opencontainers.image.title="Slack MCP Server"
LABEL org.opencontainers.image.description="Enhanced Slack MCP server for comprehensive workspace integration"
LABEL org.opencontainers.image.version="1.0.0"
LABEL org.opencontainers.image.authors="Data Everything (extends korotovsky/slack-mcp-server)"
LABEL org.opencontainers.image.source="https://github.com/Data-Everything/MCP-Platform"
LABEL org.opencontainers.image.documentation="https://github.com/Data-Everything/MCP-Platform/tree/main/mcp_platform/template/templates/slack"

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install the slack-mcp-server directly from GitHub
RUN pip install git+https://github.com/korotovsky/slack-mcp-server.git

# Create necessary directories
RUN mkdir -p /app/logs /app/config /app/cache

# Set environment variables with defaults
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV MCP_TRANSPORT=stdio
ENV MCP_PORT=3003
ENV LOG_LEVEL=INFO
ENV CACHE_ENABLED=true
ENV CACHE_TTL=3600
ENV EMBED_USER_INFO=true
ENV MAX_HISTORY_LIMIT=30d
ENV READ_ONLY_MODE=false
ENV ENABLE_MESSAGE_POSTING=false
ENV STEALTH_MODE=false

# Expose the default port
EXPOSE 3003

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:3003/health')" || exit 1

# Default command - start the slack MCP server
# The slack-mcp-server package should provide an entry point
CMD ["python", "-m", "slack_mcp_server"]