# Trino MCP Server

A production-ready Trino MCP server template for secure querying of distributed data sources with configurable access controls and multiple authentication methods.

## Overview

This template provides a secure interface to Trino (formerly Presto SQL) clusters, enabling SQL queries across multiple data sources including Hive, Iceberg, PostgreSQL, MySQL, and many others. The server supports multiple authentication methods and provides fine-grained access controls for enterprise environments.

**⚠️ Security Notice**: This template operates in read-only mode by default. Enable write operations with caution and ensure proper access controls are in place.

## Features

- **Multi-Source Queries**: Query across different data sources in a single SQL statement
- **Authentication Support**: JWT, OAuth2, and basic authentication methods
- **Access Controls**: Configurable catalog and schema filtering with regex support
- **Read-Only Mode**: Safe mode by default, prevents accidental data modifications
- **Enterprise Ready**: Production-grade configuration with proper error handling
- **Docker Integration**: Uses upstream `ghcr.io/tuannvm/mcp-trino:latest` image

## Quick Start

### Basic Setup

```bash
# Deploy with basic authentication
python -m mcp_platform deploy trino \
  --config trino_host=your-trino-server.com \
  --config trino_user=analyst
```

### JWT Authentication

```bash
# Deploy with JWT authentication
python -m mcp_platform deploy trino \
  --config trino_host=your-trino-server.com \
  --config trino_user=analyst \
  --config auth_method=jwt \
  --config jwt_token=your-jwt-token
```

### OAuth2 Authentication

```bash
# Deploy with OAuth2 authentication
python -m mcp_platform deploy trino \
  --config trino_host=your-trino-server.com \
  --config trino_user=analyst \
  --config auth_method=oauth2 \
  --config oauth2_client_id=your-client-id \
  --config oauth2_client_secret=your-client-secret \
  --config oauth2_token_url=https://auth.company.com/token
```

## Configuration

### Required Parameters

| Parameter | Description | Default |
|-----------|-------------|---------|
| `trino_host` | Trino server hostname or IP address | `localhost` |
| `trino_user` | Username for Trino authentication | `admin` |

### Authentication Parameters

| Parameter | Description | Environment Variable |
|-----------|-------------|---------------------|
| `auth_method` | Authentication method (`basic`, `jwt`, `oauth2`) | `TRINO_AUTH_METHOD` |
| `jwt_token` | JWT token (required for JWT auth) | `TRINO_JWT_TOKEN` |
| `oauth2_client_id` | OAuth2 client ID | `TRINO_OAUTH2_CLIENT_ID` |
| `oauth2_client_secret` | OAuth2 client secret | `TRINO_OAUTH2_CLIENT_SECRET` |
| `oauth2_token_url` | OAuth2 token endpoint URL | `TRINO_OAUTH2_TOKEN_URL` |

### Access Control Parameters

| Parameter | Description | Default | Environment Variable |
|-----------|-------------|---------|---------------------|
| `read_only` | Enable read-only mode | `true` | `TRINO_READ_ONLY` |
| `allowed_catalogs` | Comma-separated catalog patterns | `*` | `TRINO_ALLOWED_CATALOGS` |
| `catalog_regex` | Advanced catalog filtering regex | - | `TRINO_CATALOG_REGEX` |
| `allowed_schemas` | Comma-separated schema patterns | `*` | `TRINO_ALLOWED_SCHEMAS` |
| `schema_regex` | Advanced schema filtering regex | - | `TRINO_SCHEMA_REGEX` |

### Performance Parameters

| Parameter | Description | Default | Environment Variable |
|-----------|-------------|---------|---------------------|
| `query_timeout` | Query timeout in seconds | `300` | `TRINO_QUERY_TIMEOUT` |
| `max_results` | Maximum rows to return | `1000` | `TRINO_MAX_RESULTS` |
| `trino_port` | Trino server port | `8080` | `TRINO_PORT` |

## Authentication Methods

### Basic Authentication
Simple username-based authentication (no password required):
```bash
export TRINO_HOST=your-trino-server.com
export TRINO_USER=analyst
export TRINO_AUTH_METHOD=basic
```

### JWT Authentication
Token-based authentication for secure environments:
```bash
export TRINO_HOST=your-trino-server.com
export TRINO_USER=analyst
export TRINO_AUTH_METHOD=jwt
export TRINO_JWT_TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Note**: For JWT authentication setup and token generation, refer to the [upstream JWT documentation](https://docs.tuannvm.com/mcp-trino/docs/jwt).

### OAuth2 Authentication
Enterprise OAuth2 integration:
```bash
export TRINO_HOST=your-trino-server.com
export TRINO_USER=analyst
export TRINO_AUTH_METHOD=oauth2
export TRINO_OAUTH2_CLIENT_ID=your-client-id
export TRINO_OAUTH2_CLIENT_SECRET=your-client-secret
export TRINO_OAUTH2_TOKEN_URL=https://auth.company.com/oauth/token
```

**Note**: For detailed OAuth2 setup instructions, refer to the [upstream OAuth2 documentation](https://docs.tuannvm.com/mcp-trino/docs/oauth).

## Access Control Examples

### Catalog Filtering
```bash
# Allow only specific catalogs
python -m mcp_platform deploy trino \
  --config allowed_catalogs="hive,iceberg,postgresql"

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