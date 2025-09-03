# Trino MCP Server

A production-ready Trino MCP server template for secure querying of distributed data sources with configurable access controls and multiple authentication methods. Built with FastMCP and SQLAlchemy for robust performance and reliability.

## Overview

This template provides a secure interface to Trino (formerly Presto SQL) clusters, enabling SQL queries across multiple data sources including Hive, Iceberg, PostgreSQL, MySQL, and many others. The server is implemented in Python using FastMCP and SQLAlchemy, providing excellent performance and compatibility with the broader Python ecosystem.

**⚠️ Security Notice**: This template operates in read-only mode by default with a 1000-row limit. Enable write operations with caution and ensure proper access controls are in place.

## Features

- **Python FastMCP Implementation**: Built with FastMCP for high performance and reliability
- **SQLAlchemy Integration**: Uses SQLAlchemy with Trino dialect for robust database connectivity
- **Multi-Source Queries**: Query across different data sources in a single SQL statement
- **Authentication Support**: Username/password, OAuth 2.1, and JWT authentication methods
- **Read-Only by Default**: Safe mode with configurable override and warning system
- **Query Limits**: Configurable row limits (1000 by default) for performance and safety
- **HTTP and stdio Transport**: Supports both HTTP (default) and stdio transports
- **Access Controls**: Comprehensive security with timeout controls
- **Enterprise Ready**: Production-grade configuration with proper error handling
- **Docker Ready**: Containerized deployment with `dataeverything/mcp-trino` image

## Quick Start

### Basic Setup

```bash
# Deploy with basic authentication
python -m mcp_platform deploy trino \
  --config trino_host=your-trino-server.com \
  --config trino_user=analyst
```

### With Password Authentication

```bash
# Deploy with username/password authentication
python -m mcp_platform deploy trino \
  --config trino_host=your-trino-server.com \
  --config trino_user=analyst \
  --config trino_password=your-password \
  --config trino_catalog=hive
```

### OAuth2 Authentication

```bash
# Deploy with Google OAuth2
python -m mcp_platform deploy trino \
  --config trino_host=your-trino-server.com \
  --config trino_user=analyst \
  --config oauth_enabled=true \
  --config oauth_provider=google \
  --config oidc_issuer=https://accounts.google.com \
  --config oidc_client_id=your-client-id
```

### Enable Write Mode (Use with Caution)

```bash
# Deploy with write operations enabled
python -m mcp_platform deploy trino \
  --config trino_host=your-trino-server.com \
  --config trino_user=analyst \
  --config trino_allow_write_queries=true \
  --config trino_max_results=5000
```
  --config oauth2_client_secret=your-client-secret \
  --config oauth2_token_url=https://auth.company.com/token
