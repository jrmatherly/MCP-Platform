# Slack MCP Server Usage Guide

## Overview

The Slack MCP Server provides comprehensive integration with Slack workspaces, offering both OAuth and stealth authentication modes, message management, search capabilities, and channel/user operations.

## Quick Start Examples

### Basic Message Retrieval

```bash
# Get recent messages from #general channel
python -m mcp_platform deploy slack \
  --config slack_token=xoxb-your-token

# Then use the client to fetch messages
curl -X POST http://localhost:3003/call \
  -H "Content-Type: application/json" \
  -d '{
    "method": "conversations_history",
    "params": {
      "channel_id": "#general",
      "limit": "1d"
    }
  }'
```

### Thread Management

```bash
# Get all replies in a thread
curl -X POST http://localhost:3003/call \
  -H "Content-Type: application/json" \
  -d '{
    "method": "conversations_replies",
    "params": {
      "channel_id": "#general",
      "thread_ts": "1234567890.123456",
      "limit": "50"
    }
  }'
```

### Message Search

```bash
# Search for messages containing specific terms
curl -X POST http://localhost:3003/call \
  -H "Content-Type: application/json" \
  -d '{
    "method": "search_messages",
    "params": {
      "query": "MCP platform deployment",
      "sort": "timestamp",
      "count": 10
    }
  }'
```

## Authentication Methods

### 1. OAuth Token Authentication (Recommended)

Most secure and feature-complete method using official Slack OAuth tokens.

#### Setup Steps:

1. **Create Slack App**
   - Go to https://api.slack.com/apps
   - Click "Create New App" → "From scratch"
   - Name your app and select workspace

2. **Configure OAuth Scopes**
   - Go to "OAuth & Permissions"
   - Add Bot Token Scopes:
     - `channels:history` - Read messages in public channels
     - `channels:read` - View basic channel information
     - `chat:write` - Send messages (if posting enabled)
     - `groups:history` - Read messages in private channels
     - `im:history` - Read direct messages
     - `mpim:history` - Read group direct messages
     - `users:read` - View user information

3. **Install App to Workspace**
   - Click "Install to Workspace"
   - Copy the Bot User OAuth Token (starts with `xoxb-`)

4. **Deploy with Token**
```bash
python -m mcp_platform deploy slack \
  --config slack_token=xoxb-your-bot-token
```

#### Advanced OAuth Setup:

```bash
# With user token for enhanced permissions
python -m mcp_platform deploy slack \
  --config slack_token=xoxb-your-bot-token \
  --config slack_user_token=xoxp-your-user-token

# With app-level token for socket mode
python -m mcp_platform deploy slack \
  --config slack_token=xoxb-your-bot-token \
  --config slack_app_token=xapp-your-app-token
```

### 2. Stealth Mode Authentication

Access Slack without creating a bot or requiring workspace admin approval.

#### Setup Steps:

1. **Extract Browser Cookies**
   - Open Slack in browser and log in
   - Open Developer Tools (F12)
   - Go to Application/Storage → Cookies
   - Find cookies for your workspace domain
   - Copy the `d` cookie value (starts with `xoxd-`)

2. **Deploy with Stealth Mode**
```bash
python -m mcp_platform deploy slack \
  --config stealth_mode=true \
  --config slack_cookie="d=xoxd-your-cookie-value" \
  --config slack_workspace=yourteam
```

#### Cookie Management:

```bash
# With multiple cookie values
python -m mcp_platform deploy slack \
  --config stealth_mode=true \
  --config slack_cookie="d=xoxd-...; x=xoxs-...; other=value" \
  --config slack_workspace=yourteam.slack.com
```

## Configuration Examples

### Development Environment

```bash
# Basic development setup with debugging
python -m mcp_platform deploy slack \
  --config slack_token=xoxb-your-token \
  --config log_level=DEBUG \
  --config cache_enabled=true
```

### Production Environment

```bash
# Production setup with safety controls
python -m mcp_platform deploy slack \
  --config slack_token=xoxb-your-token \
  --config read_only_mode=true \
  --config cache_enabled=true \
  --config cache_ttl=7200 \
  --config log_level=INFO
```

### Enterprise Environment

```bash
# Enterprise setup with proxy and restrictions
python -m mcp_platform deploy slack \
  --config slack_token=xoxb-your-token \
  --config http_proxy=http://proxy.company.com:8080 \
  --config https_proxy=https://proxy.company.com:8080 \
  --config allowed_channels="#approved-channel" \
  --config max_history_limit="7d"
```

## Tool Usage Examples

### Message History Operations

