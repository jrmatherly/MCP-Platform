# Trino MCP Server Usage Guide

## Overview

The Trino MCP Server enables secure access to distributed data sources through Trino SQL queries. This guide provides detailed examples and usage scenarios for different authentication methods and access patterns.

## Available Tools

### list_catalogs

**Description**: List all accessible Trino catalogs

**Example Usage**: Get available data sources

**Parameters**:
- No parameters required

```python
# List all catalogs
result = await session.call_tool("list_catalogs", {})
print("Available catalogs:", result)
```

### list_schemas

**Description**: List schemas in a specific catalog

**Example Usage**: Browse schema structure within a catalog

**Parameters**:
- `catalog`: string - Catalog name to list schemas from

```python
# List schemas in the hive catalog
result = await session.call_tool("list_schemas", {"catalog": "hive"})
print("Hive schemas:", result)
```

### list_tables

**Description**: List tables in a specific schema

**Example Usage**: Browse table structure within a schema

**Parameters**:
- `catalog`: string - Catalog name containing the schema
- `schema`: string - Schema name to list tables from

```python
# List tables in hive.default schema
result = await session.call_tool("list_tables", {
    "catalog": "hive",
    "schema": "default"
})
print("Tables:", result)
```

### describe_table

**Description**: Get detailed schema information for a table

**Example Usage**: Inspect table structure and column definitions

**Parameters**:
- `catalog`: string - Catalog name containing the table
- `schema`: string - Schema name containing the table
- `table`: string - Table name to describe

```python
# Describe a specific table
result = await session.call_tool("describe_table", {
    "catalog": "hive",
    "schema": "sales",
    "table": "orders"
})
print("Table schema:", result)
```

### execute_query

**Description**: Execute a SQL query against Trino (subject to read-only restrictions)

**Example Usage**: Run analytical queries across multiple data sources

**Parameters**:
- `query`: string - SQL query to execute
- `catalog`: string (optional) - Default catalog for the query
- `schema`: string (optional) - Default schema for the query

```python
# Execute a simple query
result = await session.call_tool("execute_query", {
    "query": "SELECT COUNT(*) FROM hive.sales.orders WHERE order_date >= DATE '2024-01-01'"
})
print("Query result:", result)

# Cross-catalog join
result = await session.call_tool("execute_query", {
    "query": """
        SELECT o.order_id, o.customer_id, p.product_name, p.price
        FROM hive.sales.orders o
        JOIN postgresql.inventory.products p ON o.product_id = p.id
        WHERE o.order_date >= DATE '2024-01-01'
        LIMIT 100
    """
})
print("Cross-catalog results:", result)
```

### get_query_status

**Description**: Get status of a running query

**Example Usage**: Monitor long-running query progress

**Parameters**:
- `query_id`: string - Trino query ID to check

```python
# Check query status
result = await session.call_tool("get_query_status", {
    "query_id": "20240101_123456_00001_abcde"
})
print("Query status:", result)
```

### cancel_query

**Description**: Cancel a running query

**Example Usage**: Stop long-running or incorrect queries

**Parameters**:
- `query_id`: string - Trino query ID to cancel

```python
# Cancel a query
result = await session.call_tool("cancel_query", {
    "query_id": "20240101_123456_00001_abcde"
})
print("Cancel result:", result)
```

### get_cluster_info

**Description**: Get information about the Trino cluster

**Example Usage**: Check cluster status and configuration

**Parameters**:
- No parameters required

```python
# Get cluster information
result = await session.call_tool("get_cluster_info", {})
print("Cluster info:", result)
```

## Configuration

### Environment Variables

- `TRINO_HOST`: Trino server hostname (required)
- `TRINO_PORT`: Trino server port (default: 8080)
- `TRINO_USER`: Username for authentication (required)
- `TRINO_AUTH_METHOD`: Authentication method (basic, jwt, oauth2)
- `TRINO_JWT_TOKEN`: JWT token for JWT authentication
- `TRINO_OAUTH2_CLIENT_ID`: OAuth2 client ID
- `TRINO_OAUTH2_CLIENT_SECRET`: OAuth2 client secret
- `TRINO_OAUTH2_TOKEN_URL`: OAuth2 token endpoint URL
- `TRINO_READ_ONLY`: Enable read-only mode (default: true)
- `TRINO_ALLOWED_CATALOGS`: Comma-separated catalog patterns
- `TRINO_CATALOG_REGEX`: Advanced catalog filtering regex
- `TRINO_ALLOWED_SCHEMAS`: Comma-separated schema patterns
- `TRINO_SCHEMA_REGEX`: Advanced schema filtering regex
- `TRINO_QUERY_TIMEOUT`: Query timeout in seconds (default: 300)
- `TRINO_MAX_RESULTS`: Maximum rows to return (default: 1000)
- `MCP_LOG_LEVEL`: Logging level (default: info)

