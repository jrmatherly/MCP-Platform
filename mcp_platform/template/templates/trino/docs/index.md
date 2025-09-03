# Trino MCP Server - Complete Tool Reference

## Overview

The Trino MCP Server provides comprehensive access to distributed SQL query execution across multiple data sources. This reference covers all available tools, configuration options, and integration patterns.

## Tool Catalog

### Catalog & Schema Discovery

#### list_catalogs
Lists all accessible Trino catalogs based on configured access controls.

**Parameters**: None  
**Returns**: Array of catalog names  
**Access Control**: Filtered by `allowed_catalogs` and `catalog_regex`

```python
result = await session.call_tool("list_catalogs", {})
# Returns: ["hive", "iceberg", "postgresql", "mysql"]
```

#### list_schemas
Lists all schemas within a specific catalog.

**Parameters**:
- `catalog` (string, required): Target catalog name

**Returns**: Array of schema names  
**Access Control**: Filtered by `allowed_schemas` and `schema_regex`

```python
result = await session.call_tool("list_schemas", {"catalog": "hive"})
# Returns: ["default", "sales", "analytics", "staging"]
```

#### list_tables
Lists all tables within a specific schema.

**Parameters**:
- `catalog` (string, required): Target catalog name
- `schema` (string, required): Target schema name

**Returns**: Array of table names  
**Access Control**: Subject to catalog/schema filtering

```python
result = await session.call_tool("list_tables", {
    "catalog": "hive",
    "schema": "sales"
})
# Returns: ["orders", "customers", "products", "order_items"]
```

### Table Operations

#### describe_table
Provides detailed schema information for a specific table including column names, types, and constraints.

**Parameters**:
- `catalog` (string, required): Target catalog name
- `schema` (string, required): Target schema name  
- `table` (string, required): Target table name

**Returns**: Detailed table schema object with columns, types, and metadata

```python
result = await session.call_tool("describe_table", {
    "catalog": "hive",
    "schema": "sales", 
    "table": "orders"
})
# Returns: {
#   "columns": [
#     {"name": "order_id", "type": "bigint", "nullable": false},
#     {"name": "customer_id", "type": "bigint", "nullable": false},
#     {"name": "order_date", "type": "date", "nullable": false},
#     {"name": "total_amount", "type": "decimal(10,2)", "nullable": true}
#   ],
#   "partitions": ["order_date"],
#   "table_type": "EXTERNAL_TABLE"
# }
```

### Query Execution

#### execute_query
Executes SQL queries against Trino with comprehensive access control and safety features.

**Parameters**:
- `query` (string, required): SQL query to execute
- `catalog` (string, optional): Default catalog context
- `schema` (string, optional): Default schema context

**Returns**: Query results with metadata  
**Access Control**: Subject to read-only mode and catalog/schema filtering

```python
# Simple aggregation query
result = await session.call_tool("execute_query", {
    "query": "SELECT COUNT(*) as order_count FROM hive.sales.orders WHERE order_date >= DATE '2024-01-01'"
})

# Cross-catalog join
result = await session.call_tool("execute_query", {
    "query": """
        SELECT o.order_id, c.customer_name, p.product_name
        FROM hive.sales.orders o
        JOIN postgresql.crm.customers c ON o.customer_id = c.id  
        JOIN iceberg.inventory.products p ON o.product_id = p.id
        WHERE o.order_date >= DATE '2024-01-01'
        LIMIT 100
    """
})

# With catalog/schema context
result = await session.call_tool("execute_query", {
    "query": "SELECT * FROM orders WHERE order_date = CURRENT_DATE",
    "catalog": "hive",
    "schema": "sales"
})
```

### Query Management

#### get_query_status
Retrieves the current status and progress information for a running or completed query.

**Parameters**:
- `query_id` (string, required): Trino query identifier

**Returns**: Query status object with execution details

```python
result = await session.call_tool("get_query_status", {
    "query_id": "20240101_123456_00001_abcde"
})
# Returns: {
#   "query_id": "20240101_123456_00001_abcde",
#   "state": "RUNNING",
#   "progress": 0.75,
#   "elapsed_time": "45.2s",
#   "rows_processed": 1500000,
#   "data_processed": "2.3GB"
# }
```

#### cancel_query
Cancels a running query operation.

**Parameters**:
- `query_id` (string, required): Trino query identifier to cancel

**Returns**: Cancellation confirmation

```python
result = await session.call_tool("cancel_query", {
    "query_id": "20240101_123456_00001_abcde"
})
# Returns: {"cancelled": true, "query_id": "20240101_123456_00001_abcde"}
```

### Cluster Operations

#### get_cluster_info
Provides comprehensive information about the Trino cluster configuration and status.

