# MCP Platform Gateway - Docker Deployment Guide

Production-ready deployment guide for the MCP Platform Gateway using Docker and docker-compose for on-premises VPS environments.

## 🚀 Quick Start

### Prerequisites

- Docker 20.10+
- Docker Compose 2.0+
- 2GB+ RAM
- 10GB+ disk space
- Domain name (for SSL certificates)

### 1. Clone and Setup

```bash
# Clone the repository
git clone https://github.com/Data-Everything/MCP-Platform.git
cd MCP-Platform/mcp_platform/gateway

# Copy environment template
cp .env.example .env
```

### 2. Configure Environment

Edit `.env` file with your settings:

```bash
# Required settings
POSTGRES_PASSWORD=your_secure_password_here
REDIS_PASSWORD=your_secure_redis_password
GATEWAY_SECRET_KEY=your_jwt_secret_key_32_chars_minimum
GATEWAY_ADMIN_PASSWORD=your_admin_password
DOMAIN_NAME=gateway.yourdomain.com
```

### 3. Deploy

```bash
# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f mcp_gateway
```

### 4. Access Gateway

- HTTP: `http://your-domain.com` (redirects to HTTPS)
- HTTPS: `https://your-domain.com`
- Health: `https://your-domain.com/gateway/health`

## 📋 Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│     Nginx       │───▶│  MCP Gateway    │───▶│   PostgreSQL    │
│  (Reverse Proxy)│    │   (FastAPI)     │    │   (Database)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   SSL/TLS       │    │     Redis       │    │    Volumes      │
│ Termination     │    │   (Caching)     │    │ (Persistence)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

### Services

- **mcp_gateway**: Main FastAPI application
- **postgres**: PostgreSQL database for persistence
- **redis**: Redis for caching and sessions
- **nginx**: Reverse proxy with SSL termination

## ⚙️ Configuration

### Environment Variables

#### Required Settings

| Variable | Description | Example |
|----------|-------------|---------|
| `POSTGRES_PASSWORD` | PostgreSQL password | `secure_password_123` |
| `REDIS_PASSWORD` | Redis password | `redis_secure_pass` |
| `GATEWAY_SECRET_KEY` | JWT secret key (32+ chars) | `your_jwt_secret_key_here...` |
| `GATEWAY_ADMIN_PASSWORD` | Admin user password | `admin_secure_pass` |
| `DOMAIN_NAME` | Your domain name | `gateway.example.com` |

#### Optional Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `GATEWAY_LOG_LEVEL` | `INFO` | Log level (DEBUG/INFO/WARNING/ERROR) |
| `GATEWAY_WORKERS` | `2` | Number of worker processes |
| `GATEWAY_CORS_ORIGINS` | `*` | CORS allowed origins |

### Database Configuration

The setup uses PostgreSQL for production reliability:

```yaml
postgres:
  image: postgres:17-alpine
  environment:
    POSTGRES_DB: mcp_gateway
    POSTGRES_USER: mcpuser
    POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
```

### SSL/TLS Configuration

#### Option 1: Let's Encrypt (Recommended)

```bash
# Install certbot
sudo apt install certbot

# Generate certificates
sudo certbot certonly --standalone -d your-domain.com

# Copy certificates
sudo cp /etc/letsencrypt/live/your-domain.com/fullchain.pem nginx/ssl/
sudo cp /etc/letsencrypt/live/your-domain.com/privkey.pem nginx/ssl/
```

#### Option 2: Self-Signed Certificates (Development)

```bash
# Create SSL directory
mkdir -p nginx/ssl

# Generate self-signed certificate
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout nginx/ssl/privkey.pem \
  -out nginx/ssl/fullchain.pem \
  -subj "/C=US/ST=State/L=City/O=Organization/CN=your-domain.com"
```

## 🔧 Management Commands

### Service Management

```bash
# Start all services
docker-compose up -d

# Stop all services
docker-compose down

# Restart a service
docker-compose restart mcp_gateway

# View service logs
docker-compose logs -f mcp_gateway

# Scale gateway workers
docker-compose up -d --scale mcp_gateway=3
```

