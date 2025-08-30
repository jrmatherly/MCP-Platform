# MCP Gateway

## What is the MCP Gateway?

The **MCP Gateway** is a unified load balancer and proxy system that provides a single entry point for accessing all MCP (Model Context Protocol) server instances in your deployment. Instead of connecting to each MCP server individually, clients can connect to the gateway and it will automatically route requests to the appropriate healthy instances.

## Why is the Gateway Needed?

### Problems with Direct MCP Server Access

Before the gateway, clients had to:

1. **Manage Multiple Connections**: Each MCP server template required a separate connection
2. **Handle Load Balancing Manually**: No automatic distribution across multiple instances
3. **Implement Health Checking**: Clients needed to detect and handle server failures
4. **Deal with Service Discovery**: Finding and tracking available server instances
5. **Handle Failover Logic**: Manual switching when servers become unavailable

### Benefits of Using the Gateway

The MCP Gateway solves these problems by providing:

✅ **Single Endpoint**: One URL for all MCP server access
✅ **Automatic Load Balancing**: Intelligent request distribution
✅ **Health Monitoring**: Continuous health checking with automatic failover
✅ **Service Discovery**: Automatic detection of available instances
✅ **Transport Abstraction**: Unified access to both HTTP and stdio servers
✅ **High Availability**: No single point of failure

## How It Works

### High-Level Architecture

```
┌─────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Client    │───▶│   MCP Gateway   │───▶│  MCP Servers    │
│             │    │                 │    │                 │
│ Single URL  │    │ • Load Balancer │    │ • Instance 1    │
│ One API     │    │ • Health Check  │    │ • Instance 2    │
│             │    │ • Registry      │    │ • Instance N    │
└─────────────┘    └─────────────────┘    └─────────────────┘
```

### Core Components

1. **Gateway Server**: FastAPI-based HTTP server that receives requests
2. **Registry**: Maintains state of all registered server instances
3. **Load Balancer**: Routes requests using various strategies
4. **Health Checker**: Monitors server health and removes unhealthy instances
5. **Integration Layer**: Syncs with existing MCP Platform deployments

### Request Flow

1. **Client Request**: Client sends request to `/mcp/{template}/tools/list`
2. **Template Resolution**: Gateway identifies the target template
3. **Instance Selection**: Load balancer selects healthy instance
4. **Request Routing**: Gateway forwards request to selected instance
5. **Response Handling**: Gateway returns response to client

## Gateway Endpoints

### Core MCP Operations

All MCP operations follow the pattern: `/mcp/{template_name}/{operation}`

#### Tool Management
```http
GET  /mcp/{template}/tools/list     # List available tools
POST /mcp/{template}/tools/call     # Call a specific tool
```

#### Resource Management
```http
GET  /mcp/{template}/resources/list # List available resources
POST /mcp/{template}/resources/read # Read a specific resource
```

#### Health Monitoring
```http
GET  /mcp/{template}/health         # Check template health
```

### Gateway Management

#### System Information
```http
GET  /gateway/health                # Gateway health status
GET  /gateway/stats                 # Comprehensive statistics
GET  /gateway/registry              # Registry information
```

#### Instance Management
```http
POST   /gateway/register            # Register new server instance
DELETE /gateway/deregister/{template}/{instance_id}  # Remove instance
```

## API Documentation

### Swagger/OpenAPI Documentation

When the gateway is running, you can access interactive API documentation at:
- **Swagger UI**: `http://localhost:8080/docs`
- **ReDoc**: `http://localhost:8080/redoc`
- **OpenAPI JSON**: `http://localhost:8080/openapi.json`

### Example API Calls

#### List Tools
```bash
curl -X GET http://localhost:8080/mcp/filesystem/tools/list
```

Response:
```json
{
  "tools": [
    {
      "name": "read_file",
      "description": "Read the contents of a file",
      "parameters": {
        "type": "object",
        "properties": {
          "path": {"type": "string", "description": "File path"}
        }
      }
    }
  ],
  "count": 1
}
```

