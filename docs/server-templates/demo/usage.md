# Demo Hello MCP Server Usage Guide

## Overview

This guide shows how to use the Demo Hello MCP Server with different MCP clients and integration methods.

## Tool Discovery

### Interactive CLI
```bash
# Start interactive mode
python -m mcp_platform interactive

# List available tools
mcpp> tools demo
```

### Regular CLI
```bash
# Discover tools using CLI
python -m mcp_platform tools demo
```

### Python Client
```python
from mcp_platform.client import MCPClient

async def discover_tools():
    async with MCPClient() as client:
        tools = await client.list_tools("demo")
        for tool in tools:
            print(f"Tool: {tool['name']} - {tool['description']}")
```

## Available Tools

### say_hello

**Description**: Generate a personalized greeting message

**Parameters**:
- `name` (string) (optional): Name of the person to greet (optional)

### get_server_info

**Description**: Get information about the demo server

**Parameters**:
- No parameters required

### echo_message

**Description**: Echo back a message with server identification

**Parameters**:
- `message` (string) (required): Message to echo back

## Usage Examples

### Interactive CLI

```bash
# Start interactive mode
python -m mcp_platform interactive

# Deploy the template (if not already deployed)
mcpp> deploy demo

# List available tools after deployment
mcpp> tools demo
```

Then call tools:
```bash
mcpp> call demo say_hello '{"name": "example_value"}'
```

```bash
mcpp> call demo get_server_info
```

```bash
mcpp> call demo echo_message '{"message": "example_value"}'
```

### Regular CLI

```bash
# Deploy the template
python -m mcp_platform deploy demo

# Check deployment status
python -m mcp_platform status

# View logs
python -m mcp_platform logs demo

# Stop the template
python -m mcp_platform stop demo
```

### Python Client

```python
import asyncio
from mcp_platform.client import MCPClient

async def use_demo():
    async with MCPClient() as client:
        # Start the server
        deployment = await client.start_server("demo", {})
        
        if deployment["success"]:
            deployment_id = deployment["deployment_id"]
            
            try:
                # Discover available tools
                tools = await client.list_tools("demo")
                print(f"Available tools: {[t['name'] for t in tools]}")
                
                # Call say_hello
                result = await client.call_tool("demo", "say_hello", {'name': 'example_value'})
                print(f"say_hello result: {result}")
                
                # Call get_server_info
                result = await client.call_tool("demo", "get_server_info", {})
                print(f"get_server_info result: {result}")
                
            finally:
                # Clean up
                await client.stop_server(deployment_id)
        else:
            print("Failed to start server")

# Run the example
asyncio.run(use_demo())
```

## Integration Examples

### Claude Desktop

Add this configuration to your Claude Desktop configuration file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "demo": {
      "command": "python",
      "args": ["-m", "mcp_platform", "connect", "demo", "--stdio"],
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
    "demo": {
      "command": "python",
      "args": ["-m", "mcp_platform", "connect", "demo", "--stdio"],
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
python -m mcp_platform connect demo --llm claude
python -m mcp_platform connect demo --llm vscode
```

## Configuration

For template-specific configuration options, see the main template documentation. Common configuration methods:

```bash
# Deploy with configuration
python -m mcp_platform deploy demo --config key=value

# Deploy with environment variables  
python -m mcp_platform deploy demo --env KEY=VALUE

# Deploy with config file
python -m mcp_platform deploy demo --config-file config.json
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
   mcpp> tools demo --refresh
   ```

### Debug Mode

Enable debug logging for troubleshooting:

```bash
# Interactive CLI with debug
LOG_LEVEL=debug python -m mcp_platform interactive

# Deploy with debug logging
python -m mcp_platform deploy demo --config log_level=debug
```

For more help, see the [main documentation](../../) or open an issue in the repository.
