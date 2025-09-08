# MCP Platform Docker Setup

This directory contains the centralized Docker configuration for the MCP Platform project.

## Quick Start

From the project root:

```bash
# Copy and configure environment
cp .env.example .env
# Edit .env with your configuration

# Build and start all services
docker compose build
docker compose up -d

# Or start specific profiles
docker compose --profile gateway up -d        # Gateway only
docker compose --profile monitoring up -d     # With monitoring
docker compose --profile production up -d     # Full production stack
docker compose --profile templates up -d      # Template examples
```

## Directory Structure

```
docker/
├── README.md                   # This file
├── mcp-platform.dockerfile     # Main MCP Platform CLI container
├── gateway.dockerfile          # Production gateway container
├── nginx/                      # Reverse proxy configuration
│   ├── Dockerfile             # Nginx container with SSL
│   ├── nginx.conf             # Main nginx configuration
│   ├── proxy_params           # Common proxy settings
│   └── conf.d/                # Additional server configurations
├── monitoring/                 # Monitoring and alerting
│   ├── prometheus.yml         # Prometheus configuration
│   ├── alerts/                # Alert rules
│   └── grafana/               # Grafana dashboards and provisioning
└── init-scripts/              # Database initialization scripts
```

## Service Profiles

### Core Services
- `mcp-platform`: Main CLI container for template deployment
- `mcp-gateway`: Production gateway with authentication and load balancing
- `postgres`: PostgreSQL database for gateway
- `redis`: Redis cache for sessions and caching
- `nginx`: Reverse proxy with SSL termination

### Profiles
- `platform`: Core MCP Platform CLI only
- `gateway`: Production gateway stack (postgres + redis + gateway + nginx)
- `monitoring`: Prometheus + Grafana monitoring
- `production`: Full production stack (gateway + monitoring)
- `templates`: Example template deployments (demo + filesystem)

## Configuration

All configuration is managed through the root `.env` file. Key sections:

### Required Settings
```bash
POSTGRES_PASSWORD=your_secure_password
REDIS_PASSWORD=your_redis_password
GATEWAY_SECRET_KEY=your_32_char_jwt_secret
GATEWAY_ADMIN_PASSWORD=admin_password
DOMAIN_NAME=your.domain.com
```

### Optional Settings
- Network configuration (ports, subnets)
- Monitoring settings (Grafana credentials)
- Template configurations
- SSL/TLS settings

## Deployment Examples

### Development
```bash
# Basic development setup
docker compose --profile platform --profile templates up -d
```

### Staging
```bash
# Gateway with monitoring
docker compose --profile gateway --profile monitoring up -d
```

### Production
```bash
# Full production stack
docker compose --profile production up -d
```

## Template Integration

Template containers reference their original Dockerfiles:
- `mcp_platform/template/templates/demo/Dockerfile`
- `mcp_platform/template/templates/filesystem/Dockerfile`

This maintains consistency between standalone template development and Docker Compose deployment.

## Networking

All services use the `mcp_platform_network` bridge network with configurable subnet (default: 172.20.0.0/16).

## Volumes

Persistent volumes for:
- `postgres_data`: PostgreSQL database
- `redis_data`: Redis persistence
- `gateway_data`: Gateway application data
- `gateway_registry`: Server registry
- `prometheus_data`: Metrics storage
- `grafana_data`: Dashboards and settings

## Health Checks

All services include health checks:
- Gateway: HTTP health endpoint
- Database: PostgreSQL connection check
- Redis: PING command
- Nginx: HTTP status check

## Security

- Non-root users in all containers
- SSL termination at nginx layer
- Environment variable validation
- Network isolation
- Security headers in nginx

## Monitoring

Prometheus metrics collection with Grafana dashboards:
- Application metrics from gateway
- Infrastructure metrics (CPU, memory, disk)
- Alert rules for critical conditions

## Troubleshooting

```bash
# Check service status
docker compose ps

# View logs
docker compose logs mcp-gateway -f

# Restart specific service
docker compose restart nginx

# Rebuild and update
docker compose build
docker compose up -d --force-recreate
```