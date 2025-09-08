# MCP Platform - 2-Minute Quickstart

**Deploy Model Context Protocol (MCP) servers in production with zero configuration.**

## Prerequisites

- **Python 3.10+** (`python --version`)
- **Docker** (`docker --version`)
- **10 minutes** for your first deployment

## Quick Start

### 1. Install MCP Platform

```bash
# Install globally with uv (recommended)
uv tool install mcp-platform

# Or install in current project
uv add mcp-platform

# Verify installation
mcpp --version
```

### 2. Deploy Your First MCP Server

```bash
# List available templates
mcpp list

# Deploy demo server
mcpp deploy demo

# Server is now running at http://localhost:7071
```

### 3. Test Your Deployment

```bash
# Check health
curl http://localhost:7071/health

# List available tools
curl http://localhost:7071/tools

# Call a tool
curl -X POST http://localhost:7071/call \
  -H "Content-Type: application/json" \
  -d '{"method": "say_hello", "params": {"name": "World"}}'
```

**Expected Response:**
```json
{
  "success": true,
  "result": "Hello, World! Greetings from MCP Platform"
}
```

## Common Use Cases

### Deploy with Custom Configuration

```bash
# Filesystem access server
mcpp deploy filesystem --config allowed_dirs="/home/user/documents"

# GitHub integration 
mcpp deploy github --config github_token="your_token_here"

# Custom greeting
mcpp deploy demo --config hello_from="My AI Assistant"
```

### Manage Deployments

```bash
# List running deployments
mcpp list --deployed

# View logs
mcpp logs demo --follow

# Stop deployment
mcpp stop demo
```

### Production Gateway (Enterprise)

```bash
# Configure environment from project root
cp .env.example .env
# Edit .env with your settings

# Start production gateway with authentication
docker compose --profile production up -d

# Access gateway at http://localhost:8080
```

## Next Steps

| Time Investment | Guide | What You'll Learn |
|-----------------|-------|-------------------|
| **5 minutes** | [Getting Started Guide](GETTING_STARTED.md) | Local development, Docker, docker-compose |
| **15 minutes** | [CLI Reference](docs/user-guide/cli-reference.md) | All commands and options |
| **30 minutes** | [Template Guide](docs/templates/creating.md) | Create custom MCP servers |
| **1 hour** | [Docker Setup Guide](docker/README.md) | Production deployment with Docker Compose |

## Quick Troubleshooting

### Docker Issues
```bash
# Check Docker is running
docker ps

# Restart Docker daemon (macOS)
sudo launchctl stop com.docker.docker
sudo launchctl start com.docker.docker
```

### Port Conflicts
```bash
# Use different port
mcpp deploy demo --port 8080

# Check what's using port
lsof -i :7071
```

### Permission Issues
```bash
# Fix Docker permissions (Linux)
sudo usermod -aG docker $USER
newgrp docker
```

## Available Templates

| Template | Description | Use Case | Transport |
|----------|-------------|----------|-----------|
| **demo** | Hello world server | Learning, testing | HTTP, stdio |
| **filesystem** | Secure file operations | File management | stdio |
| **github** | GitHub API integration | CI/CD, development | HTTP |
| **gitlab** | GitLab API integration | CI/CD, development | HTTP |
| **bigquery** | Google BigQuery access | Data analytics | HTTP |
| **slack** | Slack API integration | Chat automation | HTTP |
| **zendesk** | Customer support tools | Support workflows | HTTP |

## Integration Examples

### Claude Desktop Configuration
```json
{
  "mcpServers": {
    "mcp-platform-demo": {
      "command": "mcpp",
      "args": ["deploy", "demo", "--transport", "stdio"]
    }
  }
}
```

### VS Code Extension
```json
{
  "mcp.servers": [
    {
      "name": "Demo Server",
      "url": "http://localhost:7071"
    }
  ]
}
```

### Python Client
```python
from mcp_platform.client import MCPClient

client = MCPClient("http://localhost:7071")
result = client.call_tool("say_hello", {"name": "Python"})
print(result)
```

## What Just Happened?

1. **MCP Platform** downloaded and deployed a Docker container
2. **MCP Server** started with FastMCP framework providing HTTP/stdio protocols
3. **Tools** were automatically discovered and made available
4. **Configuration** was processed from defaults and your inputs
5. **Health checks** ensure the server is working correctly

## Community & Support

- **[GitHub Issues](https://github.com/jrmatherly/MCP-Platform/issues)** - Bug reports and feature requests
- **[Discord Server](https://discord.gg/55Cfxe9gnr)** - Community support and discussions
- **[Documentation](https://data-everything.github.io/MCP-Platform/)** - Complete guides and API reference

---

**🎉 Congratulations!** You've deployed your first MCP server in under 2 minutes. 

Ready to go deeper? Check out the [Getting Started Guide](GETTING_STARTED.md) for local development, Docker customization, and production deployment with docker-compose.