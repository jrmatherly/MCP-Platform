# Certificate Management Guide

This guide explains how to configure and manage SSL/TLS certificates for the MCP Platform gateway using either manual certificates or Let's Encrypt automation.

## Quick Start

### 1. Configure Environment Variables

Copy and edit the environment configuration:
```bash
cp .env.example .env
# Edit .env with your certificate preferences
```

Key certificate-related variables:
```bash
# Certificate management mode
SSL_CERTIFICATE_MODE=manual          # Options: manual, letsencrypt, auto

# Manual certificate paths (when mode=manual)
SSL_CERT_PATH=/etc/nginx/ssl/fullchain.pem
SSL_KEY_PATH=/etc/nginx/ssl/privkey.pem

# Let's Encrypt configuration (when mode=letsencrypt)
DOMAIN_NAME=gateway.yourdomain.com
LETSENCRYPT_EMAIL=your-email@domain.com
LETSENCRYPT_STAGING=false            # Set to true for testing

# Monitoring
CERT_EXPIRY_WARNING_DAYS=30
```

### 2. Initialize Certificates

Run the initialization script:
```bash
./scripts/init-certificates.sh
```

This will:
- Validate your configuration
- Set up certificates based on your mode
- Start the nginx service
- Perform basic health checks

### 3. Deploy the Stack

```bash
# For gateway with manual certificates
docker compose --profile gateway up -d

# For full production stack with Let's Encrypt
docker compose --profile production up -d
```

## Certificate Modes

### Manual Certificates

**When to use**: You have your own SSL certificates (purchased, corporate CA, etc.)

**Configuration**:
```bash
SSL_CERTIFICATE_MODE=manual
SSL_CERT_PATH=/etc/nginx/ssl/fullchain.pem
SSL_KEY_PATH=/etc/nginx/ssl/privkey.pem
```

**Setup**:
1. Place your certificate chain in `docker/nginx/ssl/fullchain.pem`
2. Place your private key in `docker/nginx/ssl/privkey.pem`
3. Ensure proper permissions (644 for cert, 600 for key)
4. Run `./scripts/init-certificates.sh`

**Certificate Requirements**:
- Must be in PEM format
- Certificate file should include the full chain (certificate + intermediates)
- Private key should be unencrypted
- Must match the domain name in `DOMAIN_NAME`

### Let's Encrypt Automation

**When to use**: You want free, automatically-renewing SSL certificates

**Configuration**:
```bash
SSL_CERTIFICATE_MODE=letsencrypt
DOMAIN_NAME=gateway.yourdomain.com
LETSENCRYPT_EMAIL=your-email@domain.com
LETSENCRYPT_STAGING=false  # Set to true for testing
```

**Prerequisites**:
1. Domain must point to your server
2. Port 80 must be accessible from the internet
3. No other service using port 80

**Setup**:
1. Configure environment variables
2. Run `./scripts/init-certificates.sh`
3. Certificates will be automatically obtained and renewed

**Testing with Staging**:
For testing, use the staging environment:
```bash
LETSENCRYPT_STAGING=true
```
This avoids rate limits and issues staging certificates.

### Auto Detection

**When to use**: You want the system to choose the best option automatically

**Configuration**:
```bash
SSL_CERTIFICATE_MODE=auto
```

**Logic**:
- If `LETSENCRYPT_EMAIL` is set and domain is not localhost → Let's Encrypt
- Otherwise → Manual mode with self-signed fallback

## Certificate Management Scripts

### Initialize Certificates
```bash
./scripts/init-certificates.sh [options]

Options:
  -h, --help     Show help message
  -f, --force    Force reinitialization
```

Creates initial certificate setup based on your configuration.

### Renew/Validate Certificates
```bash
./scripts/renew-certificates.sh [options]

Options:
  -h, --help     Show help message
  -f, --force    Force renewal regardless of expiry
  -t, --test     Test SSL configuration only
```

Handles certificate renewal and validation:
- **Let's Encrypt mode**: Renews certificates using certbot
- **Manual mode**: Validates existing certificates and checks expiry
- **Auto mode**: Detects certificate type and handles accordingly

### Set Up Auto-Renewal (Let's Encrypt)

Add to your crontab for automatic certificate renewal:
```bash
crontab -e
# Add this line:
0 2 * * * /path/to/mcp-platform/scripts/renew-certificates.sh
```

## Monitoring and Health Checks

### Certificate Status Endpoint

Check certificate status via API:
```bash
curl -k https://localhost:8443/.well-known/certificate-status
```

Response includes:
- Certificate mode
- Expiry information
- Status

### Certificate Monitor Service

The `cert-monitor` service continuously monitors certificates:
- Checks certificate expiry every hour
- Logs warnings when certificates are near expiry
- Tests SSL endpoint availability
- Stores logs in `/var/log/cert-monitor/`

View monitoring logs:
```bash
docker compose logs cert-monitor
```

### Health Checks

The nginx service includes enhanced health checks:
```bash
# Check via HTTP
curl http://localhost:8080/health

# Check via HTTPS (ignoring certificate warnings)
curl -k https://localhost:8443/health
```

## Troubleshooting

### Common Issues

#### 1. Let's Encrypt Certificate Generation Fails

**Symptoms**: Certbot container exits with errors

**Solutions**:
- Verify domain points to your server: `nslookup your-domain.com`
- Check port 80 accessibility: `curl http://your-domain.com/.well-known/acme-challenge/test`
- Try staging mode first: `LETSENCRYPT_STAGING=true`
- Check firewall settings

