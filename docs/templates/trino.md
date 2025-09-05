# Trino Database Template

## Overview

The Trino MCP Server template provides comprehensive access to distributed SQL query execution across multiple data sources. Built on the upstream [mcp-trino](https://github.com/tuannvm/mcp-trino) implementation, it enables secure querying of Trino (formerly Presto) clusters with configurable access controls and multiple authentication methods.

## Features

- **Multi-Source Queries**: Execute SQL across Hive, Iceberg, PostgreSQL, MySQL, and 300+ other connectors
- **Multiple Authentication**: Support for basic, JWT, and OAuth2 authentication methods
- **Access Controls**: Fine-grained catalog and schema filtering with regex support
- **Read-Only Safety**: Operates in read-only mode by default to prevent accidental data modifications
- **Enterprise Ready**: Production-grade configuration with proper error handling and monitoring

## Quick Start

### Basic Authentication Setup

```bash
python -m mcp_platform deploy trino \
  --config trino_host=your-trino-server.com \
  --config trino_user=analyst
```

### JWT Authentication Setup

```bash
python -m mcp_platform deploy trino \
  --config trino_host=your-trino-server.com \
  --config trino_user=analyst \
  --config auth_method=jwt \
  --config jwt_token=your-jwt-token
```

For detailed JWT setup instructions, refer to the [upstream JWT documentation](https://docs.tuannvm.com/mcp-trino/docs/jwt).

### OAuth2 Authentication Setup

```bash
python -m mcp_platform deploy trino \
  --config trino_host=your-trino-server.com \
  --config trino_user=analyst \
  --config auth_method=oauth2 \
  --config oauth2_client_id=your-client-id \
  --config oauth2_client_secret=your-client-secret \
  --config oauth2_token_url=https://auth.company.com/token
```

For detailed OAuth2 setup instructions, refer to the [upstream OAuth2 documentation](https://docs.tuannvm.com/mcp-trino/docs/oauth).

## Configuration Reference

### Required Parameters

| Parameter | Description | Environment Variable |
|-----------|-------------|---------------------|
| `trino_host` | Trino server hostname | `TRINO_HOST` |
| `trino_user` | Username for authentication | `TRINO_USER` |

### Authentication Configuration

| Parameter | Description | Default | Environment Variable |
|-----------|-------------|---------|---------------------|
| `auth_method` | Authentication method | `basic` | `TRINO_AUTH_METHOD` |
| `jwt_token` | JWT token (for JWT auth) | - | `TRINO_JWT_TOKEN` |
| `oauth2_client_id` | OAuth2 client ID | - | `TRINO_OAUTH2_CLIENT_ID` |
| `oauth2_client_secret` | OAuth2 client secret | - | `TRINO_OAUTH2_CLIENT_SECRET` |
| `oauth2_token_url` | OAuth2 token endpoint | - | `TRINO_OAUTH2_TOKEN_URL` |

### Access Control Configuration

| Parameter | Description | Default | Environment Variable |
|-----------|-------------|---------|---------------------|
| `read_only` | Enable read-only mode | `true` | `TRINO_READ_ONLY` |
| `allowed_catalogs` | Catalog patterns (comma-separated) | `*` | `TRINO_ALLOWED_CATALOGS` |
| `catalog_regex` | Advanced catalog filtering regex | - | `TRINO_CATALOG_REGEX` |
| `allowed_schemas` | Schema patterns (comma-separated) | `*` | `TRINO_ALLOWED_SCHEMAS` |
| `schema_regex` | Advanced schema filtering regex | - | `TRINO_SCHEMA_REGEX` |

### Performance Configuration

| Parameter | Description | Default | Environment Variable |
|-----------|-------------|---------|---------------------|
| `query_timeout` | Query timeout (seconds) | `300` | `TRINO_QUERY_TIMEOUT` |
| `max_results` | Maximum rows to return | `1000` | `TRINO_MAX_RESULTS` |
| `trino_port` | Trino server port | `8080` | `TRINO_PORT` |

## Available Tools

### Discovery Tools
- **list_catalogs**: List all accessible Trino catalogs
- **list_schemas**: List schemas in a specific catalog
- **list_tables**: List tables in a specific schema
- **get_cluster_info**: Get Trino cluster information

### Data Access Tools
- **describe_table**: Get detailed table schema information
- **execute_query**: Execute SQL queries (subject to access controls)

### Query Management Tools
- **get_query_status**: Check status of running queries
- **cancel_query**: Cancel running queries

## Access Control Examples

### Catalog Filtering

```bash
# Allow only specific catalogs
--config allowed_catalogs="hive,iceberg,postgresql"

# Use patterns for catalog names
--config allowed_catalogs="prod_*,staging_*"

# Advanced regex filtering
--config catalog_regex="^(production|staging)_.+"
```

### Schema Filtering

```bash
# Allow specific schemas with patterns
--config allowed_schemas="public,analytics_*,reporting_*"

# Combine catalog and schema filtering
--config allowed_catalogs="hive,iceberg" --config allowed_schemas="public,prod_*"
```

### Enable Write Operations (Use with Caution)

```bash
# ⚠️ Enable write operations - ensure proper access controls!
--config read_only=false \
--config allowed_catalogs="development" \
--config allowed_schemas="sandbox_*"
```

## Example Queries

### Cross-Catalog Analytics

```sql
-- Join data from different sources
SELECT h.customer_id, h.order_date, p.product_name
FROM hive.sales.orders h
JOIN postgresql.inventory.products p ON h.product_id = p.id
WHERE h.order_date >= DATE '2024-01-01'
```

### Multi-Source Aggregation

```sql
-- Analyze data across multiple catalogs
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

## Security Best Practices

1. **Read-Only Default**: Keep `read_only=true` unless write access is specifically required
2. **Limit Access**: Use `allowed_catalogs` and `allowed_schemas` to restrict data access
3. **Secure Authentication**: Prefer JWT or OAuth2 over basic authentication in production
4. **Network Security**: Ensure Trino server is only accessible from authorized networks
5. **Audit Logging**: Enable query logging on the Trino server for audit trails

## Common Use Cases

### Data Engineering
- ETL pipeline development and testing
- Data quality analysis across sources
- Schema evolution tracking

### Analytics
- Cross-platform reporting and dashboards
- Ad-hoc data exploration
- Performance analysis and optimization

### Data Science
- Feature engineering across multiple sources
- Model training data preparation
- Exploratory data analysis

## Troubleshooting

### Connection Issues
- Verify `trino_host` and `trino_port` are correct
- Check network connectivity to Trino server
- Ensure authentication credentials are valid

### Authentication Errors
- **JWT**: Verify token is valid and not expired
- **OAuth2**: Check client credentials and token URL
- **Basic**: Ensure username is correct

### Access Denied
- Check `allowed_catalogs` and `allowed_schemas` filters
- Verify user has necessary permissions in Trino
- Review regex patterns for syntax errors

### Query Timeouts
- Increase `query_timeout` for long-running queries
- Consider optimizing query performance
- Check Trino cluster resource availability

## References

- [Upstream MCP Trino Implementation](https://github.com/tuannvm/mcp-trino)
- [General Usage Guide](https://docs.tuannvm.com/mcp-trino/solution)
- [JWT Authentication Setup](https://docs.tuannvm.com/mcp-trino/docs/jwt)
- [OAuth2 Authentication Setup](https://docs.tuannvm.com/mcp-trino/docs/oauth)
- [Trino Documentation](https://trino.io/docs/)

## License

This template extends the upstream [mcp-trino](https://github.com/tuannvm/mcp-trino) implementation. Please refer to the upstream project for licensing information.