#!/bin/bash
# Certificate Renewal Script for MCP Platform
# Handles both Let's Encrypt renewal and manual certificate validation

set -e

# Load environment variables if .env exists
if [ -f "$(dirname "$0")/../.env" ]; then
    source "$(dirname "$0")/../.env"
fi

# Default values
SSL_CERTIFICATE_MODE=${SSL_CERTIFICATE_MODE:-manual}
DOMAIN_NAME=${DOMAIN_NAME:-localhost}
LETSENCRYPT_EMAIL=${LETSENCRYPT_EMAIL:-}
CERT_EXPIRY_WARNING_DAYS=${CERT_EXPIRY_WARNING_DAYS:-30}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "=== MCP Platform Certificate Renewal ==="
echo "Mode: $SSL_CERTIFICATE_MODE"
echo "Domain: $DOMAIN_NAME"
echo "Warning days: $CERT_EXPIRY_WARNING_DAYS"
echo ""

# Function to check certificate expiry
check_certificate_expiry() {
    local cert_path="$1"
    local warning_days="$2"
    
    if [ ! -f "$cert_path" ]; then
        echo -e "${RED}✗ Certificate not found: $cert_path${NC}"
        return 1
    fi
    
    # Get certificate expiry date
    local expiry_date
    expiry_date=$(openssl x509 -in "$cert_path" -noout -enddate | cut -d= -f2)
    
    if [ -z "$expiry_date" ]; then
        echo -e "${RED}✗ Could not read certificate expiry from $cert_path${NC}"
        return 1
    fi
    
    # Convert to epoch time
    local expiry_epoch
    expiry_epoch=$(date -d "$expiry_date" +%s 2>/dev/null || date -j -f "%b %d %T %Y %Z" "$expiry_date" +%s)
    local current_epoch
    current_epoch=$(date +%s)
    local warning_epoch
    warning_epoch=$((current_epoch + warning_days * 86400))
    
    # Calculate days until expiry
    local days_until_expiry
    days_until_expiry=$(( (expiry_epoch - current_epoch) / 86400 ))
    
    echo "Certificate expires: $expiry_date"
    echo "Days until expiry: $days_until_expiry"
    
    if [ "$expiry_epoch" -lt "$current_epoch" ]; then
        echo -e "${RED}✗ Certificate has EXPIRED${NC}"
        return 2
    elif [ "$expiry_epoch" -lt "$warning_epoch" ]; then
        echo -e "${YELLOW}⚠ Certificate expires within $warning_days days${NC}"
        return 1
    else
        echo -e "${GREEN}✓ Certificate is valid and not expiring soon${NC}"
        return 0
    fi
}

# Function to renew Let's Encrypt certificates
renew_letsencrypt() {
    echo "=== Let's Encrypt Certificate Renewal ==="
    
    if [ -z "$LETSENCRYPT_EMAIL" ]; then
        echo -e "${RED}✗ LETSENCRYPT_EMAIL not set${NC}"
        return 1
    fi
    
    echo "Checking for running certbot container..."
    if docker compose ps certbot --status running >/dev/null 2>&1; then
        echo "Certbot container is running, stopping it first..."
        docker compose stop certbot
    fi
    
    echo "Running certificate renewal..."
    docker compose run --rm certbot sh -c "
        certbot renew --webroot --webroot-path=/var/www/certbot --non-interactive &&
        echo 'Certificate renewal completed successfully'
    " || {
        echo -e "${RED}✗ Certificate renewal failed${NC}"
        return 1
    }
    
    echo "Reloading nginx configuration..."
    docker compose exec nginx nginx -s reload || {
        echo -e "${RED}✗ Failed to reload nginx${NC}"
        return 1
    }
    
    echo -e "${GREEN}✓ Let's Encrypt certificates renewed successfully${NC}"
    return 0
}

# Function to validate manual certificates
validate_manual_certs() {
    echo "=== Manual Certificate Validation ==="
    
    local cert_path="/etc/nginx/ssl/fullchain.pem"
    local key_path="/etc/nginx/ssl/privkey.pem"
    local issues=0
    
    # Check certificate file
    echo "Checking certificate: $cert_path"
    if docker compose exec nginx test -f "$cert_path"; then
        docker compose exec nginx openssl x509 -in "$cert_path" -text -noout >/dev/null || {
            echo -e "${RED}✗ Certificate file is corrupted${NC}"
            ((issues++))
        }
    else
        echo -e "${RED}✗ Certificate file not found${NC}"
        ((issues++))
    fi
    
    # Check private key file
    echo "Checking private key: $key_path"
    if docker compose exec nginx test -f "$key_path"; then
        docker compose exec nginx openssl rsa -in "$key_path" -check -noout >/dev/null 2>&1 || {
            echo -e "${RED}✗ Private key file is corrupted${NC}"
            ((issues++))
        }
    else
        echo -e "${RED}✗ Private key file not found${NC}"
        ((issues++))
    fi
    
    # Check certificate-key pair match
    if [ "$issues" -eq 0 ]; then
        echo "Validating certificate-key pair..."
        local cert_md5
        local key_md5
        cert_md5=$(docker compose exec nginx openssl x509 -in "$cert_path" -noout -modulus | openssl md5 | cut -d' ' -f2)
        key_md5=$(docker compose exec nginx openssl rsa -in "$key_path" -noout -modulus 2>/dev/null | openssl md5 | cut -d' ' -f2)
        
        if [ "$cert_md5" = "$key_md5" ]; then
            echo -e "${GREEN}✓ Certificate and key pair match${NC}"
        else
            echo -e "${RED}✗ Certificate and private key do not match${NC}"
            ((issues++))
        fi
        
        # Check certificate expiry
        check_certificate_expiry "$cert_path" "$CERT_EXPIRY_WARNING_DAYS" || ((issues++))
    fi
    
    if [ "$issues" -eq 0 ]; then
        echo -e "${GREEN}✓ Manual certificates are valid${NC}"
        return 0
    else
        echo -e "${RED}✗ Found $issues issue(s) with manual certificates${NC}"
        return 1
    fi
}

# Function to test SSL configuration
test_ssl_config() {
    echo "=== SSL Configuration Test ==="
    
    echo "Testing nginx configuration..."
    if docker compose exec nginx nginx -t; then
        echo -e "${GREEN}✓ Nginx configuration is valid${NC}"
    else
        echo -e "${RED}✗ Nginx configuration has errors${NC}"
        return 1
    fi
    
    echo "Testing SSL endpoint..."
    if curl -k -s --connect-timeout 10 "https://localhost:${NGINX_HTTPS_PORT:-8443}/health" >/dev/null 2>&1; then
        echo -e "${GREEN}✓ SSL endpoint is responding${NC}"
    else
        echo -e "${YELLOW}⚠ SSL endpoint test failed (may be expected in development)${NC}"
    fi
    
    return 0
}

# Main execution
main() {
    case "$SSL_CERTIFICATE_MODE" in
        "letsencrypt")
            renew_letsencrypt
            ;;
        "manual")
            validate_manual_certs
            ;;
        "auto")
            echo "Auto mode: attempting to detect certificate type..."
            if docker compose exec nginx test -f "/etc/letsencrypt/live/$DOMAIN_NAME/fullchain.pem"; then
                echo "Detected Let's Encrypt certificates"
                SSL_CERTIFICATE_MODE="letsencrypt"
                renew_letsencrypt
            else
                echo "Detected manual certificates"
                SSL_CERTIFICATE_MODE="manual"
                validate_manual_certs
            fi
            ;;
        *)
            echo -e "${RED}✗ Unknown SSL_CERTIFICATE_MODE: $SSL_CERTIFICATE_MODE${NC}"
            echo "Valid modes: manual, letsencrypt, auto"
            exit 1
            ;;
    esac
    
    # Test SSL configuration regardless of mode
    test_ssl_config
}

# Help function
show_help() {
    cat << EOF
MCP Platform Certificate Renewal Script

Usage: $0 [options]

Options:
  -h, --help     Show this help message
  -f, --force    Force renewal even if certificates are not expiring soon
  -t, --test     Test SSL configuration only (no renewal)

Environment Variables:
  SSL_CERTIFICATE_MODE    Certificate mode (manual|letsencrypt|auto)
  DOMAIN_NAME            Domain name for certificates
  LETSENCRYPT_EMAIL      Email for Let's Encrypt registration
  CERT_EXPIRY_WARNING_DAYS  Days before expiry to show warnings

Examples:
  $0                     # Renew/validate based on SSL_CERTIFICATE_MODE
  $0 --test             # Test SSL configuration only
  $0 --force            # Force renewal regardless of expiry

EOF
}

# Parse command line arguments
FORCE_RENEWAL=false
TEST_ONLY=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -f|--force)
            FORCE_RENEWAL=true
            shift
            ;;
        -t|--test)
            TEST_ONLY=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Execute main function or test only
if [ "$TEST_ONLY" = true ]; then
    test_ssl_config
else
    main
fi

echo ""
echo "=== Certificate renewal script completed ==="