### User Management

```bash
# Create admin user
docker-compose exec mcp_gateway python -m mcp_platform.gateway.cli create-user admin \
  --email admin@example.com --password your_password --superuser

# Create API key
docker-compose exec mcp_gateway python -m mcp_platform.gateway.cli create-api-key admin \
  --name "Production API Key" --expires 365

# List users
docker-compose exec mcp_gateway python -m mcp_platform.gateway.cli list-users
```

### Database Management

```bash
# Initialize database
docker-compose exec mcp_gateway python -m mcp_platform.gateway.cli db-init

# Database backup
docker-compose exec postgres pg_dump -U mcpuser mcp_gateway > backup_$(date +%Y%m%d).sql

# Database restore
cat backup_20231201.sql | docker-compose exec -T postgres psql -U mcpuser mcp_gateway
```

## 🔍 Monitoring

### Health Checks

```bash
# Gateway health
curl https://your-domain.com/gateway/health

# Service status
docker-compose ps

# Resource usage
docker stats
```

### Optional Monitoring Stack

Enable Prometheus and Grafana:

```bash
# Start with monitoring
docker-compose --profile monitoring up -d

# Access Grafana
open http://localhost:3000
# Username: admin
# Password: admin (or set GRAFANA_ADMIN_PASSWORD)
```

### Log Management

```bash
# View logs
docker-compose logs -f --tail=100

# Log rotation (add to crontab)
docker-compose exec nginx logrotate /etc/logrotate.conf
```

## 🛡️ Security Hardening

### 1. Firewall Configuration

```bash
# Allow only necessary ports
sudo ufw allow 22    # SSH
sudo ufw allow 80    # HTTP
sudo ufw allow 443   # HTTPS
sudo ufw deny 5432   # PostgreSQL (internal only)
sudo ufw deny 6379   # Redis (internal only)
sudo ufw enable
```

### 2. SSL Security