### Configuration File

You can also use a configuration file in JSON format:

```json
{
  "trino_host": "trino.company.com",
  "trino_port": 8080,
  "trino_user": "analyst",
  "auth_method": "jwt",
  "jwt_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "read_only": true,
  "allowed_catalogs": "hive,iceberg,postgresql",
  "query_timeout": 600,
  "max_results": 5000,
  "log_level": "info"
}
```

## Setup Scenarios

### 1. Basic Development Setup

For local development with minimal security:

```bash
export TRINO_HOST=localhost
export TRINO_USER=admin
export TRINO_AUTH_METHOD=basic
export TRINO_READ_ONLY=true
```

### 2. JWT Production Setup

For production environments with JWT authentication:

```bash
export TRINO_HOST=trino.company.com
export TRINO_USER=data-analyst
export TRINO_AUTH_METHOD=jwt
export TRINO_JWT_TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
export TRINO_ALLOWED_CATALOGS=hive,iceberg
export TRINO_ALLOWED_SCHEMAS=public,analytics_*
export TRINO_READ_ONLY=true
```

### 3. OAuth2 Enterprise Setup

For enterprise environments with OAuth2:

```bash
export TRINO_HOST=trino-prod.company.com
export TRINO_USER=service-account
export TRINO_AUTH_METHOD=oauth2
export TRINO_OAUTH2_CLIENT_ID=trino-mcp-client
export TRINO_OAUTH2_CLIENT_SECRET=super-secret-key
export TRINO_OAUTH2_TOKEN_URL=https://auth.company.com/oauth/token
export TRINO_ALLOWED_CATALOGS=production_*
export TRINO_READ_ONLY=true
```

### 4. Data Engineering Setup

For data engineering with limited write access:

```bash
export TRINO_HOST=trino-dev.company.com
export TRINO_USER=data-engineer
export TRINO_AUTH_METHOD=jwt
export TRINO_JWT_TOKEN=your-jwt-token
export TRINO_ALLOWED_CATALOGS=development,staging
export TRINO_ALLOWED_SCHEMAS=workspace_*,sandbox_*
export TRINO_READ_ONLY=false  # ⚠️ Enable with caution
export TRINO_QUERY_TIMEOUT=1800  # 30 minutes for ETL
```

## Common Operations

### Data Exploration

```python
# 1. Discover available data sources
catalogs = await session.call_tool("list_catalogs", {})

# 2. Browse each catalog
for catalog in catalogs:
    schemas = await session.call_tool("list_schemas", {"catalog": catalog})
    print(f"Catalog {catalog}: {schemas}")
    
    # 3. Browse tables in each schema
    for schema in schemas[:3]:  # Limit to first 3 schemas
        tables = await session.call_tool("list_tables", {
            "catalog": catalog,
            "schema": schema
        })
        print(f"Schema {catalog}.{schema}: {tables}")
```

### Schema Analysis

```python
# Analyze table structures
tables_info = []
for table in ["orders", "customers", "products"]:
    schema_info = await session.call_tool("describe_table", {
        "catalog": "hive",
        "schema": "sales",
        "table": table
    })
    tables_info.append(schema_info)
    
print("Tables structure:", tables_info)
```

### Cross-Catalog Analytics

```python
# Analyze data across multiple sources
query = """
SELECT 
    'hive' as source,
    COUNT(*) as record_count,
    MIN(order_date) as min_date,
    MAX(order_date) as max_date
FROM hive.sales.orders
UNION ALL
SELECT 
    'postgresql' as source,
    COUNT(*) as record_count,
    MIN(created_at) as min_date,
    MAX(created_at) as max_date
FROM postgresql.crm.customers
"""

result = await session.call_tool("execute_query", {"query": query})
print("Cross-source analysis:", result)
```

### Performance Monitoring