```

## Configuration

### Required Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `trino_host` | Trino server hostname or IP address | `localhost` |
## Configuration

### Connection Parameters

| Parameter | Description | Default | Environment Variable |
|-----------|-------------|---------|---------------------|
| `trino_host` | Trino server hostname | - | `TRINO_HOST` |
| `trino_port` | Trino server port | `8080` | `TRINO_PORT` |
| `trino_user` | Username for Trino authentication | - | `TRINO_USER` |
| `trino_password` | Password for basic authentication | - | `TRINO_PASSWORD` |
| `trino_catalog` | Default catalog for queries | - | `TRINO_CATALOG` |
| `trino_schema` | Default schema for queries | - | `TRINO_SCHEMA` |
| `trino_scheme` | Connection scheme (`http` or `https`) | `https` | `TRINO_SCHEME` |
| `trino_ssl` | Enable SSL/TLS | `true` | `TRINO_SSL` |
| `trino_ssl_insecure` | Allow insecure SSL connections | `true` | `TRINO_SSL_INSECURE` |

### Authentication Parameters

| Parameter | Description | Environment Variable |
|-----------|-------------|---------------------|
| `oauth_enabled` | Enable OAuth 2.1 authentication | `TRINO_OAUTH_ENABLED` |
| `oauth_provider` | OAuth provider (`hmac`, `okta`, `google`, `azure`) | `TRINO_OAUTH_PROVIDER` |
| `jwt_secret` | JWT signing secret for HMAC provider | `TRINO_JWT_SECRET` |
| `oidc_issuer` | OIDC issuer URL | `TRINO_OIDC_ISSUER` |
| `oidc_audience` | OIDC audience | `TRINO_OIDC_AUDIENCE` |
| `oidc_client_id` | OIDC client ID | `TRINO_OIDC_CLIENT_ID` |
| `oidc_client_secret` | OIDC client secret | `TRINO_OIDC_CLIENT_SECRET` |
| `oauth_redirect_uri` | Fixed OAuth redirect URI | `TRINO_OAUTH_REDIRECT_URI` |

### Security Parameters

| Parameter | Description | Default | Environment Variable |
|-----------|-------------|---------|---------------------|
| `trino_allow_write_queries` | Allow write operations (⚠️ WARNING: Use with caution) | `false` | `TRINO_ALLOW_WRITE_QUERIES` |
| `trino_query_timeout` | Query timeout (seconds or duration format) | `300` | `TRINO_QUERY_TIMEOUT` |
| `trino_max_results` | Maximum rows to return per query | `1000` | `TRINO_MAX_RESULTS` |
| `log_level` | Logging level (`debug`, `info`, `warning`, `error`) | `info` | `MCP_LOG_LEVEL` |

## Authentication Methods

### Basic Authentication (Username/Password)
Simple username and password authentication:
```bash
export TRINO_HOST=your-trino-server.com
export TRINO_USER=analyst
export TRINO_PASSWORD=your-password
```

### OAuth 2.1 with Google
Google OAuth2 integration:
```bash
export TRINO_HOST=your-trino-server.com
export TRINO_USER=analyst
export TRINO_OAUTH_ENABLED=true
export TRINO_OAUTH_PROVIDER=google
export TRINO_OIDC_ISSUER=https://accounts.google.com
export TRINO_OIDC_CLIENT_ID=your-client-id
export TRINO_OIDC_CLIENT_SECRET=your-client-secret
```

### OAuth 2.1 with Okta
Okta OAuth2 integration:
```bash
export TRINO_HOST=your-trino-server.com
export TRINO_USER=analyst
export TRINO_OAUTH_ENABLED=true
export TRINO_OAUTH_PROVIDER=okta
export TRINO_OIDC_ISSUER=https://company.okta.com
export TRINO_OIDC_CLIENT_ID=your-client-id
export TRINO_OIDC_CLIENT_SECRET=your-client-secret
```

### JWT with HMAC Provider
JWT authentication with HMAC signing:
```bash
export TRINO_HOST=your-trino-server.com
export TRINO_USER=analyst
export TRINO_OAUTH_ENABLED=true
export TRINO_OAUTH_PROVIDER=hmac
export TRINO_JWT_SECRET=your-jwt-signing-secret
```

## Security and Access Control

### Read-Only Mode (Default)
The server operates in read-only mode by default for safety:
```bash
# Read-only mode (default)
python -m mcp_platform deploy trino \
  --config trino_host=localhost \
  --config trino_user=analyst
```

### Enable Write Mode (⚠️ Use with Caution)
```bash
# Enable write operations with warning
python -m mcp_platform deploy trino \
  --config trino_host=localhost \
  --config trino_user=analyst \
  --config trino_allow_write_queries=true
```

### Query Limits and Timeouts
```bash
# Configure query limits
python -m mcp_platform deploy trino \
  --config trino_host=localhost \
  --config trino_user=analyst \
  --config trino_max_results=5000 \
  --config trino_query_timeout=600
```

# Use regex for advanced filtering
python -m mcp_platform deploy trino \
  --config catalog_regex="^(production|staging)_.*"
```

### Schema Filtering
```bash
# Allow specific schemas with patterns
python -m mcp_platform deploy trino \
  --config allowed_schemas="public,analytics_*,reporting_*"

# Combine catalog and schema filtering
python -m mcp_platform deploy trino \
  --config allowed_catalogs="hive,iceberg" \
  --config allowed_schemas="public,prod_*"
```

