#!/bin/sh

# Check MCP_Transport env variable, default to stdio
MCP_TRANSPORT="${MCP_TRANSPORT:-stdio}"
MCP_PORT="${MCP_PORT:-8080}"

if [ "$MCP_TRANSPORT" = "stdio" ]; then
    echo "Starting Trino MCP server with stdio transport" >&2
    /server/mcp-trino stdio
else
    echo "Starting Trino MCP server with HTTP transport on port $MCP_PORT" >&2
    /server/mcp-trino serve --http --port "$MCP_PORT" "$@"
fi