```python
# Start a long-running query
query_result = await session.call_tool("execute_query", {
    "query": "SELECT COUNT(*) FROM large_table WHERE complex_condition"
})

# If you need to monitor or cancel:
# 1. Get cluster info to see active queries
cluster_info = await session.call_tool("get_cluster_info", {})

# 2. Check specific query status (if you have the query ID)
# status = await session.call_tool("get_query_status", {"query_id": "query_id"})

# 3. Cancel if needed
# cancel = await session.call_tool("cancel_query", {"query_id": "query_id"})
```

## Access Control Examples

### Catalog Filtering

```bash
# Allow only specific catalogs
export TRINO_ALLOWED_CATALOGS="hive,iceberg"

# Use patterns for catalog names
export TRINO_ALLOWED_CATALOGS="prod_*,staging_*"

# Advanced regex filtering
export TRINO_CATALOG_REGEX="^(production|staging)_.+"
```

### Schema Filtering

```bash
# Allow specific schemas
export TRINO_ALLOWED_SCHEMAS="public,analytics,reporting"

# Use patterns for schema names
export TRINO_ALLOWED_SCHEMAS="public,*_prod,analytics_*"

# Combine with catalog filtering
export TRINO_ALLOWED_CATALOGS="hive,iceberg"
export TRINO_ALLOWED_SCHEMAS="public,workspace_*"
```

## Docker Usage

### Basic Docker Run

```bash
docker run -i --rm \
  -e TRINO_HOST=localhost \
  -e TRINO_USER=admin \
  -e TRINO_READ_ONLY=true \
  ghcr.io/tuannvm/mcp-trino:latest
```

### Docker with JWT Authentication

```bash
docker run -i --rm \
  -e TRINO_HOST=trino.company.com \
  -e TRINO_USER=analyst \
  -e TRINO_AUTH_METHOD=jwt \
  -e TRINO_JWT_TOKEN=your-jwt-token \
  -e TRINO_ALLOWED_CATALOGS=hive,iceberg \
  ghcr.io/tuannvm/mcp-trino:latest
```

### Docker Compose Example

```yaml
version: '3.8'
services:
  trino-mcp:
    image: ghcr.io/tuannvm/mcp-trino:latest
    environment:
      TRINO_HOST: trino.company.com
      TRINO_USER: data-analyst
      TRINO_AUTH_METHOD: jwt
      TRINO_JWT_TOKEN: ${JWT_TOKEN}
      TRINO_READ_ONLY: "true"
      TRINO_ALLOWED_CATALOGS: "hive,iceberg,postgresql"
      TRINO_QUERY_TIMEOUT: "600"
    stdin_open: true
    tty: true
```

## Troubleshooting

### Common Issues

1. **Authentication failed**: Check credentials and authentication method
2. **Catalog not found**: Verify catalog name and access permissions
3. **Query timeout**: Increase `TRINO_QUERY_TIMEOUT` or optimize query
4. **Access denied**: Check `TRINO_ALLOWED_CATALOGS` and `TRINO_ALLOWED_SCHEMAS`
5. **Connection refused**: Verify `TRINO_HOST` and `TRINO_PORT`

### Debug Mode

Set `MCP_LOG_LEVEL=debug` environment variable for verbose logging:

```bash
export MCP_LOG_LEVEL=debug
```

### Testing Connectivity

```python
# Test basic connectivity
try:
    cluster_info = await session.call_tool("get_cluster_info", {})
    print("Connection successful:", cluster_info)
except Exception as e:
    print("Connection failed:", e)
```

## Best Practices

1. **Start with read-only**: Always use `TRINO_READ_ONLY=true` initially
2. **Limit access**: Use catalog and schema filtering to restrict data access
3. **Monitor queries**: Use `get_query_status` for long-running operations
4. **Optimize queries**: Consider query performance and cluster resources
5. **Use appropriate timeouts**: Set realistic `TRINO_QUERY_TIMEOUT` values
6. **Secure credentials**: Use environment variables or secure secret management

## Integration Examples

### Claude Desktop

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
        "TRINO_HOST": "trino.company.com",
        "TRINO_USER": "analyst",
        "TRINO_AUTH_METHOD": "jwt",
        "TRINO_JWT_TOKEN": "your-jwt-token",
        "TRINO_READ_ONLY": "true"
      }
    }
  }
}
```

### Python Client

```python
import asyncio
from fastmcp import FastMCP

async def main():
    # Note: Trino MCP uses stdio transport, not HTTP
    # Integration via subprocess or container execution
    pass

if __name__ == "__main__":
    asyncio.run(main())
```