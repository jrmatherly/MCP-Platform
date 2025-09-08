#!/bin/bash
# Quick Docker Compose startup script for MCP Platform
# Usage: ./scripts/docker-compose-up.sh [profile]

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default profile
PROFILE="${1:-production}"

echo -e "${BLUE}🐳 MCP Platform Docker Compose Setup${NC}"
echo "Profile: $PROFILE"
echo

# Check if Docker is running
if ! docker info >/dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running. Please start Docker first.${NC}"
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  .env file not found. Creating from .env.example...${NC}"
    if [ -f .env.example ]; then
        cp .env.example .env
        echo -e "${YELLOW}📝 Please edit .env file with your configuration before continuing.${NC}"
        echo -e "${YELLOW}Required: POSTGRES_PASSWORD, REDIS_PASSWORD, GATEWAY_SECRET_KEY, GATEWAY_ADMIN_PASSWORD${NC}"
        read -p "Press Enter after configuring .env file..."
    else
        echo -e "${RED}❌ .env.example not found. Cannot proceed.${NC}"
        exit 1
    fi
fi

# Source environment variables
set -a
source .env
set +a

# Check SSL certificates for gateway/production profiles
if [ "$PROFILE" = "gateway" ] || [ "$PROFILE" = "production" ] || [ "$PROFILE" = "all" ]; then
    echo -e "${BLUE}🔐 Checking SSL Configuration${NC}"
    
    if [ ! -f "docker/nginx/ssl/fullchain.pem" ] || [ ! -f "docker/nginx/ssl/privkey.pem" ]; then
        echo -e "${YELLOW}⚠️  SSL certificates not found in docker/nginx/ssl/${NC}"
        
        if [ "${DOMAIN_NAME:-localhost}" != "localhost" ]; then
            echo -e "${YELLOW}For production deployment, you should obtain SSL certificates.${NC}"
            echo -e "${YELLOW}Options:${NC}"
            echo "  1. Use Let's Encrypt: certbot certonly --standalone -d ${DOMAIN_NAME:-your-domain.com}"
            echo "  2. Upload your own certificates to docker/nginx/ssl/"
            echo "  3. Generate self-signed certificates for testing"
            echo ""
            read -p "Generate self-signed certificates for testing? (y/N): " generate_ssl
            if [ "$generate_ssl" = "y" ] || [ "$generate_ssl" = "Y" ]; then
                mkdir -p docker/nginx/ssl
                openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
                    -keyout docker/nginx/ssl/privkey.pem \
                    -out docker/nginx/ssl/fullchain.pem \
                    -subj "/C=US/ST=State/L=City/O=Organization/CN=${DOMAIN_NAME:-localhost}"
                echo -e "${GREEN}✅ Self-signed certificates generated${NC}"
            fi
        else
            echo -e "${GREEN}✅ Using localhost - SSL certificates not required${NC}"
        fi
    else
        echo -e "${GREEN}✅ SSL certificates found${NC}"
    fi
fi

# Validate required environment variables for production
if [ "$PROFILE" = "production" ] || [ "$PROFILE" = "gateway" ]; then
    source .env
    
    required_vars=("POSTGRES_PASSWORD" "REDIS_PASSWORD" "GATEWAY_SECRET_KEY" "GATEWAY_ADMIN_PASSWORD")
    missing_vars=()
    
    for var in "${required_vars[@]}"; do
        if [ -z "${!var:-}" ]; then
            missing_vars+=("$var")
        fi
    done
    
    if [ ${#missing_vars[@]} -gt 0 ]; then
        echo -e "${RED}❌ Missing required environment variables:${NC}"
        printf '%s\n' "${missing_vars[@]}"
        echo "Please configure these in your .env file."
        exit 1
    fi
fi

# Build and start services
echo -e "${BLUE}🔨 Building containers...${NC}"
docker compose build

echo -e "${BLUE}🚀 Starting services with profile: $PROFILE${NC}"
case $PROFILE in
    "dev" | "development")
        docker compose --profile platform --profile templates up -d
        ;;
    "gateway")
        docker compose --profile gateway up -d
        ;;
    "monitoring")
        docker compose --profile monitoring up -d
        ;;
    "production")
        docker compose --profile production up -d
        ;;
    "all")
        docker compose --profile platform --profile gateway --profile monitoring --profile templates up -d
        ;;
    *)
        echo -e "${YELLOW}Unknown profile: $PROFILE${NC}"
        echo "Available profiles: dev, gateway, monitoring, production, all"
        exit 1
        ;;
esac

# Wait a bit for services to start
echo -e "${BLUE}⏳ Waiting for services to start...${NC}"
sleep 5

# Show status
echo -e "${GREEN}✅ Services started!${NC}"
echo
docker compose ps

# Show useful URLs
echo
echo -e "${GREEN}🌐 Available Services:${NC}"
echo "• MCP Platform CLI: docker compose exec mcp-platform mcpp --help"

if [ "$PROFILE" = "gateway" ] || [ "$PROFILE" = "production" ] || [ "$PROFILE" = "all" ]; then
    echo "• Gateway API: http://localhost:8080/gateway/health"
    echo "• Gateway Admin: http://localhost:8080/gateway/admin"
fi

if [ "$PROFILE" = "templates" ] || [ "$PROFILE" = "all" ] || [ "$PROFILE" = "dev" ]; then
    echo "• Demo Server: http://localhost:7071/health"
fi

if [ "$PROFILE" = "monitoring" ] || [ "$PROFILE" = "production" ] || [ "$PROFILE" = "all" ]; then
    echo "• Prometheus: http://localhost:9090"
    echo "• Grafana: http://localhost:3000 (admin/admin)"
fi

echo
echo -e "${BLUE}📋 Useful commands:${NC}"
echo "• View logs: docker compose logs -f [service]"
echo "• Stop services: docker compose down"
echo "• Restart: docker compose restart [service]"
echo "• Update: docker compose pull && docker compose up -d"
echo

echo -e "${GREEN}🎉 MCP Platform is ready!${NC}"