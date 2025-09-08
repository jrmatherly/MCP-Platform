# Getting Started with MCP Platform

**Complete guide to deploying, customizing, and managing Model Context Protocol servers locally and in production.**

## Table of Contents

1. [Environment Setup](#environment-setup)
2. [Local Development](#local-development)  
3. [Docker Deployment](#docker-deployment)
4. [Docker Compose Production](#docker-compose-production)
5. [Configuration Guide](#configuration-guide)
6. [Template Development](#template-development)
7. [Production Deployment](#production-deployment)
8. [Troubleshooting](#troubleshooting)

---

## Environment Setup

### Prerequisites Verification

Before starting, verify your system meets the requirements:

```bash
# Python 3.10+ required
python --version
# Should show: Python 3.10.x or higher

# Docker for container deployment
docker --version
# Should show: Docker version 20.0+ 

# Docker Compose for production stacks
docker compose version
# Should show: Docker Compose version 2.0+

# Git for template development (optional)
git --version
```

### Install MCP Platform

#### Option 1: Global Installation (Recommended)

```bash
# Install globally with uv
uv tool install mcp-platform

# Verify installation
mcpp --version
which mcpp
```

#### Option 2: Project-Specific Installation

```bash
# Create new project
mkdir my-mcp-project && cd my-mcp-project

# Initialize with uv
uv init
uv add mcp-platform

# Activate environment
source .venv/bin/activate

# Verify installation
mcpp --version
```

#### Option 3: Development Installation

```bash
# Clone repository
git clone https://github.com/jrmatherly/MCP-Platform.git
cd MCP-Platform

# Setup development environment
make dev-setup

# Install in editable mode
uv sync --all-extras
```

### Environment Verification

```bash
# Test Docker connectivity
docker run --rm hello-world

# Test MCP Platform
mcpp list

# Expected output: List of available templates
```

---

## Local Development

### Basic Template Deployment

Start with the demo template to understand the deployment flow:

```bash
# Deploy demo server
mcpp deploy demo

# Check deployment status
mcpp list --deployed

# View server logs
mcpp logs demo

# Test the deployment
curl http://localhost:7071/health
```

### Custom Configuration

Templates support flexible configuration through multiple sources:

```bash
# Configure via CLI arguments
mcpp deploy demo \
  --config hello_from="Local Development" \
  --config log_level="debug" \
  --port 8080

# Configure via file
cat > demo-config.json << 'EOF'
{
  "hello_from": "Config File",
  "log_level": "debug",
  "auth_mode": "token",
  "auth_token": "dev-token-123"
}
EOF

mcpp deploy demo --config-file demo-config.json
```

### Working with Different Templates

#### Filesystem Template (File Operations)

```bash
# Deploy with allowed directories
mcpp deploy filesystem \
  --config allowed_dirs="/home/user/documents /tmp/workspace"

# The server will mount these as Docker volumes
# Test file operations via stdio transport
echo '{"method": "list_directory", "params": {"path": "/data"}}' | \
  docker exec -i mcp-platform-filesystem-* python -
```

#### GitHub Integration Template

```bash
# Deploy GitHub integration
mcpp deploy github \
  --config github_token="your_github_token" \
  --config repositories="user/repo1,user/repo2"

# Test API integration
curl -X POST http://localhost:7071/call \
  -H "Content-Type: application/json" \
  -d '{"method": "list_repositories", "params": {}}'
```

### Interactive Development Mode

For rapid prototyping and testing:

```bash
# Start interactive CLI
mcpp interactive

# Within interactive mode:
> deploy demo --config hello_from="Interactive"
> tools  # List available tools
> call say_hello {"name": "Developer"}  
> logs demo --tail 20
> stop demo
```

### Development Commands

```bash
# Quick validation during development
make test-quick

# Run comprehensive tests
make test-all

# Code quality checks
make lint
make type-check

# Format code
make format
```

---

## Docker Deployment

### Understanding Docker Integration

MCP Platform uses multi-stage Docker builds with uv optimization:

```dockerfile
# Example template Dockerfile structure
FROM ghcr.io/astral-sh/uv:python3.11-bookworm as builder
# ... dependency installation with caching

FROM python:3.11-bookworm-slim as runtime  
# ... optimized runtime with non-root user
```

### Manual Docker Operations

```bash
# Pull template images
docker pull mcp-platform/mcp-demo:latest
docker pull mcp-platform/mcp-filesystem:latest

# Run container manually
docker run -d \
  --name my-mcp-demo \
  --network mcp-platform \
  -p 7071:7071 \
  -e MCP_HELLO_FROM="Docker Manual" \
  mcp-platform/mcp-demo:latest

# Check container logs
docker logs my-mcp-demo

# Clean up
docker stop my-mcp-demo
docker rm my-mcp-demo
```

### Custom Docker Networks

```bash
# Create isolated network
docker network create mcp-development

# Deploy with custom network
mcpp deploy demo --network mcp-development

# List network containers
docker network inspect mcp-development
```

### Volume Management

```bash
# Deploy filesystem template with persistent volumes
mcpp deploy filesystem \
  --config allowed_dirs="/host/data" \
  --data-dir "/persistent/mcp-data"

# Inspect created volumes
docker volume ls | grep mcp
docker volume inspect mcp-platform-filesystem-data
```

### Container Resource Limits

```bash
# Deploy with resource constraints
docker run -d \
  --name resource-limited-mcp \
  --memory="512m" \
  --cpus="1.0" \
  -p 7072:7071 \
  -e MCP_HELLO_FROM="Resource Limited" \
  mcp-platform/mcp-demo:latest
```

---

## Docker Compose Production

### Gateway Stack Deployment

The production gateway provides enterprise features: authentication, load balancing, persistence, and monitoring.

```bash
# From project root directory
# Copy example environment file
cp .env.example .env

# Edit .env file with your values
# Required settings:
POSTGRES_PASSWORD=secure_password_here
REDIS_PASSWORD=redis_password_here
GATEWAY_SECRET_KEY=your_secret_key_32_chars_minimum
GATEWAY_ADMIN_PASSWORD=admin_password_here
DOMAIN_NAME=your-domain.com

# Optional monitoring settings:
GRAFANA_ADMIN_PASSWORD=grafana_password_here

# Build and deploy production stack
docker compose build
docker compose --profile production up -d

# Check services
docker compose ps
```

### Service Architecture

The docker-compose stack includes:

```yaml
services:
  postgres:     # PostgreSQL database
  redis:        # Caching and sessions  
  mcp_gateway:  # Main gateway application
  nginx:        # Reverse proxy with SSL
  prometheus:   # Metrics collection (optional)
  grafana:      # Monitoring dashboards (optional)
```

### Gateway Configuration

```bash
# Access gateway admin interface
open http://localhost:8080/admin

# Register MCP servers with gateway
curl -X POST http://localhost:8080/gateway/servers \
  -H "Authorization: Bearer your_admin_token" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "demo-server",
    "endpoint": "http://demo-container:7071",
    "health_check": "/health"
  }'

# Test load balancing
curl http://localhost:8080/proxy/demo-server/tools
```

### SSL Configuration

```bash
# Generate self-signed certificates for development
mkdir -p nginx/ssl
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx/ssl/gateway.key \
  -out nginx/ssl/gateway.crt \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=localhost"

# Update nginx configuration
cp nginx/conf.d/gateway.conf.template nginx/conf.d/gateway.conf
# Edit nginx/conf.d/gateway.conf to enable SSL

# Restart nginx
docker compose restart nginx
```

### Scaling Services

```bash
# Scale gateway workers
docker compose up -d --scale mcp-gateway=3

# Scale with custom configuration
cat > docker-compose.override.yml << 'EOF'
services:
  mcp-gateway:
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '2'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M
EOF

docker compose up -d
```

### Production Monitoring

```bash
# Deploy with monitoring enabled
docker compose --profile monitoring up -d

# Access monitoring
open http://localhost:9090  # Prometheus
open http://localhost:3000  # Grafana (admin/admin_password)

# Check metrics
curl http://localhost:8080/gateway/metrics
```

---

## Configuration Guide

### Configuration Sources (Priority Order)

1. **Environment Variables** (highest priority)
2. **CLI Arguments** (`--config`, `--override`)
3. **Configuration Files** (`--config-file`)
4. **Template Defaults** (lowest priority)

### Configuration Schema Validation

Templates define configuration schemas that validate inputs:

```json
{
  "config_schema": {
    "type": "object",
    "properties": {
      "hello_from": {
        "type": "string",
        "description": "Source of greetings",
        "default": "MCP Platform",
        "env_mapping": "MCP_HELLO_FROM"
      },
      "auth_mode": {
        "type": "string", 
        "enum": ["none", "token", "basic"],
        "default": "none"
      }
    },
    "anyOf": [
      {"properties": {"auth_mode": {"const": "none"}}},
      {
        "properties": {"auth_mode": {"const": "token"}},
        "required": ["auth_token"]
      }
    ]
  }
}
```

### Advanced Configuration Examples

#### Environment-Based Configuration

```bash
# Export environment variables
export MCP_HELLO_FROM="Production Environment"
export MCP_LOG_LEVEL="info"
export MCP_AUTH_MODE="token"
export MCP_AUTH_TOKEN="prod-token-xyz"

# Deploy using environment
mcpp deploy demo
```

#### YAML Configuration Files

```yaml
# config/production.yml
hello_from: "Production YAML"
log_level: "info"
auth_mode: "basic"
auth_username: "admin"
auth_password: "secure-password"

# Custom ports and networking
transport:
  port: 8080
  host: "0.0.0.0"

# Resource limits
resources:
  memory: "512m" 
  cpu: "1.0"
```

```bash
# Deploy with YAML config
mcpp deploy demo --config-file config/production.yml
```

#### Template Data Overrides

Use double underscore notation to modify template structure:

```bash
# Override nested template properties
mcpp deploy demo \
  --override "transport__port=9000" \
  --override "capabilities__0__name=Custom Hello" \
  --override "tools__0__description=Modified greeting tool"
```

### Configuration Validation

```bash
# Validate configuration before deployment
mcpp validate demo --config-file config/demo.yml

# Show processed configuration
mcpp deploy demo --config hello_from="Test" --dry-run --show-config
```

---

## Template Development

### Creating Custom Templates

```bash
# Generate new template
mcpp create my-custom-template

# Template directory structure
my-custom-template/
├── template.json      # Template metadata and schema
├── Dockerfile        # Multi-stage uv-optimized build  
├── pyproject.toml    # Python project configuration
├── uv.lock          # Locked dependencies
├── server.py        # MCP server implementation
├── script.sh        # Container entrypoint
├── README.md        # Template documentation
└── tests/           # Template-specific tests
```

### Template Configuration

```json
{
  "name": "My Custom MCP Server",
  "description": "Custom MCP server for specific use case",
  "version": "1.0.0", 
  "author": "Your Name",
  "category": "Custom",
  "docker_image": "your-org/your-mcp-server",
  "transport": {
    "default": "http",
    "supported": ["http", "stdio"],
    "port": 7071
  },
  "config_schema": {
    "type": "object", 
    "properties": {
      "api_key": {
        "type": "string",
        "description": "API key for external service",
        "env_mapping": "MY_API_KEY",
        "sensitive": true
      },
      "data_dir": {
        "type": "string", 
        "description": "Data directory path",
        "volume_mount": true,
        "command_arg": true,
        "default": "/data"
      }
    },
    "required": ["api_key"]
  },
  "tools": [
    {
      "name": "custom_tool",
      "description": "Performs custom operation", 
      "parameters": [
        {
          "name": "input",
          "type": "string",
          "required": true
        }
      ]
    }
  ]
}
```

### Server Implementation

```python
# server.py
from fastmcp import FastMCP
import os
import logging

# Configure logging
logging.basicConfig(level=getattr(logging, os.getenv('MCP_LOG_LEVEL', 'INFO')))
logger = logging.getLogger(__name__)

# Initialize FastMCP
mcp = FastMCP("My Custom MCP Server")

@mcp.tool()
def custom_tool(input: str) -> str:
    """Perform custom operation."""
    api_key = os.getenv('MY_API_KEY')
    data_dir = os.getenv('MY_DATA_DIR', '/data')
    
    logger.info(f"Processing: {input}")
    
    # Your custom logic here
    result = f"Processed '{input}' with key {api_key[:8]}... in {data_dir}"
    return result

if __name__ == "__main__":
    mcp.run()
```

### Docker Build Optimization

```dockerfile
# Multi-stage build with uv
FROM ghcr.io/astral-sh/uv:python3.11-bookworm as builder

WORKDIR /app
COPY pyproject.toml uv.lock ./

# Install dependencies with caching
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev --no-install-project

# Runtime stage  
FROM python:3.11-bookworm-slim as runtime

# Security: non-root user
RUN useradd --create-home --shell /bin/bash mcp && \
    mkdir -p /data && chown -R mcp:mcp /data

# Copy virtual environment
COPY --from=builder /app/.venv /app/.venv
ENV PATH="/app/.venv/bin:$PATH"

# Copy source
WORKDIR /app
COPY --chown=mcp:mcp . .

USER mcp
EXPOSE 7071

CMD ["python", "server.py"]
```

### Testing Custom Templates

```bash
# Test template locally
mcpp deploy my-custom-template --backend mock

# Run template tests
cd my-custom-template  
uv run pytest tests/ -v

# Build and test Docker image
docker build -t my-custom-template .
docker run -it --rm my-custom-template

# Integration test with MCP Platform
mcpp deploy my-custom-template --config api_key="test-key"
```

---

## Production Deployment

### High Availability Setup

```bash
# Multi-node docker swarm
docker swarm init
docker node ls

# Deploy as stack
docker stack deploy -c docker-compose.yml mcp-platform

# Scale services
docker service scale mcp-platform_mcp-gateway=5
```

### Load Balancing Configuration

```nginx
# nginx/conf.d/load-balancer.conf
upstream mcp_backends {
    least_conn;
    server mcp_gateway_1:8080 weight=3;
    server mcp_gateway_2:8080 weight=2;  
    server mcp_gateway_3:8080 weight=1;
}

server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://mcp_backends;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Health checks
        proxy_next_upstream error timeout invalid_header http_500 http_502 http_503;
        proxy_connect_timeout 5s;
        proxy_send_timeout 30s;  
        proxy_read_timeout 30s;
    }
}
```

### Database Migration

```bash
# Backup existing SQLite data
docker exec mcp_gateway_app cat /app/data/gateway.db > backup.db

# Deploy with PostgreSQL (default production profile)
docker compose --profile production up -d

# Run migrations
docker exec mcp_gateway_app python -m mcp_platform.gateway.migrate \
  --from sqlite:///app/data/gateway.db \
  --to postgresql://user:pass@postgres:5432/db
```

### Monitoring and Logging

```bash
# Enable monitoring for centralized logging
docker compose --profile monitoring up -d

# Log aggregation
docker run -d \
  --name fluent-bit \
  --volume /var/log:/var/log:ro \
  --volume $(pwd)/fluent-bit.conf:/fluent-bit/etc/fluent-bit.conf \
  fluent/fluent-bit

# Metrics collection
curl http://localhost:8080/gateway/metrics | \
  grep -E '(http_requests_total|deployment_status|error_rate)'
```

### Security Hardening

```bash
# Enable firewall
ufw allow 22/tcp
ufw allow 80/tcp  
ufw allow 443/tcp
ufw --force enable

# Secure Docker daemon
# Edit /etc/docker/daemon.json
{
  "hosts": ["unix:///var/run/docker.sock"],
  "tls": true,
  "tlscert": "/etc/docker/server-cert.pem",
  "tlskey": "/etc/docker/server-key.pem",  
  "tlsverify": true,
  "tlscacert": "/etc/docker/ca.pem"
}

# Restart Docker
systemctl restart docker
```

---

## Troubleshooting

### Common Issues

#### Docker Daemon Not Running

```bash
# Check Docker status
systemctl status docker

# Start Docker
sudo systemctl start docker

# macOS: Restart Docker Desktop
sudo launchctl stop com.docker.docker
sudo launchctl start com.docker.docker
```

#### Port Conflicts

```bash
# Find what's using port
lsof -i :7071
netstat -tulpn | grep 7071

# Kill process using port
kill -9 $(lsof -t -i:7071)

# Deploy on different port
mcpp deploy demo --port 8080
```

#### Permission Denied

```bash
# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Fix Docker socket permissions
sudo chmod 666 /var/run/docker.sock

# Container permission issues
docker exec -it container_name ls -la /data
```

#### Image Pull Failures

```bash
# Manual image pull
docker pull mcp-platform/mcp-demo:latest

# Use different registry
mcpp deploy demo --image "ghcr.io/alternative/image:tag"

# Private registry authentication
docker login your-registry.com
```

#### Configuration Validation Errors

```bash
# Validate template JSON
python -m json.tool template.json

# Check config schema
mcpp validate demo --config-file config.yml --verbose

# Debug configuration merging
mcpp deploy demo --dry-run --show-config --debug
```

### Debug Mode

```bash
# Enable debug logging
export MCP_LOG_LEVEL=DEBUG
mcpp deploy demo --verbose

# Check container logs
mcpp logs demo --follow --tail 100

# Interactive container debugging
docker exec -it mcp-platform-demo-* /bin/bash
```

### Performance Issues  

```bash
# Check resource usage
docker stats mcp-platform-*

# Increase container resources
docker run -d \
  --memory="1g" \
  --cpus="2.0" \
  mcp-platform/mcp-demo

# Gateway performance tuning
# Edit docker-compose.yml
environment:
  GATEWAY_WORKERS: 4
  GATEWAY_TIMEOUT: 300
```

### Network Connectivity

```bash
# Test container networking
docker exec mcp-platform-demo-* nslookup google.com

# Check Docker networks
docker network ls
docker network inspect mcp-platform

# Test internal connectivity  
docker exec container1 ping container2
```

### Log Analysis

```bash
# Gateway logs
docker compose logs mcp-gateway -f

# Database logs
docker compose logs postgres -f

# System logs
journalctl -u docker -f
tail -f /var/log/docker.log
```

---

## What's Next?

### Advanced Topics

- **[Gateway Configuration](mcp_platform/gateway/README.md)** - Authentication, load balancing, persistence
- **[Template Development](docs/templates/creating.md)** - Build custom MCP servers  
- **[CLI Reference](docs/user-guide/cli-reference.md)** - Complete command documentation
- **[API Documentation](docs/api/)** - Programmatic usage and integration

### Production Considerations

- **Monitoring**: Set up comprehensive monitoring with Prometheus and Grafana
- **Backup Strategy**: Implement database backups and disaster recovery
- **Security**: Regular security audits, dependency updates, and access controls
- **Scaling**: Horizontal scaling strategies and performance optimization

### Community

- **[GitHub Repository](https://github.com/jrmatherly/MCP-Platform)** - Source code and issues
- **[Discord Community](https://discord.gg/55Cfxe9gnr)** - Support and discussions
- **[Documentation Site](https://data-everything.github.io/MCP-Platform/)** - Complete documentation

---

**🚀 You're now ready to deploy and manage MCP servers in any environment!**

This guide covered local development, Docker deployment, and production docker-compose setups. You understand how to configure templates, create custom servers, and troubleshoot common issues.

For enterprise deployments, production monitoring, and advanced customization, explore the additional documentation resources linked above.