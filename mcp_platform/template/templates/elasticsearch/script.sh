#!/bin/sh

# Custom entrypoint script for Elasticsearch MCP Server
# This script handles stdio transport and passes arguments correctly to the official entrypoint

# Check MCP_Transport env variable, default to stdio
MCP_TRANSPORT="${MCP_TRANSPORT:-stdio}"
MCP_PORT="${MCP_PORT:-8080}"

# Validate required environment variables
if [ -z "$ES_URL" ]; then
    echo "Error: ES_URL environment variable is required" >&2
    exit 1
fi

# Check authentication - either API key or username/password
if [ -z "$ES_API_KEY" ] && [ -z "$ES_USERNAME" ]; then
    echo "Error: Either ES_API_KEY or ES_USERNAME/ES_PASSWORD must be provided for authentication" >&2
    exit 1
fi

if [ -n "$ES_USERNAME" ] && [ -z "$ES_PASSWORD" ]; then
    echo "Error: ES_PASSWORD is required when ES_USERNAME is provided" >&2
    exit 1
fi

# Display startup information
echo "Starting Elasticsearch MCP Server..." >&2
echo "Transport: $MCP_TRANSPORT" >&2
echo "Elasticsearch URL: $ES_URL" >&2

if [ -n "$ES_API_KEY" ]; then
    echo "Authentication: API Key" >&2
else
    echo "Authentication: Username/Password ($ES_USERNAME)" >&2
fi

if [ "$ES_SSL_SKIP_VERIFY" = "true" ]; then
    echo "SSL Verification: DISABLED" >&2
fi

echo "⚠️  WARNING: This MCP server is EXPERIMENTAL" >&2

# Start the server based on transport mode
if [ "$MCP_TRANSPORT" = "stdio" ]; then
    echo "Starting MCP server with stdio transport" >&2
    exec /usr/local/bin/elasticsearch-core-mcp-server stdio
elif [ "$MCP_TRANSPORT" = "http" ]; then
    echo "Starting MCP server with HTTP transport on port $MCP_PORT" >&2
    exec /usr/local/bin/elasticsearch-core-mcp-server http --port "$MCP_PORT" "$@"
else
    echo "Error: Unsupported transport mode: $MCP_TRANSPORT" >&2
    echo "Supported modes: stdio, http" >&2
    exit 1
fi