#### Call Tool
```bash
curl -X POST http://localhost:8080/mcp/filesystem/tools/call \
  -H "Content-Type: application/json" \
  -d '{
    "name": "read_file",
    "arguments": {"path": "/etc/hosts"}
  }'
```

Response:
```json
{
  "content": [
    {
      "type": "text",
      "text": "127.0.0.1 localhost\n..."
    }
  ],
  "isError": false
}
```

#### Check Health
```bash
curl -X GET http://localhost:8080/mcp/filesystem/health
```

Response:
```json
{
  "template_name": "filesystem",
  "total_instances": 3,
  "healthy_instances": 2,
  "health_percentage": 66.7,
  "instances": {
    "fs-1": {"healthy": true, "status": "healthy"},
    "fs-2": {"healthy": true, "status": "healthy"},
    "fs-3": {"healthy": false, "status": "unhealthy"}
  }
}
```

## Getting Started

### 1. Start the Gateway

```bash
# Basic startup (auto-discovers existing deployments)
mcpp gateway start

# Custom configuration
mcpp gateway start --host 0.0.0.0 --port 8080 --sync

# Background mode
mcpp gateway start --background
```

### 2. Verify Gateway is Running

```bash
# Check health
curl http://localhost:8080/gateway/health

# View registered instances
curl http://localhost:8080/gateway/registry
```

### 3. Register MCP Servers (if needed)

```bash
# Register HTTP server
mcpp gateway register mytemplate --endpoint http://localhost:7071

# Register stdio server
mcpp gateway register mytemplate --command "python server.py" --working-dir /app
```

### 4. Use the Gateway

```python
import aiohttp
import asyncio

async def use_gateway():
    async with aiohttp.ClientSession() as session:
        # List tools
        async with session.get("http://localhost:8080/mcp/filesystem/tools/list") as resp:
            tools = await resp.json()
            print(f"Available tools: {len(tools['tools'])}")

        # Call a tool
        async with session.post(
            "http://localhost:8080/mcp/filesystem/tools/call",
            json={"name": "read_file", "arguments": {"path": "/etc/hosts"}}
        ) as resp:
            result = await resp.json()
            print(f"Tool result: {result['content'][0]['text'][:100]}...")

asyncio.run(use_gateway())
```

## Load Balancing Strategies

The gateway supports multiple load balancing strategies:

### 1. Round Robin (Default)
Distributes requests evenly across all healthy instances.
```bash
Instance 1 → Instance 2 → Instance 3 → Instance 1 → ...
```

### 2. Least Connections
Routes to the instance with the fewest active connections.
```bash
Request → Instance with 2 connections (vs others with 5, 3, 4)
```

### 3. Weighted Round Robin
Routes based on instance weights (higher weight = more requests).
```bash
Weight 3: Instance A gets 3 requests
Weight 1: Instance B gets 1 request
```

### 4. Health-Based
Prefers instances with better health scores.
```bash
Request → Instance with 100% health (vs others with 80%, 90%)
```

### 5. Random
Randomly selects from healthy instances.
```bash
Request → Random(Instance 1, Instance 2, Instance 3)
```

## Configuration

### Template Configuration

Templates can be configured with specific load balancing settings:

```json
{
  "templates": {
    "high-performance": {
      "instances": [...],
      "load_balancer": {
        "strategy": "weighted",
        "health_check_interval": 15,
        "max_retries": 2,
        "timeout": 30
      }
    }
  }
}
```

### Environment Variables

```bash
# Gateway server settings
MCP_GATEWAY_HOST=0.0.0.0
MCP_GATEWAY_PORT=8080
MCP_GATEWAY_REGISTRY_FILE=/path/to/registry.json

# Health checking
MCP_GATEWAY_HEALTH_INTERVAL=30
MCP_GATEWAY_HEALTH_TIMEOUT=10

# Load balancing
MCP_GATEWAY_DEFAULT_STRATEGY=round_robin
MCP_GATEWAY_MAX_RETRIES=3
```

## Monitoring and Observability

### Health Endpoints

