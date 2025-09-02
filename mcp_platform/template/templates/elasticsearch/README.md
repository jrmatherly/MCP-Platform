# Elasticsearch MCP Server

This template provides integration with Elasticsearch using the official Elasticsearch MCP server.

## ⚠️ EXPERIMENTAL WARNING

This MCP server is EXPERIMENTAL as noted in the official Elasticsearch repository. Use with caution in production environments.

## Features

- **Full Elasticsearch Integration**: Access all your Elasticsearch data through MCP
- **Multiple Authentication Methods**: Support for API keys and username/password
- **Flexible Transport**: Support for both stdio and HTTP transport modes
- **Comprehensive Tools**: 5 essential tools for Elasticsearch operations
- **Version Support**: Compatible with Elasticsearch 8.x and 9.x

## Quick Setup

1. Deploy the server:
   ```bash
   mcpp deploy elasticsearch
   ```

2. Configure with your Elasticsearch credentials:
   ```bash
   # Using API key (recommended)
   mcpp configure elasticsearch ES_URL="https://your-cluster:9200" ES_API_KEY="your_key"

   # Using username/password
   mcpp configure elasticsearch ES_URL="https://your-cluster:9200" ES_USERNAME="elastic" ES_PASSWORD="your_password"
   ```

3. Test the connection:
   ```bash
   mcpp i
   mcpp> call elasticsearch list_indices --no-pull -C es_username=elastic -C es_password="jezTfCghVFjmYh2Y3N4k" -C es_url="http://host.docker.internal:9300" -C es_ssl_skip_verify=true '{"index_pattern":"*"}'
   ```

## Available Tools

- `list_indices` - List all Elasticsearch indices
- `get_mappings` - Get field mappings for an index
- `search` - Perform Elasticsearch search queries
- `esql` - Execute ES|QL queries
- `get_shards` - Get shard information

## Documentation

For complete documentation, see the [docs/index.md](docs/index.md) file.