**Parameters**: None

**Returns**: Cluster information object with nodes, version, and configuration details

```python
result = await session.call_tool("get_cluster_info", {})
# Returns: {
#   "version": "422",
#   "coordinator": "trino-coordinator:8080",
#   "workers": 5,
#   "active_queries": 12,
#   "queued_queries": 3,
#   "available_catalogs": ["hive", "iceberg", "postgresql"],
#   "memory_usage": "45.2GB / 128GB"
# }
```

## Authentication Configuration

### Basic Authentication
Simplest method using username only - suitable for development environments.

```bash
export TRINO_AUTH_METHOD=basic
export TRINO_USER=analyst
```

### JWT Authentication  
Token-based authentication for secure production environments.

```bash
export TRINO_AUTH_METHOD=jwt
export TRINO_USER=service-account
export TRINO_JWT_TOKEN=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**JWT Token Requirements**:
- Valid RS256 or HS256 signature
- Must include `sub` claim for user identification
- Should include `exp` claim for expiration
- Optional `groups` claim for role-based access

### OAuth2 Authentication
Enterprise-grade authentication with client credentials flow.

```bash
export TRINO_AUTH_METHOD=oauth2
export TRINO_USER=service-account
export TRINO_OAUTH2_CLIENT_ID=trino-mcp-client
export TRINO_OAUTH2_CLIENT_SECRET=your-client-secret
export TRINO_OAUTH2_TOKEN_URL=https://auth.company.com/oauth/token
```

**OAuth2 Flow**:
1. Client credentials exchanged for access token
2. Access token included in Trino authentication headers
3. Token automatically refreshed when expired

## Access Control Matrix

### Catalog Filtering

| Configuration | Example | Description |
|---------------|---------|-------------|
| `allowed_catalogs` | `"hive,iceberg"` | Exact catalog names |
| `allowed_catalogs` | `"prod_*,staging_*"` | Wildcard patterns |
| `catalog_regex` | `"^(prod\|stg)_.+"` | Advanced regex filtering |

### Schema Filtering

| Configuration | Example | Description |
|---------------|---------|-------------|
| `allowed_schemas` | `"public,analytics"` | Exact schema names |
| `allowed_schemas` | `"public,*_prod"` | Wildcard patterns |
| `schema_regex` | `"^(public\|analytics_.+)"` | Advanced regex filtering |

### Read-Only Mode

When `read_only=true` (default), the following operations are blocked:
- `INSERT`, `UPDATE`, `DELETE` statements
- `CREATE`, `DROP`, `ALTER` DDL operations  
- `CALL` procedure executions
- Any statement that modifies data or schema

**Override Warning**: Setting `read_only=false` enables write operations but should be used with extreme caution and proper access controls.

## Performance Configuration

### Query Timeouts
```bash
export TRINO_QUERY_TIMEOUT=300  # 5 minutes default
export TRINO_QUERY_TIMEOUT=1800 # 30 minutes for ETL workloads
```

### Result Limiting
```bash
export TRINO_MAX_RESULTS=1000   # Default row limit
export TRINO_MAX_RESULTS=10000  # Higher limit for analytics
```

### Connection Settings
```bash
export TRINO_HOST=trino.company.com
export TRINO_PORT=8080  # Default Trino port
export TRINO_PORT=443   # HTTPS/secure deployments
```

## Error Handling

### Common Error Types

#### Authentication Errors
- `AUTHENTICATION_FAILED`: Invalid credentials or expired tokens
- `AUTHORIZATION_DENIED`: User lacks necessary permissions
- `TOKEN_EXPIRED`: JWT token has expired (OAuth2 will auto-refresh)

#### Access Control Errors  
- `CATALOG_ACCESS_DENIED`: Catalog not in allowed list
- `SCHEMA_ACCESS_DENIED`: Schema not in allowed list
- `READ_ONLY_VIOLATION`: Write operation attempted in read-only mode

#### Query Errors
- `QUERY_TIMEOUT`: Query exceeded configured timeout
- `SYNTAX_ERROR`: Invalid SQL syntax
- `TABLE_NOT_FOUND`: Referenced table doesn't exist
- `COLUMN_NOT_FOUND`: Referenced column doesn't exist

#### Connection Errors
- `CONNECTION_FAILED`: Cannot connect to Trino server
- `CLUSTER_UNAVAILABLE`: Trino cluster is down or unreachable

### Error Response Format
```json
{
  "error": {
    "type": "AUTHENTICATION_FAILED",
    "message": "JWT token has expired",
    "details": {
      "token_expired_at": "2024-01-01T12:00:00Z",
      "current_time": "2024-01-01T12:05:00Z"
    }
  }
}
```

## Integration Patterns

### Batch Processing
```python
# Process multiple queries in sequence
queries = [
    "SELECT COUNT(*) FROM hive.sales.orders",
    "SELECT COUNT(*) FROM postgresql.crm.customers", 
    "SELECT COUNT(*) FROM iceberg.inventory.products"
]