```bash
# Gateway health
curl http://localhost:8080/gateway/health

# Template health
curl http://localhost:8080/mcp/filesystem/health

# Detailed statistics
curl http://localhost:8080/gateway/stats | jq
```

### Key Metrics

- **Request Count**: Total requests processed
- **Response Time**: Average response latency
- **Error Rate**: Failed request percentage
- **Instance Health**: Per-instance health status
- **Load Distribution**: Requests per instance

### Logging

The gateway provides structured logging for:
- Request routing decisions
- Health check results
- Load balancer selections
- Error conditions
- Performance metrics

## Troubleshooting

### Common Issues

#### Gateway Not Starting
```bash
# Check port availability
netstat -tlnp | grep 8080

# View detailed logs
mcpp gateway start --log-level debug
```

#### No Instances Available
```bash
# Check registry
curl http://localhost:8080/gateway/registry

# Sync with deployments
mcpp gateway sync

# Manual registration
mcpp gateway register mytemplate --endpoint http://localhost:7071
```

#### Health Check Failures
```bash
# Check instance health
curl http://localhost:8080/mcp/mytemplate/health

# View health checker stats
curl http://localhost:8080/gateway/stats | jq '.health_checker'
```

### Debug Mode

Enable debug logging for detailed troubleshooting:

```bash
mcpp gateway start --log-level debug
```

This provides detailed information about:
- Request routing decisions
- Load balancer selections
- Health check processes
- Error handling

## Best Practices

### 1. Health Check Configuration
- Set appropriate health check intervals (30-60 seconds)
- Configure timeouts based on server response times
- Use health-based load balancing for critical services

### 2. Load Balancing Strategy Selection
- **Round Robin**: General purpose, evenly distributed load
- **Least Connections**: Connection-heavy workloads
- **Weighted**: Different instance capabilities
- **Health-Based**: High availability requirements

### 3. Instance Management
- Register instances with meaningful metadata
- Use consistent naming conventions
- Monitor instance health regularly
- Plan for graceful degradation

### 4. Client Integration
- Implement proper error handling
- Use connection pooling
- Cache tool lists when appropriate
- Handle gateway unavailability

## Security Considerations

### 1. Network Security
- Deploy gateway behind load balancer/reverse proxy
- Use HTTPS in production
- Implement network segmentation
- Restrict access to management endpoints

### 2. Authentication
- Consider implementing authentication middleware
- Use API keys for service-to-service communication
- Implement rate limiting
- Log security events

### 3. Instance Security
- Validate registered instances
- Implement instance authentication
- Monitor for suspicious activity
- Regular security updates

## Migration Guide

### From Direct MCP Access

1. **Assess Current Setup**: Inventory existing MCP server connections
2. **Deploy Gateway**: Start gateway and sync with existing deployments
3. **Update Clients**: Modify client code to use gateway endpoints
4. **Test and Validate**: Verify functionality with gateway
5. **Monitor and Optimize**: Monitor performance and adjust configuration

### Client Code Changes

Before (Direct Access):
```python
# Connect to each server individually
fs_client = MCPClient("http://localhost:7071")
db_client = MCPClient("http://localhost:7072")
```

After (Gateway Access):
```python
# Single gateway connection
gateway_client = MCPClient("http://localhost:8080")
# Use /mcp/{template}/* endpoints
```

## Advanced Topics

### Custom Health Checks
Implement custom health check logic for specific templates.

### Circuit Breaker Pattern
Automatic failure isolation and recovery for resilient systems.

### Request Transformation
Modify requests/responses as they pass through the gateway.

### Multi-Region Deployment
Deploy gateways across multiple regions for global availability.

## Support and Community

- **Documentation**: [MCP Platform Docs](https://docs.mcpplatform.com)
- **Issues**: [GitHub Issues](https://github.com/Data-Everything/MCP-Platform/issues)
- **Discussions**: [GitHub Discussions](https://github.com/Data-Everything/MCP-Platform/discussions)
- **Examples**: [Gateway Examples](https://github.com/Data-Everything/MCP-Platform/tree/main/examples/gateway)
