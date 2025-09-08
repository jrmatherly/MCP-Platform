#!/bin/bash
# Certificate Initialization Script for MCP Platform
# Sets up certificates for first-time deployment

set -e

# Load environment variables if .env exists
if [ -f "$(dirname "$0")/../.env" ]; then
    source "$(dirname "$0")/../.env"
fi

# Default values
SSL_CERTIFICATE_MODE=${SSL_CERTIFICATE_MODE:-manual}
DOMAIN_NAME=${DOMAIN_NAME:-localhost}
LETSENCRYPT_EMAIL=${LETSENCRYPT_EMAIL:-}
LETSENCRYPT_STAGING=${LETSENCRYPT_STAGING:-false}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo "=== MCP Platform Certificate Initialization ==="
echo "Mode: $SSL_CERTIFICATE_MODE"
echo "Domain: $DOMAIN_NAME"
echo ""

# Function to create self-signed certificates
create_self_signed() {
    local cert_dir="$1"
    local domain="$2"
    
    echo "Creating self-signed certificate for $domain..."
    
    mkdir -p "$cert_dir"
    
    # Generate private key
    openssl genrsa -out "$cert_dir/privkey.pem" 2048
    
    # Generate certificate
    openssl req -new -x509 -key "$cert_dir/privkey.pem" -out "$cert_dir/fullchain.pem" -days 365 \
        -subj "/C=US/ST=Development/L=Local/O=MCP Platform/CN=$domain" \
        -addext "subjectAltName=DNS:$domain,DNS:www.$domain,DNS:localhost,IP:127.0.0.1"
    
    # Set proper permissions
    chmod 600 "$cert_dir/privkey.pem"
    chmod 644 "$cert_dir/fullchain.pem"
    
    echo -e "${GREEN}✓ Self-signed certificate created${NC}"
    echo "  Certificate: $cert_dir/fullchain.pem"
    echo "  Private Key: $cert_dir/privkey.pem"
    echo "  Valid for: 365 days"
    echo "  Domains: $domain, www.$domain, localhost"
}

# Function to initialize Let's Encrypt
init_letsencrypt() {
    echo "=== Let's Encrypt Initialization ==="
    
    if [ -z "$LETSENCRYPT_EMAIL" ]; then
        echo -e "${RED}✗ LETSENCRYPT_EMAIL is required for Let's Encrypt mode${NC}"
        echo "Please set LETSENCRYPT_EMAIL in your .env file"
        exit 1
    fi
    
    # Create directories
    echo "Creating Let's Encrypt directories..."
    docker compose run --rm certbot sh -c "mkdir -p /etc/letsencrypt /var/www/certbot"
    
    # Test domain reachability
    echo "Testing domain reachability..."
    if [ "$LETSENCRYPT_STAGING" != "true" ]; then
        echo -e "${YELLOW}⚠ Production mode - make sure $DOMAIN_NAME points to this server${NC}"
        echo "Press Enter to continue or Ctrl+C to abort..."
        read -r
    fi
    
    # Generate initial certificate
    echo "Generating initial Let's Encrypt certificate..."
    local staging_flag=""
    if [ "$LETSENCRYPT_STAGING" = "true" ]; then
        staging_flag="--staging"
        echo -e "${BLUE}Using Let's Encrypt staging server${NC}"
    fi
    
    docker compose run --rm certbot sh -c "
        certbot certonly 
            --webroot 
            --webroot-path=/var/www/certbot 
            --email $LETSENCRYPT_EMAIL 
            --agree-tos 
            --no-eff-email 
            --non-interactive 
            --domains $DOMAIN_NAME 
            $staging_flag
    " || {
        echo -e "${RED}✗ Let's Encrypt certificate generation failed${NC}"
        echo ""
        echo "Common issues:"
        echo "1. Domain $DOMAIN_NAME doesn't point to this server"
        echo "2. Port 80 is not accessible from the internet"
        echo "3. Firewall blocking HTTP traffic"
        echo ""
        echo "For testing, try setting LETSENCRYPT_STAGING=true"
        exit 1
    }
    
    echo -e "${GREEN}✓ Let's Encrypt certificate generated successfully${NC}"
    
    # Set up auto-renewal cron job hint
    echo ""
    echo -e "${BLUE}Auto-renewal setup:${NC}"
    echo "Add this to your crontab for automatic renewal:"
    echo "0 2 * * * $(pwd)/scripts/renew-certificates.sh"
}

# Function to initialize manual certificates
init_manual() {
    echo "=== Manual Certificate Initialization ==="
    
    local ssl_dir="docker/nginx/ssl"
    local cert_file="$ssl_dir/fullchain.pem"
    local key_file="$ssl_dir/privkey.pem"
    
    # Check if certificates already exist
    if [ -f "$cert_file" ] && [ -f "$key_file" ]; then
        echo -e "${YELLOW}⚠ Manual certificates already exist${NC}"
        echo "Certificate: $cert_file"
        echo "Private Key: $key_file"
        echo ""
        echo "Options:"
        echo "1. Keep existing certificates"
        echo "2. Replace with self-signed certificates"
        echo "3. Replace with your own certificates"
        echo ""
        read -p "Choose option (1-3): " choice
        
        case $choice in
            1)
                echo "Keeping existing certificates"
                return 0
                ;;
            2)
                echo "Replacing with self-signed certificates..."
                ;;
            3)
                echo ""
                echo "To use your own certificates:"
                echo "1. Copy your certificate to: $cert_file"
                echo "2. Copy your private key to: $key_file"
                echo "3. Ensure proper permissions (600 for key, 644 for cert)"
                echo "4. Restart the nginx service: docker compose restart nginx"
                echo ""
                echo "Press Enter when done or Ctrl+C to abort..."
                read -r
                return 0
                ;;
            *)
                echo "Invalid choice"
                exit 1
                ;;
        esac
    fi
    
    # Create self-signed certificates as fallback
    create_self_signed "$ssl_dir" "$DOMAIN_NAME"
    
    echo ""
    echo -e "${BLUE}Manual Certificate Setup:${NC}"
    echo "For production, replace the self-signed certificates with:"
    echo "1. Your SSL certificate chain → $cert_file"
    echo "2. Your private key → $key_file"
    echo ""
    echo "Certificate requirements:"
    echo "- Must be in PEM format"
    echo "- Certificate should include the full chain (cert + intermediates)"
    echo "- Private key should be unencrypted"
    echo "- Both files should be readable by the nginx process"
}