### Enable Write Operations (Use with Caution)
```bash
# ⚠️ Enable write operations - ensure proper access controls!
python -m mcp_platform deploy trino \
  --config read_only=false \
  --config allowed_catalogs="development" \
  --config allowed_schemas="sandbox_*"
```

## Available Tools

### Catalog and Schema Discovery
- `list_catalogs` - List all accessible Trino catalogs
- `list_schemas` - List schemas in a specific catalog
- `list_tables` - List tables in a specific schema
- `get_cluster_info` - Get Trino cluster information

### Table Operations
- `describe_table` - Get detailed table schema information
- `execute_query` - Execute SQL queries (subject to access controls)

### Query Management
- `get_query_status` - Check status of running queries
- `cancel_query` - Cancel running queries

## Example Queries

### Cross-Catalog Joins
```sql
-- Join data from different catalogs
SELECT h.customer_id, h.order_date, p.product_name
FROM hive.sales.orders h
JOIN postgresql.inventory.products p ON h.product_id = p.id
WHERE h.order_date >= DATE '2024-01-01'
```

### Analytics Across Sources
```sql
-- Analyze data across multiple sources
SELECT 
    catalog_name,
    COUNT(*) as table_count,
    SUM(row_count) as total_rows
FROM iceberg.analytics.table_stats
GROUP BY catalog_name
ORDER BY total_rows DESC
```

## Claude Desktop Integration

Add this configuration to your Claude Desktop `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "trino": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-e", "TRINO_HOST",
        "-e", "TRINO_USER", 
        "-e", "TRINO_AUTH_METHOD",
        "-e", "TRINO_JWT_TOKEN",
        "ghcr.io/tuannvm/mcp-trino:latest"
      ],
      "env": {
        "TRINO_HOST": "your-trino-server.com",
        "TRINO_USER": "analyst",
        "TRINO_AUTH_METHOD": "basic",
        "TRINO_READ_ONLY": "true"
      }
    }
  }
}
```

## Development

### Running Locally
```bash
# Using Docker directly
docker run -i --rm \
  -e TRINO_HOST=localhost \
  -e TRINO_USER=admin \
  -e TRINO_READ_ONLY=true \
  ghcr.io/tuannvm/mcp-trino:latest
```

### Environment Variables Reference

All environment variables from the upstream [mcp-trino](https://github.com/tuannvm/mcp-trino) implementation are supported. The template automatically maps configuration parameters to the appropriate environment variables.

## Security Best Practices

1. **Use Read-Only Mode**: Keep `read_only=true` unless write access is specifically required
2. **Limit Access**: Use `allowed_catalogs` and `allowed_schemas` to restrict data access
3. **Secure Authentication**: Prefer JWT or OAuth2 over basic authentication in production
4. **Network Security**: Ensure Trino server is only accessible from authorized networks
5. **Audit Logging**: Enable query logging on the Trino server for audit trails

## Troubleshooting

### Connection Issues
- Verify `trino_host` and `trino_port` are correct
- Check network connectivity to Trino server
- Ensure authentication credentials are valid

### Authentication Errors
- For JWT: Verify token is valid and not expired
- For OAuth2: Check client credentials and token URL
- For basic: Ensure username is correct

### Access Denied
- Check `allowed_catalogs` and `allowed_schemas` filters
- Verify user has necessary permissions in Trino
- Review regex patterns for syntax errors

### Query Timeouts
- Increase `query_timeout` for long-running queries
- Consider optimizing query performance
- Check Trino cluster resource availability

## References

- [Upstream Trino MCP Documentation](https://docs.tuannvm.com/mcp-trino/solution)
- [JWT Authentication Setup](https://docs.tuannvm.com/mcp-trino/docs/jwt)
- [OAuth2 Authentication Setup](https://docs.tuannvm.com/mcp-trino/docs/oauth)
- [Trino Documentation](https://trino.io/docs/)

## License

This template extends the upstream [mcp-trino](https://github.com/tuannvm/mcp-trino) implementation. Please refer to the upstream project for licensing information.