```python
# Python client example
from fastmcp.client import FastMCPClient

client = FastMCPClient(endpoint="http://localhost:3003")

# Get recent messages from a channel
messages = client.call("conversations_history", {
    "channel_id": "#general",
    "limit": "1d",
    "include_activity_messages": False
})

# Get messages with pagination
messages_page2 = client.call("conversations_history", {
    "channel_id": "#general",
    "cursor": messages["next_cursor"],
    "limit": "50"
})

# Get DM history
dm_messages = client.call("conversations_history", {
    "channel_id": "@username_dm",
    "limit": "1w"
})
```

### Thread Operations

```python
# Get thread replies
thread_replies = client.call("conversations_replies", {
    "channel_id": "#general",
    "thread_ts": "1234567890.123456",
    "include_activity_messages": True
})

# Get specific number of thread messages
limited_replies = client.call("conversations_replies", {
    "channel_id": "#general",
    "thread_ts": "1234567890.123456",
    "limit": "10"
})
```

### Message Posting (When Enabled)

```python
# Post a simple message
result = client.call("conversations_add_message", {
    "channel_id": "#test",
    "text": "Hello from MCP Slack Server!"
})

# Reply to a thread
thread_reply = client.call("conversations_add_message", {
    "channel_id": "#test",
    "text": "This is a thread reply",
    "thread_ts": "1234567890.123456"
})

# Post with formatting
formatted_message = client.call("conversations_add_message", {
    "channel_id": "#test",
    "text": "*Bold text* and `code` with <https://example.com|links>"
})
```

### Search Operations

```python
# Basic message search
search_results = client.call("search_messages", {
    "query": "deployment failed",
    "sort": "timestamp",
    "count": 20
})

# Advanced search with filters
filtered_search = client.call("search_messages", {
    "query": "from:@username in:#channel after:2023-01-01",
    "sort": "score",
    "count": 50
})
```

### Channel and User Management

```python
# Get channel information
channel_info = client.call("get_channel_info", {
    "channel": "#general"
})

# Get user information
user_info = client.call("get_user_info", {
    "user": "@username"
})

# List all channels
channels = client.call("list_channels")

# List direct messages
dms = client.call("list_dms")
```

## Environment Configuration

### Environment Variables

```bash
# Core authentication
export SLACK_TOKEN="xoxb-your-bot-token"
export SLACK_USER_TOKEN="xoxp-your-user-token"
export SLACK_WORKSPACE="yourteam"

# Stealth mode
export STEALTH_MODE=true
export SLACK_COOKIE="d=xoxd-your-cookie"

# Safety controls
export ENABLE_MESSAGE_POSTING=false
export ALLOWED_CHANNELS="#test,#bot-testing"
export READ_ONLY_MODE=false

# Performance
export CACHE_ENABLED=true
export CACHE_TTL=3600
export MAX_HISTORY_LIMIT="30d"

# Network
export HTTP_PROXY="http://proxy.example.com:8080"
export HTTPS_PROXY="https://proxy.example.com:8080"

# MCP settings
export MCP_TRANSPORT="stdio"
export MCP_PORT=3003
export LOG_LEVEL="INFO"
```

### Configuration Files

**JSON Configuration:**
```json
{
  "slack_token": "xoxb-your-token",
  "slack_workspace": "yourteam",
  "stealth_mode": false,
  "enable_message_posting": false,
  "allowed_channels": "#test,#bot-testing",
  "cache_enabled": true,
  "cache_ttl": 3600,
  "embed_user_info": true,
  "max_history_limit": "30d",
  "read_only_mode": false,
  "log_level": "INFO",
  "mcp_transport": "stdio",
  "mcp_port": 3003
}
```

**YAML Configuration:**
```yaml
slack_token: "xoxb-your-token"
slack_workspace: "yourteam"
stealth_mode: false
enable_message_posting: false
allowed_channels: "#test,#bot-testing"
cache_enabled: true
cache_ttl: 3600
embed_user_info: true
max_history_limit: "30d"
read_only_mode: false
log_level: "INFO"
mcp_transport: "stdio"
mcp_port: 3003
```

## Docker Usage

### Basic Docker Deployment

```bash
# Build the image
docker build -t dataeverything/mcp-slack:latest .

# Run with OAuth token
docker run -p 3003:3003 \
  -e SLACK_TOKEN=xoxb-your-token \
  -e LOG_LEVEL=INFO \
  dataeverything/mcp-slack:latest

# Run with stealth mode
docker run -p 3003:3003 \
  -e STEALTH_MODE=true \
  -e SLACK_COOKIE="d=xoxd-your-cookie" \
  -e SLACK_WORKSPACE=yourteam \
  dataeverything/mcp-slack:latest
```

### Docker Compose

