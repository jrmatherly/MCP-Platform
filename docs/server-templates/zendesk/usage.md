# Zendesk MCP Server Usage Guide

## Overview

This guide shows how to use the Zendesk MCP Server with different MCP clients and integration methods.

## Tool Discovery

### Interactive CLI
```bash
# Start interactive mode
python -m mcp_platform interactive

# List available tools
mcpp> tools zendesk
```

### Regular CLI
```bash
# Discover tools using CLI
python -m mcp_platform tools zendesk
```

### Python Client
```python
from mcp_platform.client import MCPClient

async def discover_tools():
    async with MCPClient() as client:
        tools = await client.list_tools("zendesk")
        for tool in tools:
            print(f"Tool: {tool['name']} - {tool['description']}")
```

## Available Tools

### create_ticket

**Description**: Create a new support ticket in Zendesk

**Parameters**:
- `subject` (string) (required): Subject/title of the ticket
- `description` (string) (required): Initial description or comment for the ticket
- `requester_email` (string) (optional): Email address of the person requesting support
- `priority` (string) (optional): Priority level of the ticket
- `type` (string) (optional): Type of the ticket
- `tags` (array) (optional): Tags to associate with the ticket

### get_ticket

**Description**: Retrieve detailed information about a specific ticket

**Parameters**:
- `ticket_id` (integer) (required): ID of the ticket to retrieve
- `include_comments` (boolean) (optional): Include ticket comments in the response

### update_ticket

**Description**: Update an existing ticket's properties

**Parameters**:
- `ticket_id` (integer) (required): ID of the ticket to update
- `status` (string) (optional): New status for the ticket
- `priority` (string) (optional): New priority for the ticket
- `assignee_id` (integer) (optional): ID of the agent to assign the ticket to
- `tags` (array) (optional): Tags to add or update on the ticket

### search_tickets

**Description**: Search for tickets using various criteria

**Parameters**:
- `query` (string) (optional): Search query using Zendesk search syntax
- `status` (string) (optional): Filter by ticket status
- `priority` (string) (optional): Filter by ticket priority
- `requester_email` (string) (optional): Filter by requester email address
- `created_after` (string) (optional): Filter tickets created after this date (ISO format)
- `limit` (integer) (optional): Maximum number of tickets to return

### add_ticket_comment

**Description**: Add a comment to an existing ticket

**Parameters**:
- `ticket_id` (integer) (required): ID of the ticket to comment on
- `body` (string) (required): Content of the comment
- `public` (boolean) (optional): Whether the comment is public (visible to requester) or internal
- `author_id` (integer) (optional): ID of the comment author (defaults to authenticated user)

### create_user

**Description**: Create a new user in Zendesk

**Parameters**:
- `name` (string) (required): Full name of the user
- `email` (string) (required): Email address of the user
- `role` (string) (optional): Role for the user
- `organization_id` (integer) (optional): ID of the organization to associate the user with

### get_user

**Description**: Retrieve information about a specific user

**Parameters**:
- `user_id` (integer) (optional): ID of the user to retrieve
- `email` (string) (optional): Email address of the user to retrieve

### search_users

**Description**: Search for users in Zendesk

**Parameters**:
- `query` (string) (optional): Search query for users
- `role` (string) (optional): Filter by user role
- `organization_id` (integer) (optional): Filter by organization ID

### search_articles

**Description**: Search knowledge base articles

**Parameters**:
- `query` (string) (required): Search query for articles
- `locale` (string) (optional): Language locale for articles
- `section_id` (integer) (optional): Filter by specific section ID

### get_article

**Description**: Retrieve a specific knowledge base article

**Parameters**:
- `article_id` (integer) (required): ID of the article to retrieve
- `locale` (string) (optional): Language locale for the article

### get_ticket_metrics

**Description**: Get metrics and analytics for tickets

**Parameters**:
- `start_date` (string) (optional): Start date for metrics (ISO format)
- `end_date` (string) (optional): End date for metrics (ISO format)
- `group_by` (string) (optional): Group metrics by specific field

### list_organizations

**Description**: List organizations in Zendesk

**Parameters**:
- `query` (string) (optional): Search query for organizations

## Usage Examples

### Interactive CLI

```bash
# Start interactive mode
python -m mcp_platform interactive

# Deploy the template (if not already deployed)
mcpp> deploy zendesk

# List available tools after deployment
mcpp> tools zendesk
```

Then call tools:
```bash
mcpp> call zendesk create_ticket '{"subject": "example_value", "description": "example_value", "requester_email": "example_value", "priority": "example_value", "type": "example_value", "tags": "example_value"}'
```

```bash
mcpp> call zendesk get_ticket '{"ticket_id": "example_value", "include_comments": true}'
```

```bash
mcpp> call zendesk update_ticket '{"ticket_id": "example_value", "status": "example_value", "priority": "example_value", "assignee_id": "example_value", "tags": "example_value"}'
```

### Regular CLI

```bash
# Deploy the template
python -m mcp_platform deploy zendesk

# Check deployment status
python -m mcp_platform status

# View logs
python -m mcp_platform logs zendesk

# Stop the template
python -m mcp_platform stop zendesk
```

### Python Client

```python
import asyncio
from mcp_platform.client import MCPClient

async def use_zendesk():
    async with MCPClient() as client:
        # Start the server
        deployment = await client.start_server("zendesk", {})
        
        if deployment["success"]:
            deployment_id = deployment["deployment_id"]
            
            try:
                # Discover available tools
                tools = await client.list_tools("zendesk")
                print(f"Available tools: {[t['name'] for t in tools]}")
                
                # Call create_ticket
                result = await client.call_tool("zendesk", "create_ticket", {'subject': 'example_value', 'description': 'example_value', 'requester_email': 'example_value', 'priority': 'example_value', 'type': 'example_value', 'tags': 'example_value'})
                print(f"create_ticket result: {result}")
                
                # Call get_ticket
                result = await client.call_tool("zendesk", "get_ticket", {'ticket_id': 'example_value', 'include_comments': True})
                print(f"get_ticket result: {result}")
                
            finally:
                # Clean up
                await client.stop_server(deployment_id)
        else:
            print("Failed to start server")

# Run the example
asyncio.run(use_zendesk())
```

## Integration Examples

### Claude Desktop

Add this configuration to your Claude Desktop configuration file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "zendesk": {
      "command": "python",
      "args": ["-m", "mcp_platform", "connect", "zendesk", "--stdio"],
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
    "zendesk": {
      "command": "python",
      "args": ["-m", "mcp_platform", "connect", "zendesk", "--stdio"],
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
python -m mcp_platform connect zendesk --llm claude
python -m mcp_platform connect zendesk --llm vscode
```

## Configuration

For template-specific configuration options, see the main template documentation. Common configuration methods:

```bash
# Deploy with configuration
python -m mcp_platform deploy zendesk --config key=value

# Deploy with environment variables  
python -m mcp_platform deploy zendesk --env KEY=VALUE

# Deploy with config file
python -m mcp_platform deploy zendesk --config-file config.json
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
   mcpp> tools zendesk --refresh
   ```

### Debug Mode

Enable debug logging for troubleshooting:

```bash
# Interactive CLI with debug
LOG_LEVEL=debug python -m mcp_platform interactive

# Deploy with debug logging
python -m mcp_platform deploy zendesk --config log_level=debug
```

For more help, see the [main documentation](../../) or open an issue in the repository.
