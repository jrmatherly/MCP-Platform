#!/bin/bash
# Nginx Configuration Generator for MCP Platform
# Processes templates based on SSL certificate configuration

set -e

# Default values
DOMAIN_NAME=${DOMAIN_NAME:-localhost}
SSL_CERTIFICATE_MODE=${SSL_CERTIFICATE_MODE:-manual}
SSL_CERT_PATH=${SSL_CERT_PATH:-/etc/nginx/ssl/fullchain.pem}
SSL_KEY_PATH=${SSL_KEY_PATH:-/etc/nginx/ssl/privkey.pem}
LETSENCRYPT_EMAIL=${LETSENCRYPT_EMAIL:-admin@localhost}
LETSENCRYPT_DOMAINS=${LETSENCRYPT_DOMAINS:-$DOMAIN_NAME}
CERT_EXPIRY_WARNING_DAYS=${CERT_EXPIRY_WARNING_DAYS:-30}

# Template and output paths
TEMPLATE_DIR="/etc/nginx/templates"
CONFIG_DIR="/etc/nginx/conf.d"
TEMPLATE_FILE="$TEMPLATE_DIR/gateway.conf.template"
OUTPUT_FILE="$CONFIG_DIR/gateway.conf"

echo "=== MCP Platform Nginx Configuration Generator ==="
echo "Certificate Mode: $SSL_CERTIFICATE_MODE"
echo "Domain: $DOMAIN_NAME"
echo "Template: $TEMPLATE_FILE"
echo "Output: $OUTPUT_FILE"

# Ensure directories exist
mkdir -p "$CONFIG_DIR"

# Function to check if certificate exists and is valid
check_certificate() {
    local cert_path="$1"
    if [ -f "$cert_path" ]; then
        # Check if certificate is valid and not expired
        if openssl x509 -in "$cert_path" -noout -checkend 0 >/dev/null 2>&1; then
            echo "Certificate at $cert_path is valid"
            return 0
        else
            echo "Certificate at $cert_path exists but is expired or invalid"
            return 1
        fi
    else
        echo "Certificate at $cert_path does not exist"
        return 1
    fi
}

# Function to get certificate expiry date
get_cert_expiry() {
    local cert_path="$1"
    if [ -f "$cert_path" ]; then
        openssl x509 -in "$cert_path" -noout -enddate 2>/dev/null | cut -d= -f2 || echo "unknown"
    else
        echo "no-certificate"
    fi
}

# Determine actual certificate mode based on file existence and configuration
ACTUAL_MODE="$SSL_CERTIFICATE_MODE"
if [ "$SSL_CERTIFICATE_MODE" = "auto" ]; then
    if check_certificate "$SSL_CERT_PATH"; then
        ACTUAL_MODE="manual"
        echo "Auto-detected: Using manual certificates"
    else
        ACTUAL_MODE="letsencrypt"
        echo "Auto-detected: Using Let's Encrypt (no manual certificates found)"
    fi
fi

# Set certificate paths based on mode
if [ "$ACTUAL_MODE" = "letsencrypt" ]; then
    SSL_CERT_PATH="/etc/letsencrypt/live/$DOMAIN_NAME/fullchain.pem"
    SSL_KEY_PATH="/etc/letsencrypt/live/$DOMAIN_NAME/privkey.pem"
    echo "Let's Encrypt mode: Using certificates from $SSL_CERT_PATH"
else
    echo "Manual mode: Using certificates from $SSL_CERT_PATH"
fi

# Get certificate expiry for status endpoint
CERT_EXPIRES=$(get_cert_expiry "$SSL_CERT_PATH")

# Generate configuration from template
if [ ! -f "$TEMPLATE_FILE" ]; then
    echo "ERROR: Template file $TEMPLATE_FILE not found"
    exit 1
fi

echo "Generating nginx configuration..."

# Process template with environment variable substitution
envsubst '$DOMAIN_NAME $SSL_CERT_PATH $SSL_KEY_PATH $SSL_CERTIFICATE_MODE $CERT_EXPIRES' < "$TEMPLATE_FILE" > "$OUTPUT_FILE.tmp"

# Post-process the configuration based on certificate mode
if [ "$ACTUAL_MODE" = "manual" ]; then
    # For manual mode, remove Let's Encrypt ACME challenge location
    echo "Configuring for manual certificates..."
    sed -i '/# Conditional Let'"'"'s Encrypt ACME challenges/,/}/d' "$OUTPUT_FILE.tmp"
else
    # For Let's Encrypt mode, keep ACME challenges
    echo "Configuring for Let's Encrypt certificates..."
fi

# Move final configuration into place
mv "$OUTPUT_FILE.tmp" "$OUTPUT_FILE"

echo "Configuration generated successfully at $OUTPUT_FILE"

# Validate nginx configuration
if command -v nginx >/dev/null 2>&1; then
    echo "Validating nginx configuration..."
    if nginx -t 2>/dev/null; then
        echo "✓ Nginx configuration is valid"
    else
        echo "✗ Nginx configuration validation failed"
        nginx -t
        exit 1
    fi
else
    echo "Warning: nginx not found in PATH, skipping configuration validation"
fi

# Show certificate status
echo ""
echo "=== Certificate Status ==="
echo "Mode: $ACTUAL_MODE"
echo "Certificate: $SSL_CERT_PATH"
echo "Private Key: $SSL_KEY_PATH"
echo "Expires: $CERT_EXPIRES"

if [ "$ACTUAL_MODE" = "manual" ]; then
    if check_certificate "$SSL_CERT_PATH"; then
        echo "✓ Manual certificate is valid and ready"
    else
        echo "⚠ Manual certificate is missing or invalid"
        echo "  Make sure to mount valid certificates to $SSL_CERT_PATH"
    fi
elif [ "$ACTUAL_MODE" = "letsencrypt" ]; then
    echo "ℹ Let's Encrypt mode configured"
    echo "  ACME challenges enabled at /.well-known/acme-challenge/"
    echo "  Certificates will be obtained for: $LETSENCRYPT_DOMAINS"
    echo "  Contact email: $LETSENCRYPT_EMAIL"
fi

echo "=== Configuration Complete ==="