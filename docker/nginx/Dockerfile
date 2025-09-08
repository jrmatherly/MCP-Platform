# Nginx Reverse Proxy for MCP Platform Gateway
# Provides SSL termination, load balancing, and security features with dynamic configuration

FROM nginx:alpine

# Install additional tools including gettext for envsubst
RUN apk add --no-cache \
    curl \
    wget \
    openssl \
    gettext \
    bash \
    && rm -rf /var/cache/apk/*

# Copy default nginx configuration
COPY nginx.conf /etc/nginx/nginx.conf

# Copy configuration generator and template
COPY generate-config.sh /usr/local/bin/generate-config.sh
COPY templates/ /etc/nginx/templates/

# Create directories for SSL certificates, configuration, and certbot
RUN mkdir -p /etc/nginx/ssl /etc/nginx/conf.d /var/www/certbot

# Create self-signed certificate for development fallback
RUN openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
    -keyout /etc/nginx/ssl/default.key \
    -out /etc/nginx/ssl/default.crt \
    -subj "/C=US/ST=State/L=City/O=MCP Platform/CN=localhost" \
    -addext "subjectAltName=DNS:localhost,IP:127.0.0.1"

# Set proper permissions
RUN chmod 600 /etc/nginx/ssl/default.key && \
    chmod 644 /etc/nginx/ssl/default.crt && \
    chmod +x /usr/local/bin/generate-config.sh

# Create non-root user (nginx runs as nginx user by default)
RUN chown -R nginx:nginx /var/cache/nginx /var/log/nginx

# Copy startup script
COPY docker-entrypoint.sh /docker-entrypoint.sh
RUN chmod +x /docker-entrypoint.sh

# Enhanced health check for HTTPS and HTTP
HEALTHCHECK --interval=30s --timeout=10s --retries=3 \
    CMD wget --quiet --tries=1 --spider https://localhost/health --no-check-certificate || \
    wget --quiet --tries=1 --spider http://localhost/health || exit 1

# Expose ports
EXPOSE 80 443

# Use custom entrypoint to generate configuration before starting nginx
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["nginx", "-g", "daemon off;"]