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
- **XOXC/XOXD Mode**: Use browser cookies (xoxc-... and xoxd-...) for access without bot permissions
- **XOXP Mode**: Use user OAuth tokens (xoxp-...) for standard API access

### 💬 Comprehensive Messaging
- Fetch message history with smart pagination (by date or count)
- Access thread conversations with full context
- Search across channels and DMs with advanced filters
- Post messages with safety controls and channel restrictions

### 🚀 Advanced Features
- Support for channels, DMs, and group DMs
- Channel and user lookup by name or ID (e.g., #general, @username)
- Intelligent caching with configurable cache files
- Proxy support for enterprise environments
- Custom TLS support for Enterprise Slack

## Quick Start

### Using Docker with XOXP Token

```bash
docker run -i --rm \
  -e SLACK_MCP_XOXP_TOKEN=xoxp-your-token \
  ghcr.io/korotovsky/slack-mcp-server:v1.1.24 \
  mcp-server --transport stdio
```

### Using Docker with XOXC/XOXD Tokens

```bash
docker run -i --rm \
  -e SLACK_MCP_XOXC_TOKEN=xoxc-your-token \
  -e SLACK_MCP_XOXD_TOKEN=xoxd-your-cookie \
  ghcr.io/korotovsky/slack-mcp-server:v1.1.24 \
  mcp-server --transport stdio
```

### Using MCP Platform CLI

```bash
# With XOXP token
python -m mcp_platform deploy slack --config slack_mcp_xoxp_token=xoxp-your-token

# With XOXC/XOXD tokens
python -m mcp_platform deploy slack \
  --config slack_mcp_xoxc_token=xoxc-your-token \
  --config slack_mcp_xoxd_token=xoxd-your-cookie

# With SSE transport
python -m mcp_platform deploy slack \
  --transport sse \
  --config slack_mcp_port=13080 \
  --config slack_mcp_xoxp_token=xoxp-your-token
```

### Claude Desktop Integration

Add to your `claude_desktop_config.json`:

**Using XOXP Token:**
```json
{
  "mcpServers": {
    "slack": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-e",
        "SLACK_MCP_XOXP_TOKEN",
        "ghcr.io/korotovsky/slack-mcp-server:v1.1.24",
        "mcp-server",
        "--transport",
        "stdio"
      ],
      "env": {
        "SLACK_MCP_XOXP_TOKEN": "xoxp-your-token"
      }
    }
  }
}
```

**Using XOXC/XOXD Tokens:**
```json
{
  "mcpServers": {
    "slack": {
      "command": "docker",
      "args": [
        "run",
        "-i",
        "--rm",
        "-e",
        "SLACK_MCP_XOXC_TOKEN",
        "-e",
        "SLACK_MCP_XOXD_TOKEN",
        "ghcr.io/korotovsky/slack-mcp-server:v1.1.24",
        "mcp-server",
        "--transport",
        "stdio"
      ],
      "env": {
        "SLACK_MCP_XOXC_TOKEN": "xoxc-your-token",
        "SLACK_MCP_XOXD_TOKEN": "xoxd-your-cookie"
      }
    }
  }
}
```

### SSE Transport for Web Applications

```bash
# Start SSE server
docker run -p 13080:13080 \
  -e SLACK_MCP_XOXP_TOKEN=xoxp-your-token \
  ghcr.io/korotovsky/slack-mcp-server:v1.1.24 \
  mcp-server --transport sse --host 0.0.0.0

# Connect via mcp-remote
npx mcp-remote http://localhost:13080/sse
```

## Configuration

### Authentication Methods

The server supports multiple authentication methods:

1. **XOXP Token (User OAuth)**: Standard user token for full API access
2. **XOXC/XOXD Tokens (Browser Cookies)**: Extract from browser for stealth access

### Environment Variables

All environment variables from the [korotovsky/slack-mcp-server](https://github.com/korotovsky/slack-mcp-server) are supported:

| Variable | Description | Default |
|----------|-------------|---------|
| `SLACK_MCP_XOXC_TOKEN` | Slack browser token (xoxc-...) | - |
| `SLACK_MCP_XOXD_TOKEN` | Slack browser cookie d (xoxd-...) | - |
| `SLACK_MCP_XOXP_TOKEN` | User OAuth token (xoxp-...) | - |
| `SLACK_MCP_PORT` | Port for the MCP server | 13080 |
| `SLACK_MCP_HOST` | Host for the MCP server | 127.0.0.1 |
| `SLACK_MCP_SSE_API_KEY` | Bearer token for SSE transport | - |
| `SLACK_MCP_PROXY` | Proxy URL for outgoing requests | - |
| `SLACK_MCP_USER_AGENT` | Custom User-Agent (for Enterprise Slack) | - |
| `SLACK_MCP_CUSTOM_TLS` | Enable custom TLS-handshake | false |
| `SLACK_MCP_SERVER_CA` | Path to CA certificate | - |
| `SLACK_MCP_SERVER_CA_TOOLKIT` | Inject HTTPToolkit CA certificate | false |
| `SLACK_MCP_SERVER_CA_INSECURE` | Trust insecure requests (NOT RECOMMENDED) | false |
| `SLACK_MCP_ADD_MESSAGE_TOOL` | Enable message posting control | - |
| `SLACK_MCP_ADD_MESSAGE_MARK` | Auto-mark posted messages as read | false |
| `SLACK_MCP_ADD_MESSAGE_UNFURLING` | Enable link unfurling | - |
| `SLACK_MCP_USERS_CACHE` | Path to users cache file | .users_cache.json |
| `SLACK_MCP_CHANNELS_CACHE` | Path to channels cache file | .channels_cache_v2.json |
| `SLACK_MCP_LOG_LEVEL` | Log level (debug, info, warn, error, panic, fatal) | info |

### Message Posting Control

The `SLACK_MCP_ADD_MESSAGE_TOOL` variable controls message posting:

- **`true`**: Enable posting to all channels
- **`C1234567890,C0987654321`**: Comma-separated channel IDs to whitelist
- **`!C1234567890`**: Allow all channels except specified ones
- **Empty/unset**: Disable posting (default for safety)

### Enterprise Slack Configuration

For Enterprise Slack environments, you may need:

```bash
export SLACK_MCP_USER_AGENT="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36..."
export SLACK_MCP_CUSTOM_TLS=true
```

### Configuration Examples

**Basic XOXP Authentication:**
```bash
export SLACK_MCP_XOXP_TOKEN=xoxp-your-token
docker run -i --rm -e SLACK_MCP_XOXP_TOKEN ghcr.io/korotovsky/slack-mcp-server:v1.1.24
```

**Browser Cookie Authentication:**
```bash
export SLACK_MCP_XOXC_TOKEN=xoxc-your-token
export SLACK_MCP_XOXD_TOKEN=xoxd-your-cookie
docker run -i --rm -e SLACK_MCP_XOXC_TOKEN -e SLACK_MCP_XOXD_TOKEN ghcr.io/korotovsky/slack-mcp-server:v1.1.24
```

**With Message Posting Enabled:**
```bash
export SLACK_MCP_XOXP_TOKEN=xoxp-your-token
export SLACK_MCP_ADD_MESSAGE_TOOL=C1234567890,C0987654321
docker run -i --rm -e SLACK_MCP_XOXP_TOKEN -e SLACK_MCP_ADD_MESSAGE_TOOL ghcr.io/korotovsky/slack-mcp-server:v1.1.24
```
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