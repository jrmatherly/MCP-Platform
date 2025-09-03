#!/bin/sh

# Custom entrypoint script for Open Elastic Search MCP Server
# This script handles both Elasticsearch and OpenSearch connections with multiple transport modes

# Set defaults
ENGINE_TYPE="${ENGINE_TYPE:-elasticsearch}"
MCP_TRANSPORT="${MCP_TRANSPORT:-stdio}"
MCP_HOST="${MCP_HOST:-0.0.0.0}"
MCP_PORT="${MCP_PORT:-8000}"
MCP_PATH="${MCP_PATH:-/mcp}"

# Display startup information
echo "Starting Open Elastic Search MCP Server..." >&2
echo "Engine Type: $ENGINE_TYPE" >&2
echo "Transport: $MCP_TRANSPORT" >&2

# Validate configuration based on engine type
if [ "$ENGINE_TYPE" = "elasticsearch" ]; then
    if [ -z "$ELASTICSEARCH_HOSTS" ]; then
        echo "Error: ELASTICSEARCH_HOSTS environment variable is required for Elasticsearch" >&2
        exit 1
    fi
    
    # Check authentication for Elasticsearch
    if [ -z "$ELASTICSEARCH_API_KEY" ] && [ -z "$ELASTICSEARCH_USERNAME" ]; then
        echo "Error: Either ELASTICSEARCH_API_KEY or ELASTICSEARCH_USERNAME/ELASTICSEARCH_PASSWORD must be provided for Elasticsearch authentication" >&2
        exit 1
    fi
    
    if [ -n "$ELASTICSEARCH_USERNAME" ] && [ -z "$ELASTICSEARCH_PASSWORD" ]; then
        echo "Error: ELASTICSEARCH_PASSWORD is required when ELASTICSEARCH_USERNAME is provided" >&2
        exit 1
    fi
    
    echo "Elasticsearch Hosts: $ELASTICSEARCH_HOSTS" >&2
    if [ -n "$ELASTICSEARCH_API_KEY" ]; then
        echo "Authentication: API Key" >&2
    else
        echo "Authentication: Username/Password ($ELASTICSEARCH_USERNAME)" >&2
    fi
    
    if [ "$ELASTICSEARCH_VERIFY_CERTS" = "false" ]; then
        echo "SSL Verification: DISABLED" >&2
    fi
    
    SERVER_COMMAND="elasticsearch-mcp-server"
    
elif [ "$ENGINE_TYPE" = "opensearch" ]; then
    if [ -z "$OPENSEARCH_HOSTS" ]; then
        echo "Error: OPENSEARCH_HOSTS environment variable is required for OpenSearch" >&2
        exit 1
    fi
    
    # Check authentication for OpenSearch
    if [ -z "$OPENSEARCH_USERNAME" ] || [ -z "$OPENSEARCH_PASSWORD" ]; then
        echo "Error: OPENSEARCH_USERNAME and OPENSEARCH_PASSWORD must be provided for OpenSearch authentication" >&2
        exit 1
    fi
    
    echo "OpenSearch Hosts: $OPENSEARCH_HOSTS" >&2
    echo "Authentication: Username/Password ($OPENSEARCH_USERNAME)" >&2
    
    if [ "$OPENSEARCH_VERIFY_CERTS" = "false" ]; then
        echo "SSL Verification: DISABLED" >&2
    fi
    
    SERVER_COMMAND="opensearch-mcp-server"
    
else
    echo "Error: Unsupported ENGINE_TYPE: $ENGINE_TYPE" >&2
    echo "Supported types: elasticsearch, opensearch" >&2
    exit 1
fi

echo "⚠️  WARNING: This MCP server is EXPERIMENTAL and supports both Elasticsearch and OpenSearch" >&2

# Start the server based on transport mode
if [ "$MCP_TRANSPORT" = "stdio" ]; then
    echo "Starting MCP server with stdio transport" >&2
    exec $SERVER_COMMAND
elif [ "$MCP_TRANSPORT" = "sse" ]; then
    echo "Starting MCP server with SSE transport on ${MCP_HOST}:${MCP_PORT}${MCP_PATH}" >&2
    exec $SERVER_COMMAND --transport sse --host "$MCP_HOST" --port "$MCP_PORT" --path "$MCP_PATH" "$@"
elif [ "$MCP_TRANSPORT" = "streamable-http" ]; then
    echo "Starting MCP server with Streamable HTTP transport on ${MCP_HOST}:${MCP_PORT}${MCP_PATH}" >&2
    exec $SERVER_COMMAND --transport streamable-http --host "$MCP_HOST" --port "$MCP_PORT" --path "$MCP_PATH" "$@"
else
    echo "Error: Unsupported transport mode: $MCP_TRANSPORT" >&2
    echo "Supported modes: stdio, sse, streamable-http" >&2
    exit 1
fi