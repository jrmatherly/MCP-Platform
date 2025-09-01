# Gateway Quick Setup Guide

This guide will get you up and running with the MCP Gateway in under 5 minutes.

## Prerequisites

- MCP Platform installed (`pip install mcp-platform`)
- At least one MCP server template deployed
- Python 3.11+

## Step 1: Deploy Some MCP Servers

First, let's deploy a few MCP servers to demonstrate the gateway:

```bash
# Deploy demo servers (multiple instances for demonstration)
mcpp deploy demo
mcpp deploy demo  # Deploy a second instance
mcpp deploy demo  # Deploy a third instance

# Deploy filesystem server
mcpp deploy filesystem

# Check running deployments
mcpp list
```

## Step 2: Start the Gateway

Start the gateway with automatic discovery of existing deployments:

```bash
# Basic startup with auto-discovery
mcpp gateway start --sync

# Custom host/port
mcpp gateway start --host 0.0.0.0 --port 8080 --sync

# Background mode
mcpp gateway start --background --sync
```

The gateway will:
- Automatically discover all running MCP instances
- Register them in the internal registry
- Start health monitoring
- Begin accepting requests

## Step 3: Verify Gateway is Running

Check that the gateway is healthy and has discovered your instances:

```bash
# Check gateway health
curl http://localhost:8080/gateway/health

# View registered instances
curl http://localhost:8080/gateway/registry | jq

# Check specific template health
curl http://localhost:8080/mcp/demo/health
```

## Step 4: Use the Gateway

Now you can access all your MCP servers through the unified gateway endpoint:

### List Tools
```bash
# List tools from any template
curl http://localhost:8080/mcp/demo/tools/list
curl http://localhost:8080/mcp/filesystem/tools/list
```

### Call Tools
```bash
# Call tools through the gateway (load balanced automatically)
curl -X POST http://localhost:8080/mcp/demo/tools/call \
  -H "Content-Type: application/json" \
  -d '{"name": "say_hello", "arguments": {"name": "Gateway User"}}'

curl -X POST http://localhost:8080/mcp/filesystem/tools/call \
  -H "Content-Type: application/json" \
  -d '{"name": "list_allowed_directories", "arguments": {}}'
```

### Monitor Performance
```bash
# View comprehensive statistics
curl http://localhost:8080/gateway/stats | jq

# Monitor load balancing
curl http://localhost:8080/gateway/stats | jq '.load_balancer.requests_per_instance'
```

## Step 5: Test Load Balancing

Make multiple requests to see load balancing in action:

```bash
# Make several requests and watch distribution
for i in {1..10}; do
  echo "Request $i:"
  curl -s -X POST http://localhost:8080/mcp/demo/tools/call \
    -H "Content-Type: application/json" \
    -d '{"name": "get_server_info", "arguments": {}}' | \
    jq -r '.structuredContent.name // "No name"'
done

# Check load distribution
curl -s http://localhost:8080/gateway/stats | jq '.load_balancer.requests_per_instance'
```

## Step 6: Test High Availability

Stop one of your MCP instances to see automatic failover:

```bash
# Stop one demo instance
mcpp stop demo --instance-id <instance-id>

# Gateway continues to work with remaining instances
curl -X POST http://localhost:8080/mcp/demo/tools/call \
  -H "Content-Type: application/json" \
  -d '{"name": "say_hello", "arguments": {"name": "Still Working"}}'

# Check health status
curl http://localhost:8080/mcp/demo/health | jq '.healthy_instances'
```

## Python Client Example

Use the gateway from Python code:

```python
import aiohttp
import asyncio

async def use_gateway():
    async with aiohttp.ClientSession() as session:
        # List tools
        async with session.get("http://localhost:8080/mcp/demo/tools/list") as resp:
            tools = await resp.json()
            print(f"Available tools: {[t['name'] for t in tools['tools']]}")

        # Call a tool
        payload = {
            "name": "say_hello",
            "arguments": {"name": "Python Client"}
        }
        async with session.post(
            "http://localhost:8080/mcp/demo/tools/call",
            json=payload
        ) as resp:
            result = await resp.json()
            print(f"Response: {result['content'][0]['text']}")

# Run the example
asyncio.run(use_gateway())
```

## What's Next?

- **[Gateway User Guide](index.md)**: Complete documentation
- **[API Reference](api-reference.md)**: Full endpoint documentation
- **[Technical README](../../mcp_platform/gateway/README.md)**: Implementation details
- **[Configuration Guide](index.md#configuration)**: Advanced configuration options

## Troubleshooting

### Gateway Won't Start
```bash
# Check if port is in use
netstat -tlnp | grep 8080

# Try different port
mcpp gateway start --port 8081
```

### No Instances Found
```bash
# Check deployments
mcpp list

# Manual sync
mcpp gateway sync

# View logs
mcpp gateway start --log-level debug
```

### Health Checks Failing
```bash
# Check instance status
curl http://localhost:8080/mcp/demo/health

# View detailed stats
curl http://localhost:8080/gateway/stats | jq '.health_checker'
```

---

**Congratulations!** 🎉 You now have a fully functional MCP Gateway with load balancing, health monitoring, and high availability.
