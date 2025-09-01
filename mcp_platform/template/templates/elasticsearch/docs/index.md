# Elasticsearch MCP Server Documentation

## Overview

> **⚠️ WARNING: This MCP server is EXPERIMENTAL.**

The Elasticsearch MCP Server template extends the official Elasticsearch MCP server to provide seamless integration with your Elasticsearch data using the Model Context Protocol (MCP). This template allows you to interact with your Elasticsearch indices through natural language conversations.

Our platform extends the official Elasticsearch MCP server by providing:
- **🚀 One-Command Deployment**: Deploy and manage Elasticsearch MCP servers with a single command
- **🔧 Simplified Configuration**: Streamlined environment variable and authentication management
- **📊 Comprehensive Monitoring**: Built-in logging, status monitoring, and error tracking
- **🔄 Auto-Scaling**: Docker-based deployment with automatic container management
- **⚙️ Security**: Secure credential handling and SSL configuration
- **📈 Performance Optimization**: Efficient connection management and query optimization

## Supported Elasticsearch Versions

This template works with Elasticsearch versions **8.x** and **9.x** only.

## Available Tools

The Elasticsearch MCP server provides 5 essential tools for Elasticsearch operations:

### Index Management
- **`list_indices`**: List all available Elasticsearch indices in your cluster
- **`get_mappings`**: Get detailed field mappings for a specific Elasticsearch index

### Search & Query
- **`search`**: Perform advanced Elasticsearch searches using query DSL
- **`esql`**: Execute ES|QL queries for powerful data analysis

### Cluster Information
- **`get_shards`**: Get comprehensive shard information for indices

## Quick Start

### Prerequisites

Before deploying the Elasticsearch MCP server, ensure you have:

1. **Elasticsearch Cluster**: A running Elasticsearch 8.x or 9.x cluster
2. **Authentication Credentials**: Either an API key or username/password
3. **Network Access**: Connectivity between the MCP server and your Elasticsearch cluster

### Installation

Deploy the Elasticsearch MCP server using our platform:

```bash
# Deploy with API key authentication
mcpp deploy elasticsearch --config ES_URL="https://your-elasticsearch-cluster:9200" --config ES_API_KEY="your_api_key"

# Deploy with username/password authentication
mcpp deploy elasticsearch --config ES_URL="https://your-elasticsearch-cluster:9200" --config ES_USERNAME="elastic" --config ES_PASSWORD="your_password"

# Check deployment status
mcpp status elasticsearch

# View real-time logs
mcpp logs elasticsearch
```

### Configuration

The template supports flexible authentication and configuration options:

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `ES_URL` | Elasticsearch cluster URL | Yes | - |
| `ES_API_KEY` | API key for authentication | Yes* | - |
| `ES_USERNAME` | Username for basic auth | Yes* | - |
| `ES_PASSWORD` | Password for basic auth | Yes* | - |
| `ES_SSL_SKIP_VERIFY` | Skip SSL certificate verification | No | false |
| `LOG_LEVEL` | Logging level (DEBUG, INFO, WARNING, ERROR) | No | INFO |
| `MCP_TRANSPORT` | Transport protocol (stdio, http) | No | stdio |
| `MCP_PORT` | Port for HTTP transport | No | 8080 |

*Either `ES_API_KEY` or both `ES_USERNAME` and `ES_PASSWORD` are required for authentication.

#### Creating an Elasticsearch API Key

API key authentication is recommended for security. To create an API key:

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
             "privileges": ["read", "view_index_metadata"]
           }
         ]
       }
     }
   }'
   ```

#### SSL Configuration

For production environments with self-signed certificates:

```bash
# Skip SSL verification (not recommended for production)
mcpp deploy elasticsearch --config ES_SSL_SKIP_VERIFY="true"

# For proper SSL handling, ensure your Elasticsearch cluster has valid certificates
```

## Tool Discovery

Our platform provides dynamic tool discovery to automatically catalog all available Elasticsearch tools:

```bash
# Discover all available tools
mcpp> tools elasticsearch --config ES_URL="https://your-cluster:9200" --config ES_API_KEY="your_key"

# Refresh tool cache
mcpp> tools elasticsearch --refresh