results = []
for query in queries:
    result = await session.call_tool("execute_query", {"query": query})
    results.append(result)
```

### Data Discovery Workflow
```python
# Complete data discovery process
async def discover_data_sources():
    # 1. Get available catalogs
    catalogs = await session.call_tool("list_catalogs", {})
    
    discovery_report = {}
    
    for catalog in catalogs:
        # 2. Get schemas in each catalog
        schemas = await session.call_tool("list_schemas", {"catalog": catalog})
        discovery_report[catalog] = {}
        
        for schema in schemas[:5]:  # Limit to first 5 schemas
            # 3. Get tables in each schema
            tables = await session.call_tool("list_tables", {
                "catalog": catalog,
                "schema": schema
            })
            
            discovery_report[catalog][schema] = {}
            
            for table in tables[:3]:  # Limit to first 3 tables
                # 4. Get table structure
                table_info = await session.call_tool("describe_table", {
                    "catalog": catalog,
                    "schema": schema,
                    "table": table
                })
                discovery_report[catalog][schema][table] = table_info
    
    return discovery_report
```

### Real-time Query Monitoring
```python
async def execute_with_monitoring(query):
    # Start query execution
    result = await session.call_tool("execute_query", {"query": query})
    
    # For long-running queries, you would typically:
    # 1. Get the query ID from the result
    # 2. Periodically check status
    # 3. Handle cancellation if needed
    
    return result
```

## Security Best Practices

### Environment Security
1. **Credential Management**: Use secure credential storage, not plain text
2. **Network Security**: Ensure TLS encryption for all connections
3. **Access Logging**: Enable comprehensive query and access logging
4. **Regular Rotation**: Rotate JWT tokens and OAuth2 credentials regularly

### Query Security
1. **Read-Only Default**: Always start with `read_only=true`
2. **Parameterized Queries**: Use proper SQL parameterization when possible
3. **Resource Limits**: Set appropriate timeouts and result limits
4. **Input Validation**: Validate all user inputs before query execution

### Access Control Security
1. **Principle of Least Privilege**: Grant minimum necessary access
2. **Regular Audits**: Review and update access patterns regularly
3. **Catalog Isolation**: Use separate catalogs for different environments
4. **Schema Segregation**: Implement schema-level access controls

## Monitoring and Observability

### Key Metrics to Monitor
- Query execution times and patterns
- Authentication success/failure rates
- Catalog and schema access patterns
- Error rates by type and user
- Resource utilization (CPU, memory, network)

### Logging Configuration
```bash
export MCP_LOG_LEVEL=info      # Standard logging
export MCP_LOG_LEVEL=debug     # Verbose debugging
export MCP_LOG_LEVEL=warning   # Errors and warnings only
```

### Health Checks
```python
# Regular health check pattern
async def health_check():
    try:
        cluster_info = await session.call_tool("get_cluster_info", {})
        return {"status": "healthy", "cluster": cluster_info}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
```

## Advanced Configuration

### Custom Docker Configuration
```dockerfile
FROM ghcr.io/tuannvm/mcp-trino:latest

# Add custom configuration
COPY custom-config.properties /etc/trino/
COPY custom-jvm.config /etc/trino/

# Set environment defaults
ENV TRINO_READ_ONLY=true
ENV TRINO_QUERY_TIMEOUT=600
ENV MCP_LOG_LEVEL=info
```

### Kubernetes Deployment
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: trino-mcp-server
spec:
  replicas: 1
  selector:
    matchLabels:
      app: trino-mcp-server
  template:
    metadata:
      labels:
        app: trino-mcp-server
    spec:
      containers:
      - name: trino-mcp
        image: ghcr.io/tuannvm/mcp-trino:latest
        env:
        - name: TRINO_HOST
          value: "trino.company.com"
        - name: TRINO_USER
          value: "service-account"
        - name: TRINO_AUTH_METHOD
          value: "jwt"
        - name: TRINO_JWT_TOKEN
          valueFrom:
            secretKeyRef:
              name: trino-jwt-secret
              key: token
        - name: TRINO_READ_ONLY
          value: "true"
        resources:
          requests:
            memory: "128Mi"
            cpu: "100m"
          limits:
            memory: "256Mi"
            cpu: "200m"
```

This comprehensive reference provides all the information needed to effectively use and integrate the Trino MCP Server in various environments and use cases.