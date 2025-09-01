FROM docker.elastic.co/mcp/elasticsearch:0.4.5

LABEL maintainer="Data Everything <tooling@dataeverything.com>"
LABEL description="Elasticsearch MCP Server - EXPERIMENTAL"
LABEL version="1.0.0"
LABEL elasticsearch.version="8.x-9.x"
LABEL origin="external"
LABEL experimental="true"

# Copy our custom entrypoint script
COPY script.sh /usr/local/bin/elasticsearch-mcp-entrypoint.sh

# Make the script executable
RUN chmod +x /usr/local/bin/elasticsearch-mcp-entrypoint.sh

# Set environment defaults
ENV MCP_TRANSPORT=stdio
ENV MCP_PORT=8080
ENV LOG_LEVEL=INFO

# Health check for HTTP mode
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD if [ "$MCP_TRANSPORT" = "http" ]; then \
            curl -f "http://localhost:${MCP_PORT}/ping" || exit 1; \
        else \
            echo "stdio mode - health check skipped"; \
        fi

# Use our custom entrypoint
ENTRYPOINT ["/usr/local/bin/elasticsearch-mcp-entrypoint.sh"]