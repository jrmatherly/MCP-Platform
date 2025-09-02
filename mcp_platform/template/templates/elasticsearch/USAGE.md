# Elasticsearch MCP Server Template - Usage Examples

This file contains examples of how to use the Elasticsearch MCP Server template.

## Basic Usage Examples

### 1. Deploy with API Key Authentication
```bash
# Deploy with API key (recommended)
mcpp deploy elasticsearch \
  --config ES_URL="https://your-elasticsearch-cluster:9200" \
  --config ES_API_KEY="your_api_key_here"
```

### 2. Deploy with Username/Password Authentication
```bash
# Deploy with basic authentication
mcpp deploy elasticsearch \
  --config ES_URL="https://your-elasticsearch-cluster:9200" \
  --config ES_USERNAME="elastic" \
  --config ES_PASSWORD="your_password_here"
```

### 3. Deploy with SSL Verification Disabled (Development Only)
```bash
# For development with self-signed certificates
mcpp deploy elasticsearch \
  --config ES_URL="https://localhost:9200" \
  --config ES_API_KEY="your_api_key" \
  --config ES_SSL_SKIP_VERIFY="true"
```

### 4. Deploy with HTTP Transport
```bash
# Use HTTP transport instead of stdio
mcpp deploy elasticsearch \
  --config ES_URL="https://your-cluster:9200" \
  --config ES_API_KEY="your_key" \
  --config MCP_TRANSPORT="http" \
  --config MCP_PORT="8080"
```

## Tool Usage Examples

### List all indices
```bash
mcpp call elasticsearch list_indices
```

### Get mappings for an index
```bash
mcpp call elasticsearch get_mappings '{"index": "your-index-name"}'
```

### Search documents
```bash
mcpp call elasticsearch search '{
  "index": "your-index",
  "query": {
    "match": {
      "field": "search term"
    }
  },
  "size": 5
}'
```

### Execute ES|QL query
```bash
mcpp call elasticsearch esql '{
  "query": "FROM your-index | WHERE field > 100 | LIMIT 10"
}'
```

### Get shard information
```bash
# Get shards for all indices
mcpp call elasticsearch get_shards

# Get shards for specific index
mcpp call elasticsearch get_shards '{"index": "your-index"}'
```

## Environment Variable Configuration

You can also configure using environment variables:

```bash
export ES_URL="https://your-cluster:9200"
export ES_API_KEY="your_api_key"
export LOG_LEVEL="DEBUG"

mcpp deploy elasticsearch
```

## Troubleshooting

### Connection Issues
```bash
# Test connectivity
mcpp call elasticsearch list_indices --verbose

# Check logs
mcpp logs elasticsearch
```

### Authentication Issues
```bash
# Verify credentials
mcpp configure elasticsearch ES_API_KEY="new_api_key"

# Test with debug logging
mcpp deploy elasticsearch --config LOG_LEVEL="DEBUG"
```
