# Open Elastic Search MCP Server Template

This template provides a custom MCP (Model Context Protocol) server implementation that supports both **Elasticsearch** and **OpenSearch** clusters. Built on the excellent [elasticsearch-mcp-server](https://github.com/cr7258/elasticsearch-mcp-server) project, this template brings unified search capabilities to your MCP platform.

## Overview

The Open Elastic Search template creates a containerized MCP server that can connect to either Elasticsearch or OpenSearch clusters, providing a comprehensive set of tools for index management, document operations, cluster monitoring, and general API access.

### Key Features

- **Dual Engine Support**: Works with both Elasticsearch (7.x, 8.x, 9.x) and OpenSearch (1.x, 2.x, 3.x)
- **Multiple Authentication Methods**: Supports API key authentication for Elasticsearch and username/password for both engines
- **Flexible Transport Options**: stdio, SSE, and streamable-http transport modes
- **Comprehensive Toolset**: 16 tools covering all major search engine operations
- **Custom Implementation**: Built from source for maximum flexibility and control
- **Production Ready**: Includes proper health checks, SSL configuration, and security features

## Engine Support

| Engine | Versions | Authentication |
|--------|----------|----------------|
| Elasticsearch | 7.x, 8.x, 9.x | API Key (recommended), Username/Password |
| OpenSearch | 1.x, 2.x, 3.x | Username/Password |

## Available Tools

### General Operations
- **general_api_request**: Perform any API request not covered by dedicated tools

### Index Operations
- **list_indices**: List all indices in the cluster
- **get_index**: Get detailed information about indices (mappings, settings, aliases)
- **create_index**: Create new indices with custom configuration
- **delete_index**: Remove indices from the cluster

### Document Operations
- **search_documents**: Search for documents using query DSL
- **index_document**: Create or update documents
- **get_document**: Retrieve specific documents by ID
- **delete_document**: Remove documents by ID
- **delete_by_query**: Bulk delete documents matching a query

### Cluster Operations
- **get_cluster_health**: Monitor cluster health status
- **get_cluster_stats**: Get comprehensive cluster statistics

### Alias Operations
- **list_aliases**: List all index aliases
- **get_alias**: Get alias information for specific indices
- **put_alias**: Create or update index aliases
- **delete_alias**: Remove index aliases

## Configuration

### Elasticsearch Configuration

```bash
# Required
ELASTICSEARCH_HOSTS="https://your-cluster:9200"

# Authentication (choose one)
ELASTICSEARCH_API_KEY="your_api_key"
# OR
ELASTICSEARCH_USERNAME="elastic"
ELASTICSEARCH_PASSWORD="your_password"

# Optional
ELASTICSEARCH_VERIFY_CERTS="false"  # Default: false
```

### OpenSearch Configuration

```bash
# Required
OPENSEARCH_HOSTS="https://your-cluster:9200"
OPENSEARCH_USERNAME="admin"
OPENSEARCH_PASSWORD="admin"

# Optional
OPENSEARCH_VERIFY_CERTS="false"  # Default: false
```

### Transport Configuration

```bash
# Transport mode
MCP_TRANSPORT="stdio"  # Options: stdio, sse, streamable-http

# For HTTP-based transports
MCP_HOST="0.0.0.0"
MCP_PORT="8000"
MCP_PATH="/mcp"
```

## Deployment Examples

### Deploy with Elasticsearch (API Key)

```bash
mcpp deploy open-elastic-search \
  --config ENGINE_TYPE="elasticsearch" \
  --config ELASTICSEARCH_HOSTS="https://your-cluster:9200" \
  --config ELASTICSEARCH_API_KEY="your_api_key"
```

### Deploy with Elasticsearch (Username/Password)

```bash
mcpp deploy open-elastic-search \
  --config ENGINE_TYPE="elasticsearch" \
  --config ELASTICSEARCH_HOSTS="https://your-cluster:9200" \
  --config ELASTICSEARCH_USERNAME="elastic" \
  --config ELASTICSEARCH_PASSWORD="your_password"
```

### Deploy with OpenSearch

```bash
mcpp deploy open-elastic-search \
  --config ENGINE_TYPE="opensearch" \
  --config OPENSEARCH_HOSTS="https://your-cluster:9200" \
  --config OPENSEARCH_USERNAME="admin" \
  --config OPENSEARCH_PASSWORD="admin"
```

### Deploy with HTTP Transport

```bash
mcpp deploy open-elastic-search \
  --config ENGINE_TYPE="elasticsearch" \
  --config ELASTICSEARCH_HOSTS="https://your-cluster:9200" \
  --config ELASTICSEARCH_API_KEY="your_api_key" \
  --config MCP_TRANSPORT="sse" \
  --config MCP_PORT="8080"
```

## Usage Examples

### Setup Elasticsearch (Optional)
```bash
python -c "from mcp_platform.backends.docker import DockerDeploymentService; DockerDeploymentService().create_network()"
docker run -d \
  --name elasticsearch \
  -p 9200:9200 \
  -p 9300:9300 \
  -e "discovery.type=single-node" \
  -e "xpack.security.enabled=true" \
  -e "ES_JAVA_OPTS=-Xms512m -Xmx512m" \
  -e "ELASTIC_PASSWORD=mcp-password-123" \
  --network mcp-platform \
  elasticsearch:9.1.3
```

### List all indices
```bash
mcpp interactive
mcpp> call open-elastic-search  list_indices --no-pull -C elasticsearch_username=elastic -C elasticsearch_password="mcp-password-123" -C elasticsearch_hosts="http://elasticsearch:9200" -C elasticsearch_verify_certs=true
```

### Search documents
```bash
mcpp interactive
mcpp> call open-elastic-search search_documents --no-pull -C elasticsearch_username=elastic -C elasticsearch_password="mcp-password-123" -C elasticsearch_hosts="http://elasticsearch:9200" -C elasticsearch_verify_certs=true '{
  "index": "logs",
  "body": {
    "query": {
      "match": {
        "message": "error"
      }
    },
    "size": 10
  }
}'
```

### Create an index
```bash
mcpp interactive
mcpp> call open-elastic-search --no-pull -C elasticsearch_username=elastic -C elasticsearch_password="mcp-password-123" -C elasticsearch_hosts="http://mcp-server:9300" -C elasticsearch_verify_certs=true create_index '{
  "index": "my-index",
  "body": {
    "settings": {
      "number_of_shards": 1,
      "number_of_replicas": 0
    },
    "mappings": {
      "properties": {
        "title": {"type": "text"},
        "timestamp": {"type": "date"}
      }
    }
  }
}'
```

### Index a document
```bash
mcpp interactive
mcpp> call open-elastic-search --no-pull -C elasticsearch_username=elastic -C elasticsearch_password="mcp-password-123" -C elasticsearch_hosts="http://mcp-server:9300" -C elasticsearch_verify_certs=true index_document '{
  "index": "my-index",
  "document": {
    "title": "Sample Document",
    "content": "This is a test document",
    "timestamp": "2024-01-15T10:30:00Z"
  }
}'
```

### Get cluster health
```bash
mcpp interactive
mcpp> call open-elastic-search --no-pull -C elasticsearch_username=elastic -C elasticsearch_password="mcp-password-123" -C elasticsearch_hosts="http://mcp-server:9300" -C elasticsearch_verify_certs=true get_cluster_health
```

## Security Considerations

- **Always use HTTPS** for production clusters
- **Use API keys** instead of username/password when possible (Elasticsearch)
- **Set `VERIFY_CERTS=true`** for production environments
- **Limit network access** to your clusters
- **Use strong passwords** and rotate credentials regularly

## Development Setup

For development against local clusters, you can use the provided Docker Compose files from the upstream project:

```bash
# Start Elasticsearch cluster
git clone https://github.com/cr7258/elasticsearch-mcp-server.git
cd elasticsearch-mcp-server
docker-compose -f docker-compose-elasticsearch.yml up -d

# Start OpenSearch cluster
docker-compose -f docker-compose-opensearch.yml up -d
```

## Troubleshooting

### Connection Issues
- Verify cluster URLs are accessible
- Check authentication credentials
- Ensure SSL/TLS configuration is correct
- Verify network connectivity and firewall rules

### Authentication Problems
- For Elasticsearch: Try both API key and username/password methods
- For OpenSearch: Ensure username/password are correct
- Check if credentials have appropriate permissions

### Performance Optimization
- Use connection pooling for high-throughput scenarios
- Adjust search result sizes based on your needs
- Monitor cluster resources and adjust accordingly

## Experimental Notice

⚠️ **This MCP server is EXPERIMENTAL** and should be used with caution in production environments. The template supports both Elasticsearch and OpenSearch, but thorough testing is recommended for your specific use case.

## Support

This template is based on the [elasticsearch-mcp-server](https://github.com/cr7258/elasticsearch-mcp-server) project. For issues specific to the underlying implementation, please refer to the upstream repository.
