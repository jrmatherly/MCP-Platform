# GitLab MCP Server Usage Guide

## Overview

This guide shows how to use the GitLab MCP Server with different MCP clients and integration methods.

## Tool Discovery

### Interactive CLI
```bash
# Start interactive mode
python -m mcp_platform interactive

# List available tools
mcpp> tools gitlab
```

### Regular CLI
```bash
# Discover tools using CLI
python -m mcp_platform tools gitlab
```

### Python Client
```python
from mcp_platform.client import MCPClient

async def discover_tools():
    async with MCPClient() as client:
        tools = await client.list_tools("gitlab")
        for tool in tools:
            print(f"Tool: {tool['name']} - {tool['description']}")
```

## Available Tools

## Usage Examples

### Interactive CLI

```bash
# Start interactive mode
python -m mcp_platform interactive

# Deploy the template (if not already deployed)
mcpp> deploy gitlab
```

Then call tools:
### Regular CLI

```bash
# Deploy the template
python -m mcp_platform deploy gitlab

# Check deployment status
python -m mcp_platform status

# View logs
python -m mcp_platform logs gitlab

# Stop the template
python -m mcp_platform stop gitlab
```

### Python Client

```python
import asyncio
from mcp_platform.client import MCPClient

async def use_gitlab():
    async with MCPClient() as client:
        # Start the server
        deployment = await client.start_server("gitlab", {})
        
        if deployment["success"]:
            deployment_id = deployment["deployment_id"]
            
            try:
            finally:
                # Clean up
                await client.stop_server(deployment_id)
        else:
            print("Failed to start server")

# Run the example
asyncio.run(use_gitlab())
```

## Integration Examples

### Claude Desktop

Add this configuration to your Claude Desktop configuration file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "gitlab": {
      "command": "python",
      "args": ["-m", "mcp_platform", "connect", "gitlab", "--stdio"],
      "env": {
        "LOG_LEVEL": "info"
      }
    }
  }
}
```

### VS Code

Install the MCP extension and add this to your VS Code settings (`.vscode/settings.json`):

```json
{
  "mcp.servers": {
    "gitlab": {
      "command": "python",
      "args": ["-m", "mcp_platform", "connect", "gitlab", "--stdio"],
      "env": {
        "LOG_LEVEL": "info"
      }
    }
  }
}
```

### Manual Connection

```bash
# Get connection details for other integrations
python -m mcp_platform connect gitlab --llm claude
python -m mcp_platform connect gitlab --llm vscode
```

## Configuration

For template-specific configuration options, see the main template documentation. Common configuration methods:

```bash
# Deploy with configuration
python -m mcp_platform deploy gitlab --config key=value

# Deploy with environment variables  
python -m mcp_platform deploy gitlab --env KEY=VALUE

# Deploy with config file
python -m mcp_platform deploy gitlab --config-file config.json
```

## Troubleshooting

### Common Issues

1. **Template not found**: Ensure the template name is correct
   ```bash
   python -m mcp_platform list  # List available templates
   ```

2. **Connection issues**: Check if the server is running
   ```bash
   python -m mcp_platform status
   ```

3. **Tool discovery fails**: Try refreshing the tool cache
   ```bash
   mcpp> tools gitlab --refresh
   ```

### Debug Mode

Enable debug logging for troubleshooting:

```bash
# Interactive CLI with debug
LOG_LEVEL=debug python -m mcp_platform interactive

# Deploy with debug logging
python -m mcp_platform deploy gitlab --config log_level=debug
```

For more help, see the [main documentation](../../) or open an issue in the repository.