```yaml
version: '3.8'
services:
  slack-mcp:
    image: dataeverything/mcp-slack:latest
    ports:
      - "3003:3003"
    environment:
      SLACK_TOKEN: xoxb-your-token
      SLACK_WORKSPACE: yourteam
      ENABLE_MESSAGE_POSTING: false
      CACHE_ENABLED: true
      LOG_LEVEL: INFO
      MCP_TRANSPORT: sse
    networks:
      - mcp-platform

networks:
  mcp-platform:
    external: true
```

### Docker with Volume Mounts

```bash
# Mount configuration directory
docker run -p 3003:3003 \
  -v /path/to/config:/app/config \
  -e SLACK_TOKEN=xoxb-your-token \
  dataeverything/mcp-slack:latest

# Mount logs directory
docker run -p 3003:3003 \
  -v /path/to/logs:/app/logs \
  -e SLACK_TOKEN=xoxb-your-token \
  -e LOG_LEVEL=DEBUG \
  dataeverything/mcp-slack:latest
```

## Integration Examples

### Claude Desktop Integration

Add to Claude Desktop configuration:

```json
{
  "mcpServers": {
    "slack": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-e", "SLACK_TOKEN=xoxb-your-token",
        "dataeverything/mcp-slack:latest"
      ]
    }
  }
}
```

### Custom Client Integration

```python
import asyncio
from fastmcp.client import FastMCPClient

async def slack_integration_example():
    # Initialize client
    client = FastMCPClient(endpoint="http://localhost:3003")
    
    # Get recent messages from multiple channels
    channels = ["#general", "#random", "#development"]
    
    for channel in channels:
        print(f"\n--- Messages from {channel} ---")
        messages = await client.call("conversations_history", {
            "channel_id": channel,
            "limit": "1d"
        })
        
        for message in messages.get("messages", []):
            user = message.get("user", "Unknown")
            text = message.get("text", "")
            timestamp = message.get("ts", "")
            print(f"[{timestamp}] {user}: {text}")
    
    # Search for specific content
    search_results = await client.call("search_messages", {
        "query": "error OR failed OR issue",
        "sort": "timestamp",
        "count": 10
    })
    
    print(f"\n--- Found {len(search_results.get('messages', []))} relevant messages ---")
    
    await client.close()

# Run the example
asyncio.run(slack_integration_example())
```

## Troubleshooting Guide

### Authentication Issues

1. **Invalid Token Error**
   ```bash
   # Verify token format and permissions
   # OAuth tokens: xoxb-, xoxp-, xapp-
   # Cookie values: xoxd-
   
   # Test token manually
   curl -H "Authorization: Bearer xoxb-your-token" \
        https://slack.com/api/auth.test
   ```

2. **Stealth Mode Failures**
   ```bash
   # Update browser cookies (they expire)
   # Ensure workspace domain is correct
   # Check for workspace SSO requirements
   ```

### Network and Connectivity

1. **Proxy Configuration**
   ```bash
   # Test proxy connectivity
   curl --proxy http://proxy.company.com:8080 \
        https://slack.com/api/auth.test
   
   # Use HTTPS proxy for SSL
   --config https_proxy=https://proxy.company.com:8080
   ```

2. **Port Conflicts**
   ```bash
   # Check if port is available
   netstat -an | grep 3003
   
   # Use different port
   --config mcp_port=3004
   ```

### Performance Issues

1. **Slow Message Retrieval**
   ```bash
   # Enable caching
   --config cache_enabled=true
   --config cache_ttl=7200
   
   # Reduce history limits
   --config max_history_limit="7d"
   ```

2. **Memory Usage**
   ```bash
   # Limit concurrent operations
   # Reduce cache TTL
   --config cache_ttl=1800
   
   # Use read-only mode
   --config read_only_mode=true
   ```

### Debug Information

Enable comprehensive debugging:

```bash
# Maximum debug output
python -m mcp_platform deploy slack \
  --config slack_token=xoxb-your-token \
  --config log_level=DEBUG \
  --config cache_enabled=false

# Monitor network requests
export PYTHONPATH=/app
python -c "
import logging
logging.basicConfig(level=logging.DEBUG)
# Your slack server code here
"
```

## Best Practices

### Security

1. **Use OAuth tokens when possible** - More secure than stealth mode
2. **Enable read-only mode** for monitoring applications
3. **Restrict message posting** to specific channels
4. **Rotate tokens regularly** and monitor for unauthorized usage
5. **Use environment variables** for sensitive configuration

### Performance

1. **Enable caching** for better response times
2. **Set appropriate history limits** to avoid excessive data transfer
3. **Use pagination** for large message sets
4. **Monitor resource usage** and adjust cache settings

### Reliability

1. **Handle rate limits** gracefully with retries
2. **Implement error handling** for network issues
3. **Monitor token expiration** and refresh as needed
4. **Use health checks** for production deployments

This comprehensive usage guide should help you successfully deploy and operate the Slack MCP Server in various environments and use cases.