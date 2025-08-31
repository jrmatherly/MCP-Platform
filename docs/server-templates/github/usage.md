# Github Usage Guide

## Overview

This guide shows how to use the Github with different MCP clients and integration methods.

## Tool Discovery

### Interactive CLI
```bash
# Start interactive mode
python -m mcp_platform interactive

# List available tools
mcpp> tools github
```

### Regular CLI
```bash
# Discover tools using CLI
python -m mcp_platform tools github
```

### Python Client
```python
from mcp_platform.client import MCPClient

async def discover_tools():
    async with MCPClient() as client:
        tools = await client.list_tools("github")
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
mcpp> deploy github
```

Then call tools:
### Regular CLI

```bash
# Deploy the template
python -m mcp_platform deploy github

# Check deployment status
python -m mcp_platform status

# View logs
python -m mcp_platform logs github

# Stop the template
python -m mcp_platform stop github
```

### Python Client

```python
import asyncio
from mcp_platform.client import MCPClient

async def use_github():
    async with MCPClient() as client:
        # Start the server
        deployment = await client.start_server("github", {})
        
        if deployment["success"]:
            deployment_id = deployment["deployment_id"]
            
            try:
            finally:
                # Clean up
                await client.stop_server(deployment_id)
        else:
            print("Failed to start server")

# Run the example
asyncio.run(use_github())
```

## Integration Examples

### Claude Desktop

Add this configuration to your Claude Desktop configuration file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "github": {
      "command": "python",
      "args": ["-m", "mcp_platform", "connect", "github", "--stdio"],
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
    "github": {
      "command": "python",
      "args": ["-m", "mcp_platform", "connect", "github", "--stdio"],
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
python -m mcp_platform connect github --llm claude
python -m mcp_platform connect github --llm vscode
```

## Configuration

For template-specific configuration options, see the main template documentation. Common configuration methods:

```bash
# Deploy with configuration
python -m mcp_platform deploy github --config key=value

# Deploy with environment variables  
python -m mcp_platform deploy github --env KEY=VALUE

# Deploy with config file
python -m mcp_platform deploy github --config-file config.json
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
   mcpp> tools github --refresh
   ```

### Debug Mode

Enable debug logging for troubleshooting:

```bash
# Interactive CLI with debug
LOG_LEVEL=debug python -m mcp_platform interactive

# Deploy with debug logging
python -m mcp_platform deploy github --config log_level=debug
```

For more help, see the [main documentation](../../) or open an issue in the repository.