# Get detailed tool information
mcpp> tools elasticsearch --verbose
```

## Platform Benefits

### Enhanced Deployment
- **Docker Integration**: Seamless container-based deployment extending official image
- **Environment Management**: Secure handling of Elasticsearch credentials
- **Health Monitoring**: Automatic health checks and restart policies
- **Port Management**: Automatic port allocation and HTTP/stdio transport support

### Advanced Security
- **Credential Security**: Secure storage and handling of API keys and passwords
- **SSL Support**: Flexible SSL configuration for secure connections
- **Access Control**: Fine-grained authentication and authorization

### Developer Experience
- **One-Command Setup**: Deploy Elasticsearch integration in seconds
- **Interactive CLI**: Rich terminal interface with progress indicators
- **Comprehensive Documentation**: Auto-generated tool documentation
- **Error Handling**: Robust error handling with helpful messages

## Development

### Local Development

```bash
# Clone and set up local development
git clone <repository-url>
cd elasticsearch-template

# Set environment variables
export ES_URL="https://localhost:9200"
export ES_API_KEY="your_api_key"
export LOG_LEVEL="DEBUG"

# Run with Docker
docker build -t elasticsearch-mcp-local .
docker run -e ES_URL -e ES_API_KEY elasticsearch-mcp-local
```

### Testing

```bash
# Test with our platform
mcpp deploy elasticsearch --config ES_URL="https://localhost:9200" --config ES_API_KEY="test_key"

# Call tools directly
mcpp call elasticsearch list_indices
mcpp call elasticsearch search '{"index": "test-index", "query": {"match_all": {}}}'
```

## Monitoring & Troubleshooting

### Health Checks

```bash
# Check service status
mcpp status elasticsearch

# Get detailed health information
mcpp status elasticsearch --detailed

# View real-time logs
mcpp logs elasticsearch --follow
```

### Common Issues

1. **Connection Errors**
   - Verify ES_URL is correct and accessible
   - Check network connectivity to Elasticsearch cluster
   - Ensure Elasticsearch is running and healthy

2. **Authentication Failures**
   - Verify API key or username/password are correct
   - Check API key privileges and expiration
   - Ensure user has necessary permissions

3. **SSL/TLS Issues**
   - For self-signed certificates, set `ES_SSL_SKIP_VERIFY=true` (development only)
   - For production, ensure proper certificate chain
   - Check certificate validity and hostname matching

4. **Query Errors**
   - Validate Elasticsearch query DSL syntax
   - Check index names and field mappings
   - Verify data types in ES|QL queries

### Debug Mode

Enable comprehensive debugging:

```bash
# Deploy with debug logging
mcpp deploy elasticsearch --config LOG_LEVEL="DEBUG"

# View debug logs
mcpp logs elasticsearch --level debug

# Test connectivity
mcpp call elasticsearch list_indices --verbose
```

## Security Best Practices

### Authentication
- **Use API Keys**: Prefer API key authentication over username/password
- **Principle of Least Privilege**: Grant only necessary permissions
- **Regular Rotation**: Rotate API keys regularly
- **Secure Storage**: Never expose credentials in logs or configuration files

### Network Security
- **Use HTTPS**: Always use encrypted connections to Elasticsearch
- **Network Isolation**: Deploy in secure network environments
- **Firewall Rules**: Restrict access to Elasticsearch ports
- **VPN/Tunnel**: Use VPN or SSH tunneling for remote access

### Monitoring
- **Audit Logging**: Enable Elasticsearch audit logging
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
- **Query Efficiency**: Optimize Elasticsearch queries for performance
- **Result Limiting**: Use appropriate size limits for large result sets
- **Pagination**: Implement proper pagination for large datasets

## API Reference

All 5 Elasticsearch tools are available through the MCP interface. Each tool includes:
- **Input Schema**: Detailed parameter specifications
- **Output Schema**: Response format documentation
- **Error Handling**: Comprehensive error response patterns
- **Examples**: Real-world usage examples

For detailed API documentation of each tool, use:
```bash
mcpp> tools elasticsearch --tool-name <tool_name> --detailed
```

## Experimental Notice

**⚠️ This MCP server is EXPERIMENTAL** as noted in the official Elasticsearch repository. While it provides full functionality for interacting with Elasticsearch, please be aware that:

- API interfaces may change in future versions
- Some features may not be fully stable
- Thorough testing is recommended before production use
- Official support may be limited

## Contributing

We welcome contributions to improve the Elasticsearch MCP server template:

1. **Bug Reports**: Submit issues with detailed reproduction steps
2. **Feature Requests**: Propose new Elasticsearch integrations
3. **Pull Requests**: Contribute code improvements
4. **Documentation**: Help improve this documentation

See the main repository's contributing guidelines for detailed information.

## License

This template extends the official Elasticsearch MCP server and is part of the MCP Server Templates project. See LICENSE for details.

## Support

For support, please open an issue in the main repository or contact the maintainers.