#### 2. Manual Certificates Not Working

**Symptoms**: SSL errors, browser certificate warnings

**Solutions**:
- Verify certificate format: `openssl x509 -in cert.pem -text -noout`
- Check certificate-key pair: `./scripts/renew-certificates.sh --test`
- Validate certificate chain completeness
- Check file permissions (644 for cert, 600 for key)

#### 3. Certificate Expiry Warnings

**Symptoms**: Monitor logs showing expiry warnings

**Solutions**:
- For Let's Encrypt: Run renewal script `./scripts/renew-certificates.sh`
- For manual: Replace certificates and restart nginx
- Check auto-renewal cron job (Let's Encrypt)

#### 4. Nginx Configuration Errors

**Symptoms**: Nginx fails to start, configuration test fails

**Solutions**:
```bash
# Test configuration
docker compose exec nginx nginx -t

# Check generated config
docker compose exec nginx cat /etc/nginx/conf.d/gateway.conf

# Regenerate configuration
docker compose exec nginx /usr/local/bin/generate-config.sh

# Restart nginx
docker compose restart nginx
```

### Debug Commands

#### Check Certificate Details
```bash
# Manual certificates
openssl x509 -in docker/nginx/ssl/fullchain.pem -text -noout

# Let's Encrypt certificates
docker compose exec nginx openssl x509 -in /etc/letsencrypt/live/yourdomain.com/fullchain.pem -text -noout
```

#### Test SSL Connection
```bash
# Test local SSL
openssl s_client -connect localhost:8443 -servername yourdomain.com

# Test with curl
curl -vk https://localhost:8443/health
```

#### View Configuration
```bash
# Generated nginx config
docker compose exec nginx cat /etc/nginx/conf.d/gateway.conf

# Environment variables
docker compose exec nginx env | grep -E "(SSL_|DOMAIN_|LETSENCRYPT_)"
```

## Production Deployment Checklist

### Before Deployment

- [ ] Configure environment variables in `.env`
- [ ] Set appropriate `SSL_CERTIFICATE_MODE`
- [ ] For Let's Encrypt: Verify domain DNS and port 80 access
- [ ] For manual: Prepare certificate files
- [ ] Test configuration with staging/development setup

### Initial Deployment

- [ ] Run `./scripts/init-certificates.sh`
- [ ] Deploy with appropriate profile: `docker compose --profile production up -d`
- [ ] Verify certificate status: `curl -k https://localhost:8443/.well-known/certificate-status`
- [ ] Test application endpoints
- [ ] Check monitoring logs

### Post-Deployment

- [ ] Set up auto-renewal cron job (Let's Encrypt)
- [ ] Configure monitoring alerts for certificate expiry
- [ ] Document certificate renewal procedures
- [ ] Test disaster recovery procedures

## Security Best Practices

### Certificate Security
- Use strong private keys (2048-bit RSA minimum)
- Keep private keys secure and unencrypted in storage
- Use full certificate chains including intermediates
- Enable OCSP stapling for certificate status checking

### Container Security
- Mount certificate directories as read-only where possible
- Use minimal privileges for certificate access
- Regularly update base images
- Monitor certificate access logs

### Network Security
- Restrict access to certificate management endpoints
- Use HTTPS redirects for all traffic
- Enable HSTS headers in production
- Configure proper firewall rules

## Advanced Configuration

### Custom Certificate Paths

Override default paths in docker-compose.yml:
```yaml
nginx:
  environment:
    SSL_CERT_PATH: /custom/path/cert.pem
    SSL_KEY_PATH: /custom/path/key.pem
  volumes:
    - /host/custom/path:/custom/path:ro
```

### Multiple Domains

Configure multiple domains for Let's Encrypt:
```bash
LETSENCRYPT_DOMAINS=example.com,www.example.com,api.example.com
```

### Certificate Pinning

For additional security, implement certificate pinning:
```nginx
# In nginx configuration
add_header Public-Key-Pins 'pin-sha256="..."; max-age=2592000; includeSubDomains';
```

## Migration Between Modes

### From Manual to Let's Encrypt

1. Update environment variables:
   ```bash
   SSL_CERTIFICATE_MODE=letsencrypt
   LETSENCRYPT_EMAIL=your-email@domain.com
   ```
2. Run certificate initialization:
   ```bash
   ./scripts/init-certificates.sh --force
   ```
3. Set up auto-renewal cron job

### From Let's Encrypt to Manual

1. Export current Let's Encrypt certificates:
   ```bash
   docker compose exec nginx cp /etc/letsencrypt/live/yourdomain.com/fullchain.pem /etc/nginx/ssl/
   docker compose exec nginx cp /etc/letsencrypt/live/yourdomain.com/privkey.pem /etc/nginx/ssl/
   ```
2. Update environment variables:
   ```bash
   SSL_CERTIFICATE_MODE=manual
   ```
3. Restart services:
   ```bash
   docker compose restart nginx
   ```

## Support and Resources

- **Script Help**: Run any script with `--help` for detailed usage
- **Configuration Templates**: Check `docker/nginx/templates/` for examples
- **Logs**: Use `docker compose logs [service]` for debugging
- **Health Checks**: Monitor `/.well-known/certificate-status` endpoint
- **Let's Encrypt Documentation**: https://letsencrypt.org/docs/
- **Nginx SSL Configuration**: https://ssl-config.mozilla.org/