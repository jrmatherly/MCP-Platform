# MCP Gateway API Reference

## Overview

The MCP Gateway provides a RESTful HTTP API for accessing and managing MCP (Model Context Protocol) server instances. All endpoints return JSON responses and follow standard HTTP status codes.

**Base URL**: `http://localhost:8080` (configurable)

## Authentication

Currently, the gateway does not require authentication. This may change in future versions with API key or JWT token support.

## Common Response Formats

### Success Response
```json
{
  "success": true,
  "data": { /* response data */ },
  "metadata": {
    "timestamp": "2025-08-30T12:00:00Z",
    "request_id": "req_abc123"
  }
}
```

### Error Response
```json
{
  "error": {
    "type": "ErrorType",
    "message": "Human readable error message",
    "details": { /* additional error context */ },
    "timestamp": "2025-08-30T12:00:00Z",
    "request_id": "req_abc123"
  }
}
```

## MCP Server Endpoints

All MCP server endpoints follow the pattern: `/mcp/{template_name}/{operation}`

### Tool Management

#### List Tools

Lists all available tools for a specific template.

```http
GET /mcp/{template_name}/tools/list
```

**Parameters:**
- `template_name` (path): Name of the MCP server template

**Response:**
```json
{
  "tools": [
    {
      "name": "read_file",
      "description": "Read the contents of a file",
      "category": "filesystem",
      "parameters": {
        "type": "object",
        "properties": {
          "path": {
            "type": "string",
            "description": "File path to read"
          }
        },
        "required": ["path"]
      }
    }
  ],
  "count": 1,
  "discovery_method": "static",
  "source": "http",
  "template": "filesystem",
  "_gateway_info": {
    "instance_id": "fs-http-1",
    "endpoint": "http://localhost:7071",
    "load_balancer_strategy": "round_robin"
  }
}
```

**Status Codes:**
- `200`: Success
- `404`: Template not found
- `502`: All instances unhealthy
- `503`: Service unavailable

**Example:**
```bash
curl -X GET http://localhost:8080/mcp/filesystem/tools/list
```

#### Call Tool

Executes a specific tool with provided arguments.

```http
POST /mcp/{template_name}/tools/call
```

**Parameters:**
- `template_name` (path): Name of the MCP server template

**Request Body:**
```json
{
  "name": "read_file",
  "arguments": {
    "path": "/etc/hosts"
  }
}
```

**Response:**
```json
{
  "content": [
    {
      "type": "text",
      "text": "127.0.0.1 localhost\n::1 localhost"
    }
  ],
  "structuredContent": {
    "result": "File contents here..."
  },
  "isError": false,
  "_gateway_info": {
    "instance_id": "fs-http-1",
    "endpoint": "http://localhost:7071",
    "execution_time_ms": 45
  }
}
```

**Status Codes:**
- `200`: Success
- `400`: Invalid tool name or arguments
- `404`: Template or tool not found
- `502`: Tool execution failed
- `503`: Service unavailable

**Example:**
```bash
curl -X POST http://localhost:8080/mcp/filesystem/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "name": "read_file",
    "arguments": {"path": "/etc/hosts"}
  }'
```

### Resource Management

#### List Resources

Lists all available resources for a specific template.

```http
GET /mcp/{template_name}/resources/list
```

**Parameters:**
- `template_name` (path): Name of the MCP server template

**Response:**
```json
{
  "resources": [
    {
      "uri": "file:///data/config.json",
      "name": "Configuration File",
      "description": "Application configuration",
      "mimeType": "application/json"
    }
  ],
  "count": 1,
  "_gateway_info": {
    "instance_id": "fs-http-1",
    "endpoint": "http://localhost:7071"
  }
}
```

**Example:**
```bash
curl -X GET http://localhost:8080/mcp/filesystem/resources/list
```

#### Read Resource

Reads the contents of a specific resource.

```http
POST /mcp/{template_name}/resources/read
```

**Request Body:**
```json
{
  "uri": "file:///data/config.json"
}
```

**Response:**
```json
{
  "contents": [
    {
      "uri": "file:///data/config.json",
      "mimeType": "application/json",
      "text": "{\"debug\": true, \"port\": 8080}"
    }
  ],
  "_gateway_info": {
    "instance_id": "fs-http-1",
    "endpoint": "http://localhost:7071"
  }
}
```

