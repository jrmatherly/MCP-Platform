# BigQuery MCP Server Usage Guide

## Overview

This guide shows how to use the BigQuery MCP Server with different MCP clients and integration methods.

## Tool Discovery

### Interactive CLI
```bash
# Start interactive mode
python -m mcp_platform interactive

# List available tools
mcpp> tools bigquery
```

### Regular CLI
```bash
# Discover tools using CLI
python -m mcp_platform tools bigquery
```

### Python Client
```python
from mcp_platform.client import MCPClient

async def discover_tools():
    async with MCPClient() as client:
        tools = await client.list_tools("bigquery")
        for tool in tools:
            print(f"Tool: {tool['name']} - {tool['description']}")
```

## Available Tools

### list_datasets

**Description**: List all accessible BigQuery datasets in the project

**Parameters**:
- No parameters required

### list_tables

**Description**: List tables in a specific dataset

**Parameters**:
- `dataset_id` (string) (required): Dataset ID to list tables from

### describe_table

**Description**: Get detailed schema information for a table

**Parameters**:
- `dataset_id` (string) (required): Dataset ID containing the table
- `table_id` (string) (required): Table ID to describe

### execute_query

**Description**: Execute a SQL query against BigQuery (subject to read-only restrictions)

**Parameters**:
- `query` (string) (required): SQL query to execute
- `dry_run` (boolean) (optional): Validate query without executing (default: false)

### get_job_status

**Description**: Get status of a BigQuery job

**Parameters**:
- `job_id` (string) (required): BigQuery job ID to check

### get_dataset_info

**Description**: Get detailed information about a dataset

**Parameters**:
- `dataset_id` (string) (required): Dataset ID to get information for

## Usage Examples

### Interactive CLI

```bash
# Start interactive mode
python -m mcp_platform interactive

# Deploy the template (if not already deployed)
mcpp> deploy bigquery

# List available tools after deployment
mcpp> tools bigquery
```

Then call tools:
```bash
mcpp> call bigquery list_datasets
```

```bash
mcpp> call bigquery list_tables '{"dataset_id": "example_value"}'
```

```bash
mcpp> call bigquery describe_table '{"dataset_id": "example_value", "table_id": "example_value"}'
```

### Regular CLI

```bash
# Deploy the template
python -m mcp_platform deploy bigquery

# Check deployment status
python -m mcp_platform status

# View logs
python -m mcp_platform logs bigquery

# Stop the template
python -m mcp_platform stop bigquery
```

### Python Client

```python
import asyncio
from mcp_platform.client import MCPClient

async def use_bigquery():
    async with MCPClient() as client:
        # Start the server
        deployment = await client.start_server("bigquery", {})
        
        if deployment["success"]:
            deployment_id = deployment["deployment_id"]
            
            try:
                # Discover available tools
                tools = await client.list_tools("bigquery")
                print(f"Available tools: {[t['name'] for t in tools]}")
                
                # Call list_datasets
                result = await client.call_tool("bigquery", "list_datasets", {})
                print(f"list_datasets result: {result}")
                
                # Call list_tables
                result = await client.call_tool("bigquery", "list_tables", {'dataset_id': 'example_value'})
                print(f"list_tables result: {result}")
                
            finally:
                # Clean up
                await client.stop_server(deployment_id)
        else:
            print("Failed to start server")

# Run the example
asyncio.run(use_bigquery())
```

## Integration Examples

### Claude Desktop

Add this configuration to your Claude Desktop configuration file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "bigquery": {
      "command": "python",
      "args": ["-m", "mcp_platform", "connect", "bigquery", "--stdio"],
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
    "bigquery": {
      "command": "python",
      "args": ["-m", "mcp_platform", "connect", "bigquery", "--stdio"],
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
python -m mcp_platform connect bigquery --llm claude
python -m mcp_platform connect bigquery --llm vscode
```

## Configuration

For template-specific configuration options, see the main template documentation. Common configuration methods:

```bash
# Deploy with configuration
python -m mcp_platform deploy bigquery --config key=value

# Deploy with environment variables  
python -m mcp_platform deploy bigquery --env KEY=VALUE

# Deploy with config file
python -m mcp_platform deploy bigquery --config-file config.json
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
   mcpp> tools bigquery --refresh
   ```

### Debug Mode

Enable debug logging for troubleshooting:

```bash
# Interactive CLI with debug
LOG_LEVEL=debug python -m mcp_platform interactive

# Deploy with debug logging
python -m mcp_platform deploy bigquery --config log_level=debug
```

For more help, see the [main documentation](../../) or open an issue in the repository.