- Use strong SSL certificates (Let's Encrypt recommended)
- Enable HSTS headers (configured in nginx)
- Disable weak SSL protocols (TLSv1.2+ only)

### 3. Database Security

```bash
# Set strong passwords
POSTGRES_PASSWORD=your_very_strong_password_here_with_special_chars

# Restrict database access to application only
# (Already configured in docker-compose.yml)
```

### 4. Application Security

- Set restrictive CORS origins in production
- Use strong JWT secret keys (32+ characters)
- Enable rate limiting (configured in nginx)
- Regular security updates

### 5. Container Security

```bash
# Run as non-root user (configured in Dockerfile)
# Read-only file systems where possible
# Resource limits

# Security scanning
docker scout cves mcp_gateway_app
```

## 🔄 Backup and Recovery

### Automated Backup Script

Create `scripts/backup.sh`:

```bash
#!/bin/bash
BACKUP_DIR="/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# Database backup
docker-compose exec -T postgres pg_dump -U mcpuser mcp_gateway | gzip > "${BACKUP_DIR}/db_${DATE}.sql.gz"

# Registry backup
docker cp mcp_gateway_app:/app/registry "${BACKUP_DIR}/registry_${DATE}"

# Clean old backups (keep 30 days)
find "${BACKUP_DIR}" -name "*.sql.gz" -mtime +30 -delete
```

### Recovery Process

```bash
# Stop services
docker-compose down

# Restore database
gunzip < backup_20231201.sql.gz | docker-compose exec -T postgres psql -U mcpuser mcp_gateway

# Restore registry
docker cp registry_backup/ mcp_gateway_app:/app/registry

# Start services
docker-compose up -d
```

## 🚨 Troubleshooting

### Common Issues

#### 1. Gateway Won't Start

```bash
# Check logs
docker-compose logs mcp_gateway

# Check database connection
docker-compose exec postgres pg_isready -U mcpuser -d mcp_gateway

# Verify environment variables
docker-compose exec mcp_gateway env | grep GATEWAY
```

#### 2. SSL Certificate Issues

```bash
# Check certificate validity
openssl x509 -in nginx/ssl/fullchain.pem -text -noout

# Test SSL configuration
docker-compose exec nginx nginx -t

# Reload nginx configuration
docker-compose exec nginx nginx -s reload
```

#### 3. Database Connection Issues

```bash
# Check PostgreSQL status
docker-compose exec postgres pg_isready

# Check database logs
docker-compose logs postgres

# Test connection
docker-compose exec mcp_gateway python -c "
from mcp_platform.gateway.database import initialize_database
from mcp_platform.gateway.models import GatewayConfig, DatabaseConfig
import asyncio
async def test():
    config = GatewayConfig(database=DatabaseConfig(url='postgresql://mcpuser:password@postgres:5432/mcp_gateway'))
    db = await initialize_database(config)
    print('Connection successful')
asyncio.run(test())
"
```

#### 4. Performance Issues

```bash
# Monitor resource usage
docker stats

# Check gateway metrics
curl https://your-domain.com/gateway/stats

# Adjust worker count
# Edit .env: GATEWAY_WORKERS=4
docker-compose up -d
```

### Log Locations

```
nginx_logs/           # Nginx access and error logs
/app/logs/           # Gateway application logs (inside container)
postgres logs        # Via docker-compose logs postgres
redis logs           # Via docker-compose logs redis
```

## 🔄 Updates and Maintenance

### Updating the Gateway

```bash
# Pull latest changes
git pull origin main

# Rebuild and restart
docker-compose build --no-cache mcp_gateway
docker-compose up -d

# Verify deployment
curl https://your-domain.com/gateway/health
```

### Regular Maintenance

```bash
# Weekly maintenance script
#!/bin/bash

# Update system packages
sudo apt update && sudo apt upgrade -y

# Clean Docker
docker system prune -f

# Backup database
./scripts/backup.sh

# Check certificate expiry
openssl x509 -in nginx/ssl/fullchain.pem -checkend 864000

# Restart services (if needed)
docker-compose restart
```

## 📊 Performance Tuning

### Resource Allocation

```yaml
# docker-compose.yml additions
mcp_gateway:
  deploy:
    resources:
      limits:
        memory: 1G
        cpus: '1.0'
      reservations:
        memory: 512M
        cpus: '0.5'
```

### Database Optimization

```bash
# PostgreSQL tuning
docker-compose exec postgres psql -U mcpuser -d mcp_gateway -c "
ALTER SYSTEM SET shared_buffers = '256MB';
ALTER SYSTEM SET effective_cache_size = '1GB';
ALTER SYSTEM SET maintenance_work_mem = '64MB';
SELECT pg_reload_conf();
"
```

### Nginx Optimization

- Increase worker connections
- Enable HTTP/2
- Configure proper caching headers
- Use gzip compression (already configured)

## 📞 Support

### Getting Help

1. Check logs: `docker-compose logs -f`
2. Verify configuration: Review `.env` file
3. Test connectivity: Use health check endpoints
4. Community support: GitHub Issues

### Useful Commands

```bash
# Complete service restart
docker-compose down && docker-compose up -d

# Check all service status
docker-compose ps && docker-compose logs --tail=10

# Monitor real-time logs
docker-compose logs -f mcp_gateway nginx postgres

# Emergency stop
docker-compose kill
```

---

## 📝 Summary

This deployment provides a production-ready MCP Platform Gateway with:

- ✅ **Security**: SSL/TLS, authentication, rate limiting
- ✅ **Scalability**: Multiple workers, load balancing
- ✅ **Reliability**: Health checks, automatic restarts
- ✅ **Monitoring**: Comprehensive logging and metrics
- ✅ **Persistence**: PostgreSQL database with backups
- ✅ **Performance**: Nginx reverse proxy, caching

For additional configuration options and advanced deployment scenarios, refer to the [Gateway README](README.md) and [API documentation](../../README.md).