**Example:**
```bash
curl -X POST http://localhost:8080/mcp/filesystem/resources/read \
  -H "Content-Type: application/json" \
  -d '{"uri": "file:///data/config.json"}'
```

### Health Monitoring

#### Check Template Health

Returns health status for all instances of a template.

```http
GET /mcp/{template_name}/health
```

**Parameters:**
- `template_name` (path): Name of the MCP server template

**Response:**
```json
{
  "template_name": "filesystem",
  "total_instances": 3,
  "healthy_instances": 2,
  "health_percentage": 66.7,
  "instances": {
    "fs-http-1": {
      "healthy": true,
      "endpoint": "http://localhost:7071",
      "transport": "http",
      "status": "healthy",
      "consecutive_failures": 0,
      "last_health_check": "2025-08-30T12:00:00Z"
    },
    "fs-http-2": {
      "healthy": true,
      "endpoint": "http://localhost:7072",
      "transport": "http",
      "status": "healthy",
      "consecutive_failures": 0,
      "last_health_check": "2025-08-30T12:00:00Z"
    },
    "fs-stdio-1": {
      "healthy": false,
      "command": ["python", "server.py"],
      "transport": "stdio",
      "status": "unhealthy",
      "consecutive_failures": 3,
      "last_health_check": "2025-08-30T11:58:00Z"
    }
  }
}
```

**Example:**
```bash
curl -X GET http://localhost:8080/mcp/filesystem/health
```

## Gateway Management Endpoints

### Gateway Health

Returns the overall health status of the gateway itself.

```http
GET /gateway/health
```

**Response:**
```json
{
  "status": "healthy",
  "uptime_seconds": 3600.5,
  "total_requests": 1234,
  "registry_stats": {
    "total_templates": 3,
    "total_instances": 8,
    "healthy_instances": 6,
    "unhealthy_instances": 2
  },
  "health_checker_stats": {
    "running": true,
    "check_interval": 30,
    "timeout": 10,
    "total_checks": 240,
    "successful_checks": 180,
    "failed_checks": 60,
    "success_rate_percent": 75.0
  },
  "load_balancer_stats": {
    "total_requests": 1200,
    "default_strategy": "round_robin",
    "requests_per_instance": {
      "fs-http-1": 400,
      "fs-http-2": 300,
      "db-http-1": 500
    }
  }
}
```

**Example:**
```bash
curl -X GET http://localhost:8080/gateway/health
```

### Registry Information

Returns complete registry information including all templates and instances.

```http
GET /gateway/registry
```

**Response:**
```json
{
  "templates": {
    "filesystem": {
      "name": "filesystem",
      "instances": [
        {
          "id": "fs-http-1",
          "template_name": "filesystem",
          "endpoint": "http://localhost:7071",
          "transport": "http",
          "status": "healthy",
          "backend": "docker",
          "metadata": {"weight": 2},
          "last_health_check": "2025-08-30T12:00:00Z",
          "consecutive_failures": 0
        }
      ],
      "load_balancer": {
        "strategy": "round_robin",
        "health_check_interval": 30,
        "max_retries": 3,
        "timeout": 60
      }
    }
  },
  "stats": {
    "total_templates": 1,
    "total_instances": 1,
    "healthy_instances": 1,
    "unhealthy_instances": 0
  }
}
```

**Example:**
```bash
curl -X GET http://localhost:8080/gateway/registry
```

### Gateway Statistics

Returns comprehensive statistics about gateway performance and operations.

```http
GET /gateway/stats
```

**Response:**
```json
{
  "gateway": {
    "uptime_seconds": 3600.5,
    "total_requests": 1234,
    "request_timeout": 60,
    "max_retries": 3
  },
  "registry": {
    "total_templates": 3,
    "total_instances": 8,
    "healthy_instances": 6,
    "unhealthy_instances": 2,
    "templates": {
      "filesystem": {
        "total_instances": 3,
        "healthy_instances": 2,
        "load_balancer_strategy": "round_robin"
      }
    }
  },
  "health_checker": {
    "running": true,
    "check_interval": 30,
    "timeout": 10,
    "max_concurrent_checks": 10,
    "total_checks": 240,
    "successful_checks": 180,
    "failed_checks": 60,
    "success_rate_percent": 75.0,
    "last_check_time": "2025-08-30T12:00:00Z",
    "uptime_seconds": 3600.5
  },
  "load_balancer": {
    "default_strategy": "round_robin",
    "available_strategies": [
      "round_robin",
      "least_connections",
      "weighted",
      "health_based",
      "random"
    ],
    "total_requests": 1200,
    "requests_per_instance": {
      "fs-http-1": 400,
      "fs-http-2": 300,
      "db-http-1": 500
    },
    "strategy_stats": {
      "round_robin": {
        "name": "round_robin",
        "type": "RoundRobinStrategy"
      }
    }
  }
}
```

