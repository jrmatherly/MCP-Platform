#!/bin/bash

# Slack MCP Server Startup Script
# This script configures and starts the slack-mcp-server with appropriate settings

set -e

# Default values
: ${MCP_TRANSPORT:="stdio"}
: ${MCP_PORT:="3003"}
: ${LOG_LEVEL:="INFO"}
: ${CACHE_ENABLED:="true"}
: ${CACHE_TTL:="3600"}
: ${MAX_HISTORY_LIMIT:="30d"}
: ${READ_ONLY_MODE:="false"}
: ${ENABLE_MESSAGE_POSTING:="false"}
: ${STEALTH_MODE:="false"}
: ${EMBED_USER_INFO:="true"}

# Set up logging
export LOG_LEVEL

# Authentication setup
if [ "$STEALTH_MODE" = "true" ]; then
    if [ -z "$SLACK_COOKIE" ]; then
        echo "Error: SLACK_COOKIE is required when STEALTH_MODE=true"
        exit 1
    fi
    if [ -z "$SLACK_WORKSPACE" ]; then
        echo "Error: SLACK_WORKSPACE is required when STEALTH_MODE=true"
        exit 1
    fi
    echo "Starting in stealth mode for workspace: $SLACK_WORKSPACE"
    export SLACK_COOKIE
    export SLACK_WORKSPACE
else
    if [ -z "$SLACK_TOKEN" ] && [ -z "$SLACK_USER_TOKEN" ] && [ -z "$SLACK_APP_TOKEN" ]; then
        echo "Error: At least one of SLACK_TOKEN, SLACK_USER_TOKEN, or SLACK_APP_TOKEN is required"
        exit 1
    fi
    echo "Starting with OAuth token authentication"
fi

# Configure caching
export CACHE_ENABLED
export CACHE_TTL

# Configure safety settings
export READ_ONLY_MODE
export ENABLE_MESSAGE_POSTING
export MAX_HISTORY_LIMIT

# Configure message settings
export EMBED_USER_INFO

# Set up allowed channels if specified
if [ -n "$ALLOWED_CHANNELS" ]; then
    export ALLOWED_CHANNELS
    echo "Message posting restricted to channels: $ALLOWED_CHANNELS"
fi

# Set up proxy if specified
if [ -n "$HTTP_PROXY" ]; then
    export HTTP_PROXY
    echo "Using HTTP proxy: $HTTP_PROXY"
fi

if [ -n "$HTTPS_PROXY" ]; then
    export HTTPS_PROXY
    echo "Using HTTPS proxy: $HTTPS_PROXY"
fi

# Prepare command line arguments
ARGS=()

# Add transport-specific arguments
if [ "$MCP_TRANSPORT" = "sse" ]; then
    ARGS+=("--sse")
    ARGS+=("--port" "$MCP_PORT")
    echo "Starting SSE server on port $MCP_PORT"
elif [ "$MCP_TRANSPORT" = "stdio" ]; then
    ARGS+=("--stdio")
    echo "Starting with stdio transport"
else
    echo "Warning: Unknown transport mode '$MCP_TRANSPORT', defaulting to stdio"
    ARGS+=("--stdio")
fi

# Add authentication arguments
if [ "$STEALTH_MODE" = "true" ]; then
    ARGS+=("--stealth")
    ARGS+=("--cookie" "$SLACK_COOKIE")
    ARGS+=("--workspace" "$SLACK_WORKSPACE")
else
    if [ -n "$SLACK_TOKEN" ]; then
        ARGS+=("--token" "$SLACK_TOKEN")
    fi
    if [ -n "$SLACK_USER_TOKEN" ]; then
        ARGS+=("--user-token" "$SLACK_USER_TOKEN")
    fi
    if [ -n "$SLACK_APP_TOKEN" ]; then
        ARGS+=("--app-token" "$SLACK_APP_TOKEN")
    fi
fi

# Add feature flags
if [ "$READ_ONLY_MODE" = "true" ]; then
    ARGS+=("--read-only")
fi

if [ "$ENABLE_MESSAGE_POSTING" = "true" ]; then
    ARGS+=("--enable-posting")
fi

if [ "$CACHE_ENABLED" = "true" ]; then
    ARGS+=("--cache")
    ARGS+=("--cache-ttl" "$CACHE_TTL")
fi

if [ "$EMBED_USER_INFO" = "true" ]; then
    ARGS+=("--embed-users")
fi

# Add proxy settings
if [ -n "$HTTP_PROXY" ]; then
    ARGS+=("--http-proxy" "$HTTP_PROXY")
fi

if [ -n "$HTTPS_PROXY" ]; then
    ARGS+=("--https-proxy" "$HTTPS_PROXY")
fi

# Add channel restrictions
if [ -n "$ALLOWED_CHANNELS" ]; then
    ARGS+=("--allowed-channels" "$ALLOWED_CHANNELS")
fi

# Add history limit
ARGS+=("--max-history" "$MAX_HISTORY_LIMIT")

# Add log level
ARGS+=("--log-level" "$LOG_LEVEL")

# Debug information
if [ "$LOG_LEVEL" = "DEBUG" ]; then
    echo "Debug: Command arguments: ${ARGS[@]}"
    echo "Debug: Environment variables:"
    env | grep -E '^(SLACK_|MCP_|CACHE_|READ_ONLY|ENABLE_|STEALTH|LOG_|HTTP)' | sort
fi

echo "Starting Slack MCP Server..."

# Execute the slack-mcp-server with all arguments
exec python -m slack_mcp_server "${ARGS[@]}" "$@"