# Open Elastic Search MCP Server Documentation

## Overview

> **⚠️ WARNING: This MCP server is EXPERIMENTAL.**

The Open Elastic Search MCP Server template provides a custom implementation that supports both **Elasticsearch** and **OpenSearch** clusters, allowing you to interact with your search data through the Model Context Protocol (MCP). Built on the excellent [elasticsearch-mcp-server](https://github.com/cr7258/elasticsearch-mcp-server) project, this template brings unified search capabilities to your MCP platform.

Our platform extends the base implementation by providing:
- **🚀 One-Command Deployment**: Deploy and manage search MCP servers with a single command
- **🔧 Dual Engine Support**: Works with both Elasticsearch and OpenSearch clusters
- **🛡️ Multiple Authentication Methods**: API key and username/password authentication
- **📊 Comprehensive Monitoring**: Built-in logging, status monitoring, and error tracking
- **🔄 Flexible Transport**: Support for stdio, SSE, and streamable-HTTP transport modes
- **⚙️ Security**: Secure credential handling and SSL configuration
- **📈 Performance Optimization**: Efficient connection management and query optimization

## Supported Engines and Versions

| Engine | Versions | Authentication Methods |
|--------|----------|----------------------|
| **Elasticsearch** | 7.x, 8.x, 9.x | API Key (recommended), Username/Password |
| **OpenSearch** | 1.x, 2.x, 3.x | Username/Password |

## Available Tools

The Open Elastic Search MCP server provides 16 comprehensive tools organized into categories:

### General Operations
- **`general_api_request`**: Perform any HTTP API request not covered by dedicated tools

### Index Management
- **`list_indices`**: List all indices in the cluster
- **`get_index`**: Get detailed information about indices (mappings, settings, aliases)
- **`create_index`**: Create new indices with custom configuration
- **`delete_index`**: Remove indices from the cluster

### Document Operations
- **`search_documents`**: Search for documents using query DSL
- **`index_document`**: Create or update documents
- **`get_document`**: Retrieve specific documents by ID
- **`delete_document`**: Remove documents by ID
- **`delete_by_query`**: Bulk delete documents matching a query

### Cluster Operations
- **`get_cluster_health`**: Monitor cluster health status
- **`get_cluster_stats`**: Get comprehensive cluster statistics

### Alias Operations
- **`list_aliases`**: List all index aliases
- **`get_alias`**: Get alias information for specific indices
- **`put_alias`**: Create or update index aliases
- **`delete_alias`**: Remove index aliases

## Quick Start

### Prerequisites

Before deploying the Open Elastic Search MCP server, ensure you have:

1. **Search Cluster**: A running Elasticsearch or OpenSearch cluster
2. **Authentication Credentials**: Appropriate credentials for your chosen engine
3. **Network Access**: Connectivity between the MCP server and your search cluster

### Installation

Deploy the Open Elastic Search MCP server using our platform:

```bash
# Deploy with API key authentication
mcpp deploy elasticsearch --config ES_URL="https://your-elasticsearch-cluster:9200" --config ES_API_KEY="your_api_key"

# Deploy with username/password authentication
mcpp deploy elasticsearch --config ES_URL="https://your-elasticsearch-cluster:9200" --config ES_USERNAME="elastic" --config ES_PASSWORD="your_password"

# Deploy with Elasticsearch using API key
mcpp deploy open-elastic-search \
  --config ENGINE_TYPE="elasticsearch" \
  --config ELASTICSEARCH_HOSTS="https://your-cluster:9200" \
  --config ELASTICSEARCH_API_KEY="your_api_key"

# Deploy with OpenSearch
mcpp deploy open-elastic-search \
  --config ENGINE_TYPE="opensearch" \
  --config OPENSEARCH_HOSTS="https://your-cluster:9200" \
  --config OPENSEARCH_USERNAME="admin" \
  --config OPENSEARCH_PASSWORD="admin"

# Check deployment status
mcpp status open-elastic-search

# View real-time logs
mcpp logs open-elastic-search
```

### Configuration

The template supports flexible configuration for both Elasticsearch and OpenSearch:

#### Elasticsearch Configuration

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `ENGINE_TYPE` | Search engine type | No | elasticsearch |
| `ELASTICSEARCH_HOSTS` | Elasticsearch cluster hosts | Yes | - |
| `ELASTICSEARCH_API_KEY` | API key for authentication | Yes* | - |
| `ELASTICSEARCH_USERNAME` | Username for basic auth | Yes* | - |
| `ELASTICSEARCH_PASSWORD` | Password for basic auth | Yes* | - |
| `ELASTICSEARCH_VERIFY_CERTS` | SSL certificate verification | No | false |

#### OpenSearch Configuration

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `ENGINE_TYPE` | Search engine type | Yes | elasticsearch |
| `OPENSEARCH_HOSTS` | OpenSearch cluster hosts | Yes | - |
| `OPENSEARCH_USERNAME` | Username for authentication | Yes | - |
| `OPENSEARCH_PASSWORD` | Password for authentication | Yes | - |
| `OPENSEARCH_VERIFY_CERTS` | SSL certificate verification | No | false |

#### Transport Configuration

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `MCP_TRANSPORT` | Transport protocol | No | stdio |
| `MCP_HOST` | Host for HTTP-based transports | No | 0.0.0.0 |
| `MCP_PORT` | Port for HTTP-based transports | No | 8000 |
| `MCP_PATH` | Path for HTTP-based transports | No | /mcp |

*For Elasticsearch: Either `ELASTICSEARCH_API_KEY` or both `ELASTICSEARCH_USERNAME` and `ELASTICSEARCH_PASSWORD` are required.

#### Creating an Elasticsearch API Key

API key authentication is recommended for Elasticsearch. To create an API key:

1. **Using Kibana**:
   - Go to Stack Management → API Keys
   - Click "Create API key"
   - Provide appropriate privileges for your use case

2. **Using REST API**:
   ```bash
   curl -X POST "localhost:9200/_security/api_key" \
   -H "Content-Type: application/json" \
   -u elastic:password \
   -d '{
     "name": "mcp-server-key",
     "role_descriptors": {
       "mcp_role": {
         "cluster": ["monitor", "read_slm"],
         "index": [
           {
             "names": ["*"],
             "privileges": ["read", "write", "create", "delete", "view_index_metadata"]
           }
         ]
       }
     }
   }'
   ```

#### SSL Configuration

For production environments:

```bash
# Enable SSL verification (recommended for production)
mcpp deploy open-elastic-search \
  --config ELASTICSEARCH_VERIFY_CERTS="true"

# Skip SSL verification (development only)
mcpp deploy open-elastic-search \
  --config ELASTICSEARCH_VERIFY_CERTS="false"
```

## Tool Discovery

The platform provides static tool discovery with comprehensive documentation:

```bash
# List all available tools
mcpp interactive
mcpp> tools open-elastic-search

# Get detailed tool information
mcpp> tools open-elastic-search --verbose

# Get help for a specific tool
mcpp> help open-elastic-search search_documents
```

## Platform Benefits

### Enhanced Deployment
- **Custom Docker Build**: Built from source for maximum flexibility and control
- **Dual Engine Support**: Unified interface for both Elasticsearch and OpenSearch
- **Environment Management**: Secure handling of credentials for multiple engines
- **Health Monitoring**: Automatic health checks and restart policies
- **Transport Flexibility**: Support for stdio, SSE, and streamable-HTTP transports

### Advanced Security
- **Multi-Engine Authentication**: Support for different authentication methods per engine
- **SSL Support**: Flexible SSL configuration for secure connections
- **Access Control**: Fine-grained authentication and authorization
- **Credential Isolation**: Separate credential handling for different engines

### Developer Experience
- **One-Command Setup**: Deploy search integration in seconds
- **Interactive CLI**: Rich terminal interface with progress indicators
- **Comprehensive Documentation**: Auto-generated tool documentation
- **Error Handling**: Robust error handling with helpful messages
- **Development Support**: Built-in Docker Compose files for local testing

## Development

### Local Development

```bash
# Clone the external repository for local development
git clone https://github.com/cr7258/elasticsearch-mcp-server.git
cd elasticsearch-mcp-server

# Start Elasticsearch cluster
docker-compose -f docker-compose-elasticsearch.yml up -d

# Start OpenSearch cluster (alternative)
docker-compose -f docker-compose-opensearch.yml up -d

# Deploy against local cluster
mcpp deploy open-elastic-search \
  --config ENGINE_TYPE="elasticsearch" \
  --config ELASTICSEARCH_HOSTS="https://localhost:9200" \
  --config ELASTICSEARCH_USERNAME="elastic" \
  --config ELASTICSEARCH_PASSWORD="test123" \
  --config ELASTICSEARCH_VERIFY_CERTS="false"
```

### Testing

```bash
# Test with Elasticsearch
mcpp deploy open-elastic-search \
  --config ENGINE_TYPE="elasticsearch" \
  --config ELASTICSEARCH_HOSTS="https://localhost:9200" \
  --config ELASTICSEARCH_API_KEY="test_key"

# Test with OpenSearch
mcpp deploy open-elastic-search \
  --config ENGINE_TYPE="opensearch" \
  --config OPENSEARCH_HOSTS="https://localhost:9200" \
  --config OPENSEARCH_USERNAME="admin" \
  --config OPENSEARCH_PASSWORD="admin"

# Call tools directly
mcpp i
mcpp> call open-elastic-search list_indices
mcpp> call open-elastic-search search_documents '{"index": "test-index", "body": {"query": {"match_all": {}}}}'
mcpp> call open-elastic-search get_cluster_health
```

## Monitoring & Troubleshooting

### Health Checks

```bash
# Check service status
mcpp status open-elastic-search

# Get detailed health information
mcpp status open-elastic-search --detailed

# View real-time logs
mcpp logs open-elastic-search --follow
```

### Common Issues

1. **Connection Errors**
   - Verify hosts URL is correct and accessible
   - Check network connectivity to your search cluster
   - Ensure cluster is running and healthy

2. **Authentication Failures**
   - For Elasticsearch: Verify API key or username/password
   - For OpenSearch: Verify username/password credentials
   - Check user privileges and permissions

3. **SSL/TLS Issues**
   - For self-signed certificates, set `*_VERIFY_CERTS=false` (development only)
   - For production, ensure proper certificate chain
   - Check certificate validity and hostname matching

4. **Engine Type Issues**
   - Ensure `ENGINE_TYPE` matches your cluster type
   - Verify you're using the correct environment variables for your engine
   - Check that authentication method is supported by your engine

### Debug Mode

Enable comprehensive debugging:

```bash
# Deploy with debug mode
mcpp deploy open-elastic-search \
  --config ENGINE_TYPE="elasticsearch" \
  --config ELASTICSEARCH_HOSTS="https://localhost:9200" \
  --config ELASTICSEARCH_API_KEY="test_key" \
  --debug

# View debug logs
mcpp logs open-elastic-search --level debug

# Test connectivity
mcpp i
mcpp> call open-elastic-search list_indices --verbose
```

## Security Best Practices

### Authentication
- **Use API Keys**: Prefer API key authentication for Elasticsearch when possible
- **Principle of Least Privilege**: Grant only necessary permissions
- **Regular Rotation**: Rotate credentials regularly
- **Secure Storage**: Never expose credentials in logs or configuration files

### Network Security
- **Use HTTPS**: Always use encrypted connections to your clusters
- **Network Isolation**: Deploy in secure network environments
- **Firewall Rules**: Restrict access to cluster ports
- **VPN/Tunnel**: Use VPN or SSH tunneling for remote access

### Monitoring
- **Audit Logging**: Enable cluster audit logging
- **Query Monitoring**: Monitor query patterns and performance
- **Access Logging**: Track MCP server access and usage
- **Alert Setup**: Configure alerts for security events

## Performance Optimization

### Connection Management
- **Connection Pooling**: Efficient HTTP connection reuse
- **Timeout Configuration**: Proper request timeout settings
- **Retry Logic**: Automatic retry for transient failures

### Query Optimization
- **Index Selection**: Use specific indices instead of wildcards
- **Query Efficiency**: Optimize search queries for performance
- **Result Limiting**: Use appropriate size limits for large result sets
- **Pagination**: Implement proper pagination for large datasets

## API Reference

All 16 search tools are available through the MCP interface. Each tool includes:
- **Input Schema**: Detailed parameter specifications
- **Output Schema**: Response format documentation
- **Error Handling**: Comprehensive error response patterns
- **Examples**: Real-world usage examples

### Tool Categories

1. **General Operations** (1 tool): `general_api_request`
2. **Index Operations** (4 tools): `list_indices`, `get_index`, `create_index`, `delete_index`
3. **Document Operations** (5 tools): `search_documents`, `index_document`, `get_document`, `delete_document`, `delete_by_query`
4. **Cluster Operations** (2 tools): `get_cluster_health`, `get_cluster_stats`
5. **Alias Operations** (4 tools): `list_aliases`, `get_alias`, `put_alias`, `delete_alias`

For detailed API documentation of each tool, use:
```bash
mcpp> tools open-elastic-search --tool-name <tool_name> --detailed
```

## Experimental Notice

**⚠️ This MCP server is EXPERIMENTAL** and supports both Elasticsearch and OpenSearch. While it provides comprehensive functionality for interacting with search clusters, please be aware that:

- API interfaces may change in future versions
- Some features may not be fully stable across all engine versions
- Thorough testing is recommended before production use
- Performance characteristics may vary between engines

## Contributing

We welcome contributions to improve the Open Elastic Search MCP server template:

1. **Bug Reports**: Submit issues with detailed reproduction steps
2. **Feature Requests**: Propose new search integrations
3. **Pull Requests**: Contribute code improvements
4. **Documentation**: Help improve this documentation

See the main repository's contributing guidelines for detailed information.

## License

This template is based on the [elasticsearch-mcp-server](https://github.com/cr7258/elasticsearch-mcp-server) project and is part of the MCP Server Templates project. See LICENSE for details.

## Support

For support, please:
1. Check the upstream [elasticsearch-mcp-server](https://github.com/cr7258/elasticsearch-mcp-server) repository
2. Open an issue in the main MCP Platform repository
3. Contact the maintainers

For issues specific to the underlying implementation, please refer to the upstream repository.