**Example:**
```bash
curl -X GET http://localhost:8080/gateway/stats
```

### Register Server Instance

Manually register a new server instance.

```http
POST /gateway/register
```

**Request Body:**
```json
{
  "template_name": "filesystem",
  "instance": {
    "id": "fs-new-1",
    "endpoint": "http://localhost:7073",
    "transport": "http",
    "backend": "docker",
    "metadata": {
      "weight": 1,
      "tier": "production"
    }
  }
}
```

**Response:**
```json
{
  "success": true,
  "message": "Instance fs-new-1 registered successfully",
  "instance_id": "fs-new-1",
  "template_name": "filesystem"
}
```

**Example:**
```bash
curl -X POST http://localhost:8080/gateway/register \
  -H "Content-Type: application/json" \
  -d '{
    "template_name": "filesystem",
    "instance": {
      "id": "fs-new-1",
      "endpoint": "http://localhost:7073",
      "transport": "http"
    }
  }'
```

### Deregister Server Instance

Remove a server instance from the registry.

```http
DELETE /gateway/deregister/{template_name}/{instance_id}
```

**Parameters:**
- `template_name` (path): Name of the template
- `instance_id` (path): ID of the instance to remove

**Response:**
```json
{
  "success": true,
  "message": "Deregistered instance fs-old-1 from template filesystem"
}
```

**Status Codes:**
- `200`: Success
- `404`: Instance not found

**Example:**
```bash
curl -X DELETE http://localhost:8080/gateway/deregister/filesystem/fs-old-1
```

## Error Handling

### HTTP Status Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 200 | OK | Request successful |
| 400 | Bad Request | Invalid request parameters or body |
| 404 | Not Found | Template, tool, or resource not found |
| 422 | Unprocessable Entity | Request validation failed |
| 500 | Internal Server Error | Unexpected server error |
| 502 | Bad Gateway | MCP server error or unavailable |
| 503 | Service Unavailable | No healthy instances available |
| 504 | Gateway Timeout | Request timeout exceeded |

### Error Response Details

#### Bad Request (400)
```json
{
  "error": {
    "type": "ValidationError",
    "message": "Missing required parameter 'name'",
    "details": {
      "field": "name",
      "provided": null,
      "required": true
    }
  }
}
```

#### Not Found (404)
```json
{
  "error": {
    "type": "TemplateNotFound",
    "message": "Template 'nonexistent' not found",
    "details": {
      "template": "nonexistent",
      "available_templates": ["filesystem", "database", "api"]
    }
  }
}
```

#### Service Unavailable (503)
```json
{
  "error": {
    "type": "NoHealthyInstances",
    "message": "No healthy instances available for template 'filesystem'",
    "details": {
      "template": "filesystem",
      "total_instances": 3,
      "healthy_instances": 0,
      "attempted_fallback": true
    }
  }
}
```

#### Gateway Timeout (504)
```json
{
  "error": {
    "type": "RequestTimeout",
    "message": "Request timeout exceeded (60 seconds)",
    "details": {
      "timeout_seconds": 60,
      "instance_id": "fs-http-1",
      "endpoint": "http://localhost:7071"
    }
  }
}
```

## Request/Response Headers

### Common Request Headers
```http
Content-Type: application/json
Accept: application/json
User-Agent: MCP-Client/1.0
```

### Common Response Headers
```http
Content-Type: application/json
X-Gateway-Version: 1.0.0
X-Request-ID: req_abc123
X-Instance-ID: fs-http-1
X-Load-Balancer-Strategy: round_robin
```

## Rate Limiting

Currently, no rate limiting is implemented. Future versions may include:
- Per-client rate limiting
- Per-template rate limiting
- Burst request handling
- Rate limit headers in responses

## Caching

The gateway implements minimal caching:
- Tool lists cached for 60 seconds
- Health check results cached for 30 seconds
- No caching for tool calls or resource reads