# Function to validate initialization
validate_setup() {
    echo "=== Validation ==="
    
    # Check if docker compose file exists
    if [ ! -f "docker-compose.yml" ]; then
        echo -e "${RED}✗ docker-compose.yml not found${NC}"
        echo "Please run this script from the project root directory"
        exit 1
    fi
    
    # Check if nginx template exists
    if [ ! -f "docker/nginx/templates/gateway.conf.template" ]; then
        echo -e "${RED}✗ Nginx template not found${NC}"
        echo "Please ensure docker/nginx/templates/gateway.conf.template exists"
        exit 1
    fi
    
    # Check if generate-config.sh exists
    if [ ! -f "docker/nginx/generate-config.sh" ]; then
        echo -e "${RED}✗ Configuration generator not found${NC}"
        echo "Please ensure docker/nginx/generate-config.sh exists"
        exit 1
    fi
    
    echo -e "${GREEN}✓ Basic setup validation passed${NC}"
}

# Function to start services
start_services() {
    echo "=== Starting Services ==="
    
    echo "Building and starting nginx service..."
    docker compose build nginx
    docker compose up -d nginx
    
    # Wait for nginx to be ready
    echo "Waiting for nginx to be ready..."
    local retries=0
    while [ $retries -lt 30 ]; do
        if curl -s --connect-timeout 5 "http://localhost:${NGINX_HTTP_PORT:-8080}/health" >/dev/null 2>&1; then
            break
        fi
        ((retries++))
        sleep 2
    done
    
    if [ $retries -eq 30 ]; then
        echo -e "${RED}✗ Nginx failed to start within 60 seconds${NC}"
        echo "Check logs: docker compose logs nginx"
        exit 1
    fi
    
    echo -e "${GREEN}✓ Nginx started successfully${NC}"
    
    # Test HTTPS endpoint
    if curl -k -s --connect-timeout 5 "https://localhost:${NGINX_HTTPS_PORT:-8443}/health" >/dev/null 2>&1; then
        echo -e "${GREEN}✓ HTTPS endpoint is working${NC}"
    else
        echo -e "${YELLOW}⚠ HTTPS endpoint test failed (check certificate configuration)${NC}"
    fi
}

# Main execution
main() {
    validate_setup
    
    case "$SSL_CERTIFICATE_MODE" in
        "manual")
            init_manual
            ;;
        "letsencrypt")
            init_letsencrypt
            ;;
        "auto")
            echo "Auto mode: choosing best option based on environment..."
            if [ -n "$LETSENCRYPT_EMAIL" ] && [ "$DOMAIN_NAME" != "localhost" ]; then
                echo "Detected Let's Encrypt configuration"
                SSL_CERTIFICATE_MODE="letsencrypt"
                init_letsencrypt
            else
                echo "Using manual certificate mode"
                SSL_CERTIFICATE_MODE="manual"
                init_manual
            fi
            ;;
        *)
            echo -e "${RED}✗ Unknown SSL_CERTIFICATE_MODE: $SSL_CERTIFICATE_MODE${NC}"
            echo "Valid modes: manual, letsencrypt, auto"
            exit 1
            ;;
    esac
    
    start_services
    
    echo ""
    echo -e "${GREEN}=== Certificate initialization completed ===${NC}"
    echo "Mode: $SSL_CERTIFICATE_MODE"
    echo "Domain: $DOMAIN_NAME"
    echo ""
    echo "Next steps:"
    echo "1. Test your setup: curl -k https://localhost:${NGINX_HTTPS_PORT:-8443}/health"
    echo "2. Check certificate status: ./scripts/renew-certificates.sh --test"
    echo "3. View logs: docker compose logs nginx"
    if [ "$SSL_CERTIFICATE_MODE" = "letsencrypt" ]; then
        echo "4. Set up auto-renewal: crontab -e (add: 0 2 * * * $(pwd)/scripts/renew-certificates.sh)"
    fi
}

# Help function
show_help() {
    cat << EOF
MCP Platform Certificate Initialization Script

Usage: $0 [options]

Options:
  -h, --help     Show this help message
  -f, --force    Force reinitialization even if certificates exist

Environment Variables:
  SSL_CERTIFICATE_MODE    Certificate mode (manual|letsencrypt|auto)
  DOMAIN_NAME            Domain name for certificates
  LETSENCRYPT_EMAIL      Email for Let's Encrypt registration
  LETSENCRYPT_STAGING    Use staging server (true/false)

Examples:
  $0                     # Initialize based on SSL_CERTIFICATE_MODE
  $0 --force            # Force reinitialization

EOF
}

# Parse command line arguments
FORCE_INIT=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -f|--force)
            FORCE_INIT=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Check if running from correct directory
if [ ! -f "docker-compose.yml" ]; then
    echo -e "${RED}✗ Please run this script from the MCP Platform root directory${NC}"
    exit 1
fi

# Execute main function
main