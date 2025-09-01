#!/usr/bin/env python3
"""
Generate Gateway API documentation from FastAPI OpenAPI schema.

This script generates static markdown documentation for the Gateway API.
"""

import sys
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent.parent))


def create_api_reference_content() -> str:
    """Create the complete API reference content."""
    return """# MCP Gateway API Reference

Enhanced unified HTTP gateway for Model Context Protocol servers with authentication, database persistence, and comprehensive management capabilities.

**Version**: 2.0.0

## Base URL

```
http://localhost:8000
```

## Authentication

The MCP Gateway supports multiple authentication methods:

### JWT Token Authentication

1. **Login to get a token:**
   ```bash
   curl -X POST "http://localhost:8000/auth/login" \\
     -H "Content-Type: application/x-www-form-urlencoded" \\
     -d "username=your_username&password=your_password"
   ```

2. **Use the token in requests:**
   ```bash
   curl -H "Authorization: Bearer YOUR_JWT_TOKEN" "http://localhost:8000/api/endpoint"
   ```

### API Key Authentication

1. **Create an API key** (requires admin access):
   ```bash
   curl -X POST "http://localhost:8000/auth/api-keys" \\
     -H "Authorization: Bearer YOUR_JWT_TOKEN" \\
     -H "Content-Type: application/json" \\
     -d '{"name": "my-api-key", "permissions": ["gateway:read", "tools:call"]}'
   ```

2. **Use the API key in requests:**
   ```bash
   curl -H "X-API-Key: YOUR_API_KEY" "http://localhost:8000/api/endpoint"
   ```

## Core API Endpoints

### Health Check

#### GET /health

Check the health status of the Gateway server.

**Parameters:** None

**Responses:**
- **200**: Health check response with server status
- **503**: Service unavailable

**Example:**
```bash
curl "http://localhost:8000/health"
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00Z",
  "uptime": 3600,
  "version": "2.0.0",
  "database": "connected",
  "mcp_servers": {
    "total": 5,
    "healthy": 4,
    "unhealthy": 1
  }
}
```

### Authentication Endpoints

#### POST /auth/login

Authenticate user and return JWT token.

**Request Body:**
- Content-Type: `application/x-www-form-urlencoded`
- `username` (string, required): Username
- `password` (string, required): Password

**Responses:**
- **200**: Successfully authenticated
- **401**: Invalid credentials

**Example:**
```bash
curl -X POST "http://localhost:8000/auth/login" \\
  -H "Content-Type: application/x-www-form-urlencoded" \\
  -d "username=admin&password=password"
```

#### POST /auth/users

Create a new user (admin only).

**Request Body:**
- Content-Type: `application/json`
- `username` (string, required): Unique username
- `email` (string, required): User email
- `password` (string, required): User password
- `is_superuser` (boolean, optional): Whether user has admin privileges

**Responses:**
- **201**: User created successfully
- **400**: Invalid input data
- **403**: Insufficient permissions

**Example:**
```bash
curl -X POST "http://localhost:8000/auth/users" \\
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{"username": "newuser", "email": "user@example.com", "password": "password123"}'
```

#### POST /auth/api-keys

Create a new API key.

**Request Body:**
- Content-Type: `application/json`
- `name` (string, required): Descriptive name for the API key
- `permissions` (array, required): List of permissions to grant
- `expires_at` (string, optional): ISO datetime when key expires

**Responses:**
- **201**: API key created successfully
- **400**: Invalid input data
- **403**: Insufficient permissions

**Example:**
```bash
curl -X POST "http://localhost:8000/auth/api-keys" \\
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{"name": "my-service-key", "permissions": ["gateway:read", "tools:call"]}'
```

### Server Management

#### GET /servers

List all registered MCP servers.

**Parameters:**
- `include_health` (query, boolean): Include health status in response

**Responses:**
- **200**: List of registered servers
- **403**: Insufficient permissions

**Example:**
```bash
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \\
  "http://localhost:8000/servers?include_health=true"
```

#### POST /servers

Register a new MCP server.

**Request Body:**
- Content-Type: `application/json`
- `template_name` (string, required): Template identifier
- `instance_metadata` (object, optional): Additional metadata
- `config` (object, optional): Server configuration

**Responses:**
- **201**: Server registered successfully
- **400**: Invalid server configuration
- **403**: Insufficient permissions

**Example:**
```bash
curl -X POST "http://localhost:8000/servers" \\
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{"template_name": "file-server", "config": {"base_path": "/data"}}'
```

#### GET /servers/{server_id}

Get details of a specific server.

**Parameters:**
- `server_id` (path, string): Server identifier

**Responses:**
- **200**: Server details
- **404**: Server not found
- **403**: Insufficient permissions

**Example:**
```bash
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \\
  "http://localhost:8000/servers/server-123"
```

#### DELETE /servers/{server_id}

Unregister a server.

**Parameters:**
- `server_id` (path, string): Server identifier

**Responses:**
- **204**: Server unregistered successfully
- **404**: Server not found
- **403**: Insufficient permissions

**Example:**
```bash
curl -X DELETE \\
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \\
  "http://localhost:8000/servers/server-123"
```

### Tool Execution

#### POST /tools/call

Execute a tool on an MCP server.

**Request Body:**
- Content-Type: `application/json`
- `server_id` (string, required): Target server identifier
- `tool_name` (string, required): Name of tool to execute
- `arguments` (object, optional): Tool arguments

**Responses:**
- **200**: Tool executed successfully
- **400**: Invalid tool request
- **404**: Server or tool not found
- **403**: Insufficient permissions
- **500**: Tool execution failed

**Example:**
```bash
curl -X POST "http://localhost:8000/tools/call" \\
  -H "Authorization: Bearer YOUR_JWT_TOKEN" \\
  -H "Content-Type: application/json" \\
  -d '{
    "server_id": "file-server-1",
    "tool_name": "read_file",
    "arguments": {"path": "/data/example.txt"}
  }'
```

### Gateway Statistics

#### GET /stats

Get gateway performance and usage statistics.

**Responses:**
- **200**: Gateway statistics
- **403**: Insufficient permissions

**Example:**
```bash
curl -H "Authorization: Bearer YOUR_JWT_TOKEN" \\
  "http://localhost:8000/stats"
```

**Response:**
```json
{
  "uptime": 3600,
  "total_requests": 1250,
  "active_servers": 5,
  "healthy_servers": 4,
  "load_balancer": {
    "strategy": "round_robin",
    "total_requests": 1000,
    "requests_per_server": {
      "server-1": 250,
      "server-2": 250,
      "server-3": 250,
      "server-4": 250
    }
  }
}
```

## Authentication Scopes

The Gateway uses a permission-based authentication system with the following scopes:

- `gateway:read` - Read gateway status and configuration
- `gateway:write` - Modify gateway configuration and manage servers
- `tools:call` - Execute tools on MCP servers
- `admin` - Full administrative access

## Error Handling

All endpoints return standardized error responses:

```json
{
  "detail": "Error description",
  "error_code": "SPECIFIC_ERROR_CODE",
  "request_id": "unique-request-identifier"
}
```

### Common HTTP Status Codes

- `200` - Success
- `201` - Created
- `204` - No Content (successful deletion)
- `400` - Bad Request (invalid parameters)
- `401` - Unauthorized (authentication required)
- `403` - Forbidden (insufficient permissions)
- `404` - Not Found
- `422` - Validation Error
- `500` - Internal Server Error
- `503` - Service Unavailable

### Error Response Examples

**Authentication Error:**
```json
{
  "detail": "Could not validate credentials",
  "error_code": "INVALID_TOKEN"
}
```

**Permission Error:**
```json
{
  "detail": "Insufficient permissions for this operation",
  "error_code": "INSUFFICIENT_PERMISSIONS",
  "required_permissions": ["gateway:write"]
}
```

**Validation Error:**
```json
{
  "detail": [
    {
      "loc": ["body", "server_id"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ],
  "error_code": "VALIDATION_ERROR"
}
```

## Rate Limiting

The Gateway implements rate limiting to prevent abuse:

- **Authenticated users**: 1000 requests per hour
- **API key users**: 5000 requests per hour
- **Admin users**: No limit

### Rate Limit Headers

Rate limit information is included in response headers:

- `X-RateLimit-Limit` - Maximum requests allowed in current window
- `X-RateLimit-Remaining` - Requests remaining in current window
- `X-RateLimit-Reset` - Unix timestamp when rate limit resets

**Example Response Headers:**
```
X-RateLimit-Limit: 1000
X-RateLimit-Remaining: 950
X-RateLimit-Reset: 1609459200
```

## Database Modes

The Gateway supports multiple database backends:

### SQLite (Development)
```bash
# Start with SQLite database
python -m mcp_platform.gateway --database-url sqlite:///gateway.db
```

### PostgreSQL (Production)
```bash
# Start with PostgreSQL
python -m mcp_platform.gateway --database-url postgresql://user:pass@localhost/gateway
```

### Memory Mode (Testing)
```bash
# Start with in-memory database
python -m mcp_platform.gateway --database-url sqlite:///:memory:
```

## Configuration Options

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GATEWAY_HOST` | Server host address | `0.0.0.0` |
| `GATEWAY_PORT` | Server port | `8000` |
| `GATEWAY_DATABASE_URL` | Database connection URL | `sqlite:///gateway.db` |
| `GATEWAY_SECRET_KEY` | JWT signing secret | Auto-generated |
| `GATEWAY_AUTH_ENABLED` | Enable authentication | `true` |
| `GATEWAY_ADMIN_PASSWORD` | Default admin password | Auto-generated |
| `GATEWAY_CORS_ORIGINS` | Allowed CORS origins | `*` |

### Configuration File

Create a `gateway.yaml` configuration file:

```yaml
host: "0.0.0.0"
port: 8000
database_url: "postgresql://user:pass@localhost/gateway"
auth:
  enabled: true
  secret_key: "your-secret-key"
  access_token_expire_minutes: 60
cors_origins:
  - "http://localhost:3000"
  - "https://your-frontend.com"
load_balancer:
  strategy: "round_robin"
  health_check_interval: 30
```

## SDK Usage

### Python Client

```python
import asyncio
from mcp_platform.gateway.client import GatewayClient

async def main():
    # Initialize client
    client = GatewayClient("http://localhost:8000")

    # Authenticate
    await client.login("username", "password")

    # List servers
    servers = await client.list_servers()
    print(f"Active servers: {len(servers)}")

    # Execute a tool
    result = await client.call_tool(
        server_id="file-server-1",
        tool_name="read_file",
        arguments={"path": "/data/example.txt"}
    )
    print(f"Tool result: {result}")

asyncio.run(main())
```

### API Key Usage

```python
from mcp_platform.gateway.client import GatewayClient

# Initialize with API key
client = GatewayClient("http://localhost:8000", api_key="your-api-key")

# Use client normally - authentication is handled automatically
servers = await client.list_servers()
```
"""


def generate_gateway_api_docs():
    """Generate Gateway API documentation."""
    print("📝 Generating Gateway API documentation...")

    try:
        # Create the markdown content
        markdown_content = create_api_reference_content()

        print("✅ Generated markdown content")

        # Save to docs directory
        docs_dir = Path(__file__).parent.parent / "docs" / "gateway"
        docs_dir.mkdir(exist_ok=True)

        api_docs_file = docs_dir / "api-reference.md"
        with open(api_docs_file, "w", encoding="utf-8") as f:
            f.write(markdown_content)

        print(f"✅ Generated Gateway API documentation: {api_docs_file}")

    except Exception as e:
        print(f"❌ Error generating Gateway API docs: {e}")
        raise


if __name__ == "__main__":
    generate_gateway_api_docs()