## WebSocket Support

WebSocket support is planned for future versions to enable:
- Real-time health status updates
- Streaming tool responses
- Live performance metrics
- Event notifications

## Batch Operations

Future API versions may support batch operations:

```http
POST /mcp/{template_name}/tools/batch
```

```json
{
  "operations": [
    {
      "id": "op1",
      "name": "read_file",
      "arguments": {"path": "/file1.txt"}
    },
    {
      "id": "op2",
      "name": "read_file",
      "arguments": {"path": "/file2.txt"}
    }
  ]
}
```

## SDK Examples

### Python Example
```python
import aiohttp
import asyncio

class MCPGatewayClient:
    def __init__(self, base_url="http://localhost:8080"):
        self.base_url = base_url
        self.session = None

    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()

    async def list_tools(self, template: str):
        async with self.session.get(f"{self.base_url}/mcp/{template}/tools/list") as resp:
            return await resp.json()

    async def call_tool(self, template: str, name: str, arguments: dict):
        payload = {"name": name, "arguments": arguments}
        async with self.session.post(
            f"{self.base_url}/mcp/{template}/tools/call",
            json=payload
        ) as resp:
            return await resp.json()

# Usage
async def main():
    async with MCPGatewayClient() as client:
        tools = await client.list_tools("filesystem")
        print(f"Available tools: {[t['name'] for t in tools['tools']]}")

        result = await client.call_tool(
            "filesystem",
            "read_file",
            {"path": "/etc/hosts"}
        )
        print(f"File contents: {result['content'][0]['text'][:100]}...")

asyncio.run(main())
```

### JavaScript Example
```javascript
class MCPGatewayClient {
    constructor(baseUrl = 'http://localhost:8080') {
        this.baseUrl = baseUrl;
    }

    async listTools(template) {
        const response = await fetch(`${this.baseUrl}/mcp/${template}/tools/list`);
        return await response.json();
    }

    async callTool(template, name, arguments) {
        const response = await fetch(`${this.baseUrl}/mcp/${template}/tools/call`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ name, arguments }),
        });
        return await response.json();
    }
}

// Usage
const client = new MCPGatewayClient();

client.listTools('filesystem')
    .then(tools => console.log('Available tools:', tools.tools.map(t => t.name)))
    .then(() => client.callTool('filesystem', 'read_file', { path: '/etc/hosts' }))
    .then(result => console.log('File contents:', result.content[0].text.substring(0, 100)));
```

### cURL Examples Collection

```bash
#!/bin/bash
# Gateway API examples

BASE_URL="http://localhost:8080"

echo "=== Gateway Health Check ==="
curl -s "$BASE_URL/gateway/health" | jq

echo -e "\n=== List Filesystem Tools ==="
curl -s "$BASE_URL/mcp/filesystem/tools/list" | jq '.tools[] | .name'

echo -e "\n=== Call Read File Tool ==="
curl -s -X POST "$BASE_URL/mcp/filesystem/tools/call" \
  -H "Content-Type: application/json" \
  -d '{"name": "read_file", "arguments": {"path": "/etc/hosts"}}' | jq

echo -e "\n=== Check Template Health ==="
curl -s "$BASE_URL/mcp/filesystem/health" | jq

echo -e "\n=== Gateway Statistics ==="
curl -s "$BASE_URL/gateway/stats" | jq '.load_balancer.total_requests'

echo -e "\n=== Registry Information ==="
curl -s "$BASE_URL/gateway/registry" | jq '.stats'
```

## OpenAPI Specification

The complete OpenAPI 3.0 specification is available at:
- **JSON**: `http://localhost:8080/openapi.json`
- **Interactive Docs**: `http://localhost:8080/docs`
- **ReDoc**: `http://localhost:8080/redoc`

This provides:
- Complete endpoint documentation
- Request/response schemas
- Interactive API testing
- Code generation support
- Validation rules

## Versioning

API versioning is planned for future releases:
- Header-based versioning: `X-API-Version: 1.0`
- URL-based versioning: `/v1/mcp/{template}/tools/list`
- Backwards compatibility guarantees
- Deprecation notices

## Support

For API support and questions:
- **Documentation**: [Gateway User Guide](../gateway/index.md)
- **Issues**: [GitHub Issues](https://github.com/Data-Everything/MCP-Platform/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Data-Everything/MCP-Platform/discussions)
