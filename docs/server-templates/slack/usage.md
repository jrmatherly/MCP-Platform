# Slack MCP Server Usage Guide

## Overview

This guide shows how to use the Slack MCP Server with different MCP clients and integration methods.

## Tool Discovery

### Interactive CLI
```bash
# Start interactive mode
python -m mcp_platform interactive

# List available tools
mcpp> tools slack
```

### Regular CLI
```bash
# Discover tools using CLI
python -m mcp_platform tools slack
```

### Python Client
```python
from mcp_platform.client import MCPClient

async def discover_tools():
    async with MCPClient() as client:
        tools = await client.list_tools("slack")
        for tool in tools:
            print(f"Tool: {tool['name']} - {tool['description']}")
```

## Available Tools

This template uses an external MCP server implementation. Tools are dynamically discovered at runtime.

Use the tool discovery methods above to see the full list of available tools for this template.

## Usage Examples

### Interactive CLI

```bash
# Start interactive mode
python -m mcp_platform interactive

# Deploy the template (if not already deployed)
mcpp> deploy slack

# List available tools after deployment
mcpp> tools slack
```

Example tool calls (replace with actual tool names discovered above):
```bash
# Example - replace 'tool_name' with actual tool from discovery
mcpp> call slack tool_name '{"param": "value"}'
```

### Regular CLI

```bash
# Deploy the template
python -m mcp_platform deploy slack

# Check deployment status
python -m mcp_platform status

# View logs
python -m mcp_platform logs slack

# Stop the template
python -m mcp_platform stop slack
```

### Python Client

```python
import asyncio
from mcp_platform.client import MCPClient

async def use_slack():
    async with MCPClient() as client:
        # Start the server
        deployment = await client.start_server("slack", {})
        
        if deployment["success"]:
            deployment_id = deployment["deployment_id"]
            
            try:
                # Discover available tools
                tools = await client.list_tools("slack")
                print(f"Available tools: {[t['name'] for t in tools]}")
                
                # Example tool call (replace with actual tool name)
                # result = await client.call_tool("slack", "tool_name", {"param": "value"})
                # print(f"Tool result: {result}")
                
            finally:
                # Clean up
                await client.stop_server(deployment_id)
        else:
            print("Failed to start server")

# Run the example
asyncio.run(use_slack())
```

## Integration Examples

### Claude Desktop

Add this configuration to your Claude Desktop configuration file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "slack": {
      "command": "python",
      "args": ["-m", "mcp_platform", "connect", "slack", "--stdio"],
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
    "slack": {
      "command": "python",
      "args": ["-m", "mcp_platform", "connect", "slack", "--stdio"],
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
python -m mcp_platform connect slack --llm claude
python -m mcp_platform connect slack --llm vscode
```

## Configuration

For template-specific configuration options, see the main template documentation. Common configuration methods:

```bash
# Deploy with configuration
python -m mcp_platform deploy slack --config key=value

# Deploy with environment variables  
python -m mcp_platform deploy slack --env KEY=VALUE

# Deploy with config file
python -m mcp_platform deploy slack --config-file config.json
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
   mcpp> tools slack --refresh
   ```

### Debug Mode

Enable debug logging for troubleshooting:

```bash
# Interactive CLI with debug
LOG_LEVEL=debug python -m mcp_platform interactive

# Deploy with debug logging
python -m mcp_platform deploy slack --config log_level=debug
```

For more help, see the [main documentation](../../) or open an issue in the repository.
