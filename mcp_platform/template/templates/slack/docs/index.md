# Slack MCP Server

Enhanced Slack MCP server for comprehensive workspace integration with channels, DMs, and message management.

This template extends the powerful [korotovsky/slack-mcp-server](https://github.com/korotovsky/slack-mcp-server) and provides seamless integration with the MCP Platform ecosystem.

## Overview

The Slack MCP Server provides a comprehensive interface to Slack workspaces, enabling AI assistants and automation tools to interact with Slack channels, direct messages, and threads. It supports both official OAuth authentication and stealth mode using browser cookies.

### Key Features

- **Dual Authentication**: OAuth tokens or browser cookies (stealth mode)
- **Message Management**: Fetch, search, and post messages with safety controls
- **Thread Support**: Complete thread conversation handling
- **Channel Operations**: List, lookup, and manage channels
- **User Management**: User information and DM handling
- **Smart Pagination**: Efficient message history with date/count limits
- **Enterprise Ready**: Proxy support and security features

## Architecture

The Slack MCP server follows a modular architecture:

1. **Authentication Layer**: Handles OAuth and stealth mode authentication
2. **API Interface**: Manages Slack Web API communication
3. **Caching System**: Improves performance with configurable TTL
4. **Safety Controls**: Message posting restrictions and read-only mode
5. **Transport Layer**: Supports stdio and SSE protocols

## Quick Start

### OAuth Mode (Recommended)

```bash
# Create Slack app and get bot token
python -m mcp_platform deploy slack \
  --config slack_token=xoxb-your-bot-token
```

### Stealth Mode

```bash
# Extract browser cookies and deploy
python -m mcp_platform deploy slack \
  --config stealth_mode=true \
  --config slack_cookie="d=xoxd-your-cookie" \
  --config slack_workspace=yourteam
```

## Configuration

### Authentication Options

| Method | Tokens Required | Permissions | Setup Complexity |
|--------|----------------|-------------|-----------------|
| OAuth Bot | `slack_token` (xoxb-) | Bot scopes | Medium |
| OAuth User | `slack_user_token` (xoxp-) | User scopes | Medium |
| OAuth App | `slack_app_token` (xapp-) | App-level | High |
| Stealth | `slack_cookie` (browser) | User session | Low |

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SLACK_TOKEN` | Bot OAuth token | - |
| `SLACK_USER_TOKEN` | User OAuth token | - |
| `SLACK_COOKIE` | Browser cookie for stealth | - |
| `SLACK_WORKSPACE` | Workspace domain | - |
| `STEALTH_MODE` | Enable stealth authentication | false |
| `ENABLE_MESSAGE_POSTING` | Allow posting messages | false |
| `ALLOWED_CHANNELS` | Posting channel restrictions | - |
| `CACHE_ENABLED` | Enable user/channel caching | true |
| `READ_ONLY_MODE` | Restrict to read operations | false |

### Safety Features

- **Message posting disabled by default** - Requires explicit enabling
- **Channel restrictions** - Limit posting to specific channels
- **Read-only mode** - Complete write protection
- **Token validation** - Automatic credential verification

## Available Tools

### conversations_history

Get messages from channels, DMs, or group DMs with smart pagination.

**Parameters:**
- `channel_id`: Channel ID (C123...) or name (#general, @user)
- `limit`: Time period (1d, 7d, 30d) or message count
- `include_activity_messages`: Include join/leave events
- `cursor`: Pagination cursor for next page

**Example:**
```python
client.call("conversations_history", {
    "channel_id": "#general",
    "limit": "1d"
})
```

### conversations_replies

Get all messages in a thread conversation.

**Parameters:**
- `channel_id`: Channel containing the thread
- `thread_ts`: Thread timestamp (1234567890.123456)
- `limit`: Message limit or time period
- `cursor`: Pagination cursor

**Example:**
```python
client.call("conversations_replies", {
    "channel_id": "#general", 
    "thread_ts": "1234567890.123456"
})
```

### conversations_add_message

Post messages to channels or DMs (requires explicit enabling).

**Parameters:**
- `channel_id`: Target channel or DM
- `text`: Message content
- `thread_ts`: Reply to thread (optional)

**Example:**
```python
client.call("conversations_add_message", {
    "channel_id": "#test",
    "text": "Hello from MCP!"
})
```

### search_messages

Search messages across the workspace with filters.

**Parameters:**
- `query`: Search terms and filters
- `sort`: Sort by timestamp or relevance
- `count`: Number of results

**Example:**
```python
client.call("search_messages", {
    "query": "MCP platform in:#general",
    "sort": "timestamp",
    "count": 20
})
```

### Channel and User Management

Additional tools for workspace management:

- `list_channels`: Get all accessible channels
- `get_channel_info`: Channel details and metadata
- `get_user_info`: User profile information
- `list_dms`: Direct message conversations

## Transport Modes

### Stdio Transport

Perfect for Claude Desktop and MCP clients:

```bash
# Direct stdio usage
python server.py --slack-token xoxb-your-token

# Docker stdio
docker run -i --rm \
  -e SLACK_TOKEN=xoxb-your-token \
  dataeverything/mcp-slack
```

### Server-Sent Events (SSE)

For web applications and real-time integration:

```bash
# Start SSE server
python -m mcp_platform deploy slack \
  --config mcp_transport=sse \
  --config mcp_port=3003

# Connect via HTTP
curl -N http://localhost:3003/sse
```

## Integration Examples

### Claude Desktop

Add to your Claude Desktop configuration:

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

### Custom Application

```python
import asyncio
from fastmcp.client import FastMCPClient

async def slack_integration():
    client = FastMCPClient(endpoint="http://localhost:3003")
    
    # Get recent messages
    messages = await client.call("conversations_history", {
        "channel_id": "#general",
        "limit": "1d"
    })
    
    # Search for issues
    issues = await client.call("search_messages", {
        "query": "error OR failed OR bug",
        "sort": "timestamp"
    })
    
    await client.close()

asyncio.run(slack_integration())
```

## Enterprise Deployment

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
      CACHE_ENABLED: true
      READ_ONLY_MODE: true
      LOG_LEVEL: INFO
    networks:
      - mcp-platform

networks:
  mcp-platform:
    external: true
```

### Kubernetes

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: slack-mcp
spec:
  replicas: 2
  selector:
    matchLabels:
      app: slack-mcp
  template:
    metadata:
      labels:
        app: slack-mcp
    spec:
      containers:
      - name: slack-mcp
        image: dataeverything/mcp-slack:latest
        ports:
        - containerPort: 3003
        env:
        - name: SLACK_TOKEN
          valueFrom:
            secretKeyRef:
              name: slack-secrets
              key: token
        - name: CACHE_ENABLED
          value: "true"
        - name: READ_ONLY_MODE
          value: "true"
```

## Troubleshooting

### Authentication Issues

1. **Invalid Token**: Verify token format and permissions
2. **Expired Cookies**: Update browser cookies for stealth mode
3. **Permission Denied**: Check bot/app scopes in Slack

### Performance Issues

1. **Slow Responses**: Enable caching and reduce history limits
2. **Rate Limiting**: Implement exponential backoff
3. **Memory Usage**: Adjust cache TTL and concurrent requests

### Network Issues

1. **Proxy Configuration**: Set HTTP_PROXY and HTTPS_PROXY
2. **Firewall**: Ensure port 3003 is accessible
3. **SSL/TLS**: Verify certificate trust for enterprise networks

## Best Practices

### Security

- Use read-only mode for monitoring applications
- Restrict message posting to specific channels
- Rotate tokens regularly and monitor usage
- Use environment variables for sensitive data

### Performance

- Enable caching for better response times
- Set appropriate history limits
- Use pagination for large datasets
- Monitor resource usage and adjust accordingly

### Reliability

- Implement error handling and retries
- Use health checks for production deployments
- Monitor token expiration and refresh
- Set up logging and alerting

## Contributing

Contributions to improve the Slack MCP server template are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Update documentation
5. Submit a pull request

## License

This template extends the korotovsky/slack-mcp-server project. Please refer to the original project's license terms.

## Support

- **Template Issues**: [MCP Platform Repository](https://github.com/Data-Everything/MCP-Platform)
- **Slack Server Issues**: [korotovsky/slack-mcp-server](https://github.com/korotovsky/slack-mcp-server)
- **Documentation**: [MCP Platform Docs](https://docs.mcp-platform.com)
