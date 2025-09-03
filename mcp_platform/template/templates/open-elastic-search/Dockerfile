FROM python:3.11-slim

LABEL maintainer="Data Everything <tooling@dataeverything.com>"
LABEL description="Open Elastic Search MCP Server - Custom implementation supporting both Elasticsearch and OpenSearch"
LABEL version="2.0.11"
LABEL elasticsearch.version="7.x-8.x-9.x"
LABEL opensearch.version="1.x-2.x-3.x"
LABEL origin="custom"
LABEL experimental="true"

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv (ultrafast Python package installer and resolver)
RUN pip install uv

# Set working directory
WORKDIR /app

# Clone the elasticsearch-mcp-server repository
RUN git clone https://github.com/Data-Everything/elasticsearch-mcp-server.git .

# Install dependencies using uv
RUN uv pip install --system -e .

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
