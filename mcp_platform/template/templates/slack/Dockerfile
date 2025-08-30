FROM ghcr.io/korotovsky/slack-mcp-server:v1.1.24

LABEL org.opencontainers.image.title="Slack MCP Server"
LABEL org.opencontainers.image.description="Enhanced Slack MCP server for comprehensive workspace integration"
LABEL org.opencontainers.image.version="1.0.0"
LABEL org.opencontainers.image.authors="Data Everything (extends korotovsky/slack-mcp-server)"
LABEL org.opencontainers.image.source="https://github.com/Data-Everything/MCP-Platform"
LABEL org.opencontainers.image.documentation="https://github.com/Data-Everything/MCP-Platform/tree/main/mcp_platform/template/templates/slack"

# Set working directory
WORKDIR /app

# Create necessary directories for caching and logs
RUN mkdir -p /app/logs /app/config /app/cache

# Set environment variables with defaults matching korotovsky/slack-mcp-server
ENV SLACK_MCP_PORT=3003
ENV SLACK_MCP_HOST=127.0.0.1
ENV SLACK_MCP_LOG_LEVEL=info
ENV SLACK_MCP_USERS_CACHE=/app/cache/.users_cache.json
ENV SLACK_MCP_CHANNELS_CACHE=/app/cache/.channels_cache_v2.json

# Expose the default port
EXPOSE 3003

# Default command - use the original entrypoint but with stdio transport
CMD ["mcp-server", "--transport", "stdio"]