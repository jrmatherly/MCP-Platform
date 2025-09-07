#!/bin/bash

# MCP Platform Gateway - Production Startup Script
# This script helps with initial deployment and common operations

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_header() {
    echo -e "${BLUE}======================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}======================================${NC}"
}

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    print_warning "Running as root. Consider using a non-root user for security."
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    print_error ".env file not found. Please copy .env.example to .env and configure it."
    exit 1
fi

# Source environment variables
set -a
source .env
set +a

# Validate required environment variables
print_header "Validating Environment Configuration"

required_vars=("POSTGRES_PASSWORD" "REDIS_PASSWORD" "GATEWAY_SECRET_KEY" "GATEWAY_ADMIN_PASSWORD")
missing_vars=()

for var in "${required_vars[@]}"; do
    if [ -z "${!var}" ]; then
        missing_vars+=("$var")
    else
        print_status "$var is set"
    fi
done

if [ ${#missing_vars[@]} -ne 0 ]; then
    print_error "Missing required environment variables:"
    for var in "${missing_vars[@]}"; do
        echo "  - $var"
    done
    print_error "Please configure these variables in your .env file."
    exit 1
fi

# Check Docker and Docker Compose
print_header "Checking Dependencies"

if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
else
    print_status "Docker is available"
fi

if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
else
    print_status "Docker Compose is available"
fi

# Check SSL certificates
print_header "Checking SSL Configuration"

if [ ! -f "nginx/ssl/fullchain.pem" ] || [ ! -f "nginx/ssl/privkey.pem" ]; then
    print_warning "SSL certificates not found in nginx/ssl/"
    
    if [ "$DOMAIN_NAME" != "localhost" ]; then
        print_warning "For production deployment, you should obtain SSL certificates."
        print_warning "Options:"
        echo "  1. Use Let's Encrypt: certbot certonly --standalone -d $DOMAIN_NAME"
        echo "  2. Upload your own certificates to nginx/ssl/"
        echo "  3. Generate self-signed certificates for testing"
        
        read -p "Generate self-signed certificates for testing? (y/N): " generate_ssl
        if [ "$generate_ssl" = "y" ] || [ "$generate_ssl" = "Y" ]; then
            mkdir -p nginx/ssl
            openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
                -keyout nginx/ssl/privkey.pem \
                -out nginx/ssl/fullchain.pem \
                -subj "/C=US/ST=State/L=City/O=Organization/CN=$DOMAIN_NAME"
            print_status "Self-signed certificates generated"
        fi
    else
        print_status "Using localhost - SSL certificates not required"
    fi
else
    print_status "SSL certificates found"
fi

# Create necessary directories
print_header "Creating Required Directories"

directories=("nginx/ssl" "monitoring" "scripts" "backups")
for dir in "${directories[@]}"; do
    mkdir -p "$dir"
    print_status "Created directory: $dir"
done

# Start services
print_header "Starting MCP Platform Gateway"

print_status "Building and starting services..."
docker-compose up -d --build

# Wait for services to be ready
print_status "Waiting for services to start..."
sleep 10

# Check service health
print_header "Checking Service Health"

# Check if containers are running
services=("mcp_gateway_app" "mcp_gateway_db" "mcp_gateway_redis" "mcp_gateway_nginx")
for service in "${services[@]}"; do
    if [ "$(docker inspect -f '{{.State.Running}}' "$service" 2>/dev/null)" = "true" ]; then
        print_status "$service is running"
    else
        print_error "$service is not running"
        docker logs "$service" --tail 10
    fi
done

# Test gateway health endpoint
print_status "Testing gateway health endpoint..."
if curl -f -s "http://localhost/gateway/health" > /dev/null; then
    print_status "Gateway health check passed"
else
    print_warning "Gateway health check failed - service may still be starting"
fi

# Display access information
print_header "Deployment Complete"

print_status "MCP Platform Gateway is starting up!"
echo ""
echo "Access Information:"
echo "  • Gateway URL: http://$DOMAIN_NAME"
echo "  • Health Check: http://$DOMAIN_NAME/gateway/health"
echo "  • Logs: docker-compose logs -f mcp_gateway"
echo ""
echo "Management Commands:"
echo "  • Create admin user: docker-compose exec mcp_gateway python -m mcp_platform.gateway.cli create-user admin --superuser"
echo "  • Create API key: docker-compose exec mcp_gateway python -m mcp_platform.gateway.cli create-api-key admin --name 'API Key'"
echo "  • View status: docker-compose ps"
echo "  • Stop services: docker-compose down"
echo ""

if [ -f "nginx/ssl/fullchain.pem" ]; then
    echo "HTTPS URL: https://$DOMAIN_NAME"
fi

print_status "Setup complete! Check the logs for any issues: docker-compose logs -f"