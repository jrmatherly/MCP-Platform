# Slack MCP Server

Enhanced Slack MCP server for comprehensive workspace integration with channels, DMs, and message management.

This template extends the powerful [korotovsky/slack-mcp-server](https://github.com/korotovsky/slack-mcp-server) and provides seamless integration with the MCP Platform ecosystem.

## Features

- **conversations_history**: Get messages from channels, DMs, or group DMs with smart pagination
- **conversations_replies**: Get thread messages for a specific conversation
- **conversations_add_message**: Post messages to channels or DMs (safety controls apply)
- **search_messages**: Search messages across channels and DMs with filters
- **channel_management**: List, lookup, and manage channel information
- **user_management**: Lookup user information and manage DM conversations

## Key Capabilities

### 🔐 Dual Authentication Modes
- **OAuth Mode**: Use standard Slack OAuth tokens (xoxb-, xoxp-, xapp-)
- **Stealth Mode**: Use browser cookies for access without bot permissions

### 💬 Comprehensive Messaging
- Fetch message history with smart pagination (by date or count)
- Access thread conversations with full context
- Search across channels and DMs with advanced filters
- Post messages with safety controls and channel restrictions

### 🚀 Advanced Features
- Support for channels, DMs, and group DMs
- Channel and user lookup by name or ID (e.g., #general, @username)
- Embedded user information for better context
- Caching for improved performance
- Proxy support for enterprise environments

## Quick Start

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run with OAuth token (stdio transport)
python server.py --slack-token xoxb-your-token

# Run with stealth mode
python server.py --stealth-mode --slack-cookie "d=xoxd-..." --slack-workspace yourteam

# Run with SSE transport
python server.py --mcp-transport sse --mcp-port 3003
```

### Docker Deployment

```bash
# Build the image
docker build -t dataeverything/mcp-slack:latest .

# Run with OAuth token
docker run -p 3003:3003 \
  -e SLACK_TOKEN=xoxb-your-token \
  dataeverything/mcp-slack:latest

# Run with stealth mode
docker run -p 3003:3003 \
  -e STEALTH_MODE=true \
  -e SLACK_COOKIE="d=xoxd-..." \
  -e SLACK_WORKSPACE=yourteam \
  dataeverything/mcp-slack:latest

# Join MCP Platform network
docker network create mcp-platform
docker run --network mcp-platform --name slack \
  -p 3003:3003 -e SLACK_TOKEN=xoxb-your-token \
  dataeverything/mcp-slack:latest
```

### MCP Platform CLI

```bash
# Deploy with OAuth token
python -m mcp_platform deploy slack --config slack_token=xoxb-your-token

# Deploy with stealth mode
python -m mcp_platform deploy slack \
  --config stealth_mode=true \
  --config slack_cookie="d=xoxd-..." \
  --config slack_workspace=yourteam

# Deploy with SSE transport
python -m mcp_platform deploy slack \
  --config mcp_transport=sse \
  --config mcp_port=3003
```

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SLACK_TOKEN` | Slack OAuth bot token (xoxb-...) | - |
| `SLACK_USER_TOKEN` | Slack user token (xoxp-...) | - |
| `SLACK_APP_TOKEN` | Slack app token (xapp-...) | - |
| `SLACK_COOKIE` | Browser cookie for stealth mode | - |
| `SLACK_WORKSPACE` | Workspace domain (yourteam.slack.com) | - |
| `STEALTH_MODE` | Enable stealth mode authentication | false |
| `ENABLE_MESSAGE_POSTING` | Allow posting messages | false |
| `ALLOWED_CHANNELS` | Comma-separated allowed channels | - |
| `CACHE_ENABLED` | Enable user/channel caching | true |
| `CACHE_TTL` | Cache time-to-live in seconds | 3600 |
| `MAX_HISTORY_LIMIT` | Maximum history fetch limit | 30d |
| `READ_ONLY_MODE` | Restrict to read-only operations | false |
| `LOG_LEVEL` | Logging level (DEBUG, INFO, WARNING, ERROR) | INFO |
| `MCP_TRANSPORT` | Transport mode (stdio, sse) | stdio |
| `MCP_PORT` | Port for SSE transport | 3003 |

### Configuration Options

```bash
# Direct configuration (for config_schema properties)
--config slack_token="xoxb-your-token"
--config stealth_mode=true
--config enable_message_posting=true

# Environment variables
--env SLACK_TOKEN="xoxb-your-token"
--env STEALTH_MODE=true
--env ENABLE_MESSAGE_POSTING=true

# Double-underscore notation (for nested configs)
--config slack__workspace="yourteam"
--config slack__max_history="90d"
```

### Configuration Files

**JSON Configuration (`slack-config.json`):**
```json
{
  "slack_token": "xoxb-your-token",
  "slack_workspace": "yourteam",
  "enable_message_posting": false,
  "allowed_channels": "#test,#bot-testing",
  "cache_enabled": true,
  "log_level": "INFO"
}
```

**YAML Configuration (`slack-config.yml`):**
```yaml
slack_token: "xoxb-your-token"
slack_workspace: "yourteam"
enable_message_posting: false
allowed_channels: "#test,#bot-testing"
cache_enabled: true
log_level: INFO
```

## Available Tools

### 1. conversations_history

Get messages from channels, DMs, or group DMs with smart pagination.

**Parameters:**
- `channel_id` (string, required): Channel ID (Cxxxxxxxxxx) or name (#general, @username)
- `include_activity_messages` (boolean, optional): Include activity messages like joins/leaves
- `cursor` (string, optional): Pagination cursor from previous request
- `limit` (string, optional): Time limit (1d, 7d, 30d) or message count (50, 100)

**Examples:**
```python
# Get recent messages from #general
client.call("conversations_history", channel_id="#general", limit="1d")

# Get DM history with specific user
client.call("conversations_history", channel_id="@username", limit="50")

# Get messages with activity events
client.call("conversations_history", 
           channel_id="#general", 
           include_activity_messages=True)
```

### 2. conversations_replies

Get thread messages for a specific conversation.

**Parameters:**
- `channel_id` (string, required): Channel ID or name
- `thread_ts` (string, required): Thread timestamp (1234567890.123456)
- `include_activity_messages` (boolean, optional): Include activity messages
- `cursor` (string, optional): Pagination cursor
- `limit` (string, optional): Time limit or message count

**Example:**
```python
# Get all replies in a thread
client.call("conversations_replies", 
           channel_id="#general", 
           thread_ts="1234567890.123456")
```

### 3. conversations_add_message

Post messages to channels or DMs (requires explicit enabling for safety).

**Parameters:**
- `channel_id` (string, required): Channel ID or name
- `text` (string, required): Message text
- `thread_ts` (string, optional): Reply to thread timestamp

**Example:**
```python
# Post a message (only if enabled)
client.call("conversations_add_message", 
           channel_id="#test", 
           text="Hello from MCP!")

# Reply to a thread
client.call("conversations_add_message", 
           channel_id="#test", 
           text="Thread reply",
           thread_ts="1234567890.123456")
```

### 4. search_messages

Search messages across channels and DMs with filters.

**Parameters:**
- `query` (string, required): Search query
- `sort` (string, optional): Sort order (timestamp, score)
- `count` (integer, optional): Number of results to return

**Example:**
```python
# Search for messages containing "MCP"
client.call("search_messages", 
           query="MCP platform", 
           sort="timestamp", 
           count=20)
```

### 5. Channel and User Management

Additional tools for managing channels and users:

```python
# List channels
client.call("list_channels")

# Get channel info
client.call("get_channel_info", channel="#general")

# Get user info
client.call("get_user_info", user="@username")

# List DMs
client.call("list_dms")
```

## Authentication Modes

### OAuth Mode (Recommended)

Use standard Slack OAuth tokens for secure API access:

```bash
# Get tokens from https://api.slack.com/apps
python -m mcp_platform deploy slack \
  --config slack_token=xoxb-your-bot-token \
  --config slack_user_token=xoxp-your-user-token
```

### Stealth Mode

Use browser cookies for access without bot permissions:

```bash
# Extract cookies from browser developer tools
python -m mcp_platform deploy slack \
  --config stealth_mode=true \
  --config slack_cookie="d=xoxd-...;..." \
  --config slack_workspace=yourteam
```

## Safety Features

### Message Posting Controls

Message posting is **disabled by default** for safety:

```bash
# Enable posting with channel restrictions
python -m mcp_platform deploy slack \
  --config enable_message_posting=true \
  --config allowed_channels="#test,#bot-testing"
```

### Read-Only Mode

For maximum security, enable read-only mode:

```bash
python -m mcp_platform deploy slack \
  --config read_only_mode=true
```

## Transport Modes

### Stdio (Default)

Perfect for Claude Desktop and other MCP clients:

```bash
# Direct stdio usage
python server.py --slack-token xoxb-your-token

# Docker stdio
docker run -i --rm -e SLACK_TOKEN=xoxb-your-token dataeverything/mcp-slack
```

### Server-Sent Events (SSE)

For web applications and real-time updates:

```bash
# Start SSE server
python server.py --mcp-transport sse --mcp-port 3003

# Connect to SSE endpoint
curl -N http://localhost:3003/sse
```

## Troubleshooting

### Common Issues

1. **Authentication Error: Invalid Token**
   ```bash
   # Verify token permissions and expiration
   # For OAuth: Check bot/user token scopes
   # For stealth: Update browser cookies
   ```

2. **Channel Not Found**
   ```bash
   # Use channel ID instead of name
   # Ensure bot has access to private channels
   ```

3. **Message Posting Forbidden**
   ```bash
   # Enable message posting explicitly
   --config enable_message_posting=true
   
   # Check allowed channels configuration
   --config allowed_channels="#your-channel"
   ```

4. **SSE Connection Issues**
   ```bash
   # Ensure port is available
   --config mcp_port=3004
   
   # Check firewall settings
   ```

### Debugging

Enable debug logging for detailed information:

```bash
# Local development
python server.py --log-level DEBUG

# Docker
docker run -e LOG_LEVEL=DEBUG dataeverything/mcp-slack

# CLI deployment
python -m mcp_platform deploy slack --config log_level=DEBUG
```

## Enterprise Setup

### Proxy Configuration

For enterprise environments with proxy requirements:

```bash
python -m mcp_platform deploy slack \
  --config http_proxy=http://proxy.company.com:8080 \
  --config https_proxy=https://proxy.company.com:8080
```

### Advanced Caching

Configure caching for better performance:

```bash
python -m mcp_platform deploy slack \
  --config cache_enabled=true \
  --config cache_ttl=7200  # 2 hours
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes following the code style
4. Add tests for new functionality
5. Update documentation
6. Submit a pull request

## License

This template extends the korotovsky/slack-mcp-server project. Please refer to the original project's license terms.

## Support

- **Template Issues**: Report to MCP Platform repository
- **Slack Server Issues**: Report to [korotovsky/slack-mcp-server](https://github.com/korotovsky/slack-mcp-server)
- **Documentation**: See MCP Platform documentation for template usage