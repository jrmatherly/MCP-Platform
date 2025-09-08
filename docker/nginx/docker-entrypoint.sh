#!/bin/bash
# Docker entrypoint for MCP Platform Nginx
# Generates configuration based on environment variables before starting nginx

set -e

# Default environment variables
export DOMAIN_NAME=${DOMAIN_NAME:-localhost}
export SSL_CERTIFICATE_MODE=${SSL_CERTIFICATE_MODE:-manual}
export SSL_CERT_PATH=${SSL_CERT_PATH:-/etc/nginx/ssl/fullchain.pem}
export SSL_KEY_PATH=${SSL_KEY_PATH:-/etc/nginx/ssl/privkey.pem}
export LETSENCRYPT_EMAIL=${LETSENCRYPT_EMAIL:-}
export LETSENCRYPT_DOMAINS=${LETSENCRYPT_DOMAINS:-$DOMAIN_NAME}
export CERT_EXPIRY_WARNING_DAYS=${CERT_EXPIRY_WARNING_DAYS:-30}

echo "=== MCP Platform Nginx Startup ==="
echo "Domain: $DOMAIN_NAME"
echo "Certificate Mode: $SSL_CERTIFICATE_MODE"
echo "Certificate Path: $SSL_CERT_PATH"
echo "Private Key Path: $SSL_KEY_PATH"

# Function to wait for file to exist
wait_for_file() {
    local file_path="$1"
    local max_wait="${2:-30}"
    local waited=0
    
    while [ ! -f "$file_path" ] && [ $waited -lt $max_wait ]; do
        echo "Waiting for $file_path to exist... ($waited/$max_wait seconds)"
        sleep 1
        ((waited++))
    done
    
    if [ ! -f "$file_path" ]; then
        echo "Warning: $file_path not found after ${max_wait}s"
        return 1
    fi
    
    return 0
}

# Function to check certificate validity
check_certificate() {
    local cert_path="$1"
    
    if [ ! -f "$cert_path" ]; then
        return 1
    fi
    
    # Check if certificate is readable and valid
    if openssl x509 -in "$cert_path" -noout -text >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Generate nginx configuration based on certificate mode
echo "Generating nginx configuration..."

# Run the configuration generator
if ! /usr/local/bin/generate-config.sh; then
    echo "Error: Failed to generate nginx configuration"
    exit 1
fi

# Additional certificate-specific setup
case "$SSL_CERTIFICATE_MODE" in
    "letsencrypt")
        echo "Let's Encrypt mode: Checking for certificates..."
        
        # Check if Let's Encrypt certificates exist
        LETSENCRYPT_CERT="/etc/letsencrypt/live/$DOMAIN_NAME/fullchain.pem"
        LETSENCRYPT_KEY="/etc/letsencrypt/live/$DOMAIN_NAME/privkey.pem"
        
        if [ -f "$LETSENCRYPT_CERT" ] && [ -f "$LETSENCRYPT_KEY" ]; then
            echo "Found existing Let's Encrypt certificates"
            # Update paths to use Let's Encrypt certificates
            export SSL_CERT_PATH="$LETSENCRYPT_CERT"
            export SSL_KEY_PATH="$LETSENCRYPT_KEY"
        else
            echo "No Let's Encrypt certificates found - using fallback certificates"
            echo "Note: Certbot should generate certificates on first run"
        fi
        ;;
        
    "manual")
        echo "Manual certificate mode: Validating certificates..."
        
        if check_certificate "$SSL_CERT_PATH"; then
            echo "Manual certificates found and valid"
        else
            echo "Warning: Manual certificates not found or invalid, using fallback"
            export SSL_CERT_PATH="/etc/nginx/ssl/default.crt"
            export SSL_KEY_PATH="/etc/nginx/ssl/default.key"
        fi
        ;;
        
    "auto")
        echo "Auto mode: Detecting certificate type..."
        
        LETSENCRYPT_CERT="/etc/letsencrypt/live/$DOMAIN_NAME/fullchain.pem"
        if [ -f "$LETSENCRYPT_CERT" ]; then
            echo "Auto-detected: Using Let's Encrypt certificates"
            export SSL_CERT_PATH="$LETSENCRYPT_CERT"
            export SSL_KEY_PATH="/etc/letsencrypt/live/$DOMAIN_NAME/privkey.pem"
        elif check_certificate "$SSL_CERT_PATH"; then
            echo "Auto-detected: Using manual certificates"
        else
            echo "Auto-detected: Using fallback certificates"
            export SSL_CERT_PATH="/etc/nginx/ssl/default.crt"
            export SSL_KEY_PATH="/etc/nginx/ssl/default.key"
        fi
        ;;
esac

echo "Final certificate configuration:"
echo "  Certificate: $SSL_CERT_PATH"
echo "  Private Key: $SSL_KEY_PATH"

# Validate that final certificate files exist
if [ ! -f "$SSL_CERT_PATH" ]; then
    echo "Error: Certificate file not found: $SSL_CERT_PATH"
    echo "Using default fallback certificates"
    export SSL_CERT_PATH="/etc/nginx/ssl/default.crt"
    export SSL_KEY_PATH="/etc/nginx/ssl/default.key"
fi

# Re-generate configuration with updated paths if needed
if [ "$SSL_CERT_PATH" != "${SSL_CERT_PATH_ORIGINAL:-$SSL_CERT_PATH}" ]; then
    echo "Re-generating configuration with updated certificate paths..."
    /usr/local/bin/generate-config.sh
fi

# Test nginx configuration
echo "Testing nginx configuration..."
if nginx -t; then
    echo "✓ Nginx configuration is valid"
else
    echo "✗ Nginx configuration is invalid"
    echo "Configuration details:"
    cat /etc/nginx/conf.d/gateway.conf
    exit 1
fi

# Show certificate information
if [ -f "$SSL_CERT_PATH" ]; then
    echo "Certificate information:"
    echo "  Subject: $(openssl x509 -in "$SSL_CERT_PATH" -noout -subject 2>/dev/null | cut -d= -f2- || echo 'unknown')"
    echo "  Issuer: $(openssl x509 -in "$SSL_CERT_PATH" -noout -issuer 2>/dev/null | cut -d= -f2- || echo 'unknown')"
    echo "  Expires: $(openssl x509 -in "$SSL_CERT_PATH" -noout -enddate 2>/dev/null | cut -d= -f2 || echo 'unknown')"
    echo "  Alt Names: $(openssl x509 -in "$SSL_CERT_PATH" -noout -text 2>/dev/null | grep -A1 "Subject Alternative Name" | tail -n1 | sed 's/^[[:space:]]*//' || echo 'none')"
fi

echo "=== Starting Nginx ==="

# Execute the command passed to docker run
exec "$@"