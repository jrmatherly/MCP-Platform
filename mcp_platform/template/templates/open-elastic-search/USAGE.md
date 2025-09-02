# Open Elastic Search MCP Server Template - Usage Examples

This file contains comprehensive examples of how to use the Open Elastic Search MCP Server template with both Elasticsearch and OpenSearch clusters.

## Deployment Examples

### 1. Deploy with Elasticsearch (API Key Authentication)
```bash
# Deploy with API key (recommended for Elasticsearch)
mcpp deploy open-elastic-search \
  --config ENGINE_TYPE="elasticsearch" \
  --config ELASTICSEARCH_HOSTS="https://your-elasticsearch-cluster:9200" \
  --config ELASTICSEARCH_API_KEY="your_api_key_here"
```

### 2. Deploy with Elasticsearch (Username/Password Authentication)
```bash
# Deploy with basic authentication
mcpp deploy open-elastic-search \
  --config ENGINE_TYPE="elasticsearch" \
  --config ELASTICSEARCH_HOSTS="https://your-elasticsearch-cluster:9200" \
  --config ELASTICSEARCH_USERNAME="elastic" \
  --config ELASTICSEARCH_PASSWORD="your_password_here"
```

### 3. Deploy with OpenSearch
```bash
# Deploy with OpenSearch cluster
mcpp deploy open-elastic-search \
  --config ENGINE_TYPE="opensearch" \
  --config OPENSEARCH_HOSTS="https://your-opensearch-cluster:9200" \
  --config OPENSEARCH_USERNAME="admin" \
  --config OPENSEARCH_PASSWORD="admin"
```

### 4. Deploy with SSL Verification Disabled (Development Only)
```bash
# For development with self-signed certificates (Elasticsearch)
mcpp deploy open-elastic-search \
  --config ENGINE_TYPE="elasticsearch" \
  --config ELASTICSEARCH_HOSTS="https://localhost:9200" \
  --config ELASTICSEARCH_API_KEY="your_api_key" \
  --config ELASTICSEARCH_VERIFY_CERTS="false"

# For OpenSearch
mcpp deploy open-elastic-search \
  --config ENGINE_TYPE="opensearch" \
  --config OPENSEARCH_HOSTS="https://localhost:9200" \
  --config OPENSEARCH_USERNAME="admin" \
  --config OPENSEARCH_PASSWORD="admin" \
  --config OPENSEARCH_VERIFY_CERTS="false"
```

### 5. Deploy with SSE Transport
```bash
# Use SSE transport for HTTP-based communication
mcpp deploy open-elastic-search \
  --config ENGINE_TYPE="elasticsearch" \
  --config ELASTICSEARCH_HOSTS="https://your-cluster:9200" \
  --config ELASTICSEARCH_API_KEY="your_key" \
  --config MCP_TRANSPORT="sse" \
  --config MCP_HOST="0.0.0.0" \
  --config MCP_PORT="8000" \
  --config MCP_PATH="/sse"
```

### 6. Deploy with Streamable HTTP Transport
```bash
# Use streamable-http transport
mcpp deploy open-elastic-search \
  --config ENGINE_TYPE="elasticsearch" \
  --config ELASTICSEARCH_HOSTS="https://your-cluster:9200" \
  --config ELASTICSEARCH_API_KEY="your_key" \
  --config MCP_TRANSPORT="streamable-http" \
  --config MCP_HOST="0.0.0.0" \
  --config MCP_PORT="8000" \
  --config MCP_PATH="/mcp"
```

## Tool Usage Examples

### General Operations

#### Make a custom API request
```bash
mcpp call open-elastic-search general_api_request '{
  "method": "GET",
  "path": "/_cluster/settings",
  "params": {
    "include_defaults": true
  }
}'
```

### Index Operations

#### List all indices
```bash
mcpp call open-elastic-search list_indices
```

#### Get detailed index information
```bash
mcpp call open-elastic-search get_index '{"index": "my-index"}'
```

#### Create a new index with mappings
```bash
mcpp call open-elastic-search create_index '{
  "index": "product-catalog",
  "body": {
    "settings": {
      "number_of_shards": 2,
      "number_of_replicas": 1,
      "analysis": {
        "analyzer": {
          "custom_analyzer": {
            "tokenizer": "standard",
            "filter": ["lowercase", "stop"]
          }
        }
      }
    },
    "mappings": {
      "properties": {
        "name": {
          "type": "text",
          "analyzer": "custom_analyzer"
        },
        "description": {
          "type": "text"
        },
        "price": {
          "type": "float"
        },
        "category": {
          "type": "keyword"
        },
        "created_at": {
          "type": "date"
        },
        "tags": {
          "type": "keyword"
        }
      }
    }
  }
}'
```

#### Delete an index
```bash
mcpp call open-elastic-search delete_index '{"index": "old-index"}'
```

### Document Operations

#### Search for documents with complex query
```bash
mcpp call open-elastic-search search_documents '{
  "index": "product-catalog",
  "body": {
    "query": {
      "bool": {
        "must": [
          {
            "match": {
              "name": "laptop"
            }
          },
          {
            "range": {
              "price": {
                "gte": 500,
                "lte": 2000
              }
            }
          }
        ],
        "filter": [
          {
            "term": {
              "category": "electronics"
            }
          }
        ]
      }
    },
    "sort": [
      {
        "price": {
          "order": "asc"
        }
      }
    ],
    "size": 20,
    "_source": ["name", "price", "category"]
  }
}'
```

#### Index a document
```bash
mcpp call open-elastic-search index_document '{
  "index": "product-catalog",
  "document": {
    "name": "MacBook Pro",
    "description": "High-performance laptop for professionals",
    "price": 1999.99,
    "category": "electronics",
    "created_at": "2024-01-15T10:30:00Z",
    "tags": ["laptop", "apple", "professional"]
  }
}'
```

#### Index a document with specific ID
```bash
mcpp call open-elastic-search index_document '{
  "index": "product-catalog",
  "id": "prod-001",
  "document": {
    "name": "Dell XPS 13",
    "description": "Compact ultrabook with excellent performance",
    "price": 1299.99,
    "category": "electronics",
    "created_at": "2024-01-15T11:00:00Z",
    "tags": ["laptop", "dell", "ultrabook"]
  }
}'
```

#### Get a document by ID
```bash
mcpp call open-elastic-search get_document '{
  "index": "product-catalog",
  "id": "prod-001"
}'
```

#### Delete a document
```bash
mcpp call open-elastic-search delete_document '{
  "index": "product-catalog",
  "id": "prod-001"
}'
```

#### Delete documents by query
```bash
mcpp call open-elastic-search delete_by_query '{
  "index": "product-catalog",
  "body": {
    "query": {
      "range": {
        "created_at": {
          "lt": "2023-01-01"
        }
      }
    }
  }
}'
```

### Cluster Operations

#### Get cluster health
```bash
mcpp call open-elastic-search get_cluster_health
```

#### Get cluster statistics
```bash
mcpp call open-elastic-search get_cluster_stats
```

### Alias Operations

#### List all aliases
```bash
mcpp call open-elastic-search list_aliases
```

#### Get aliases for a specific index
```bash
mcpp call open-elastic-search get_alias '{"index": "product-catalog"}'
```

#### Create an alias
```bash
mcpp call open-elastic-search put_alias '{
  "index": "product-catalog-v2",
  "alias": "product-catalog",
  "body": {
    "filter": {
      "term": {
        "status": "active"
      }
    }
  }
}'
```

#### Delete an alias
```bash
mcpp call open-elastic-search delete_alias '{
  "index": "product-catalog-v1",
  "alias": "product-catalog"
}'
```

## Advanced Usage Scenarios

### 1. Multi-Index Search
```bash
mcpp call open-elastic-search search_documents '{
  "index": "logs-*,metrics-*",
  "body": {
    "query": {
      "bool": {
        "must": [
          {
            "range": {
              "@timestamp": {
                "gte": "now-1h"
              }
            }
          }
        ]
      }
    },
    "sort": [
      {
        "@timestamp": {
          "order": "desc"
        }
      }
    ],
    "size": 100
  }
}'
```

### 2. Aggregations Query
```bash
mcpp call open-elastic-search search_documents '{
  "index": "sales-data",
  "body": {
    "size": 0,
    "aggs": {
      "sales_by_category": {
        "terms": {
          "field": "category.keyword",
          "size": 10
        },
        "aggs": {
          "total_revenue": {
            "sum": {
              "field": "amount"
            }
          },
          "avg_order_value": {
            "avg": {
              "field": "amount"
            }
          }
        }
      },
      "sales_over_time": {
        "date_histogram": {
          "field": "@timestamp",
          "calendar_interval": "1d"
        },
        "aggs": {
          "daily_revenue": {
            "sum": {
              "field": "amount"
            }
          }
        }
      }
    }
  }
}'
```

### 3. Bulk Index Multiple Documents
```bash
# Index multiple documents (you'd typically use this pattern in a script)
for doc in doc1 doc2 doc3; do
  mcpp call open-elastic-search index_document "{
    \"index\": \"bulk-test\",
    \"document\": {
      \"name\": \"$doc\",
      \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"
    }
  }"
done
```

### 4. Index Template Creation (via general API)
```bash
mcpp call open-elastic-search general_api_request '{
  "method": "PUT",
  "path": "/_index_template/logs-template",
  "body": {
    "index_patterns": ["logs-*"],
    "template": {
      "settings": {
        "number_of_shards": 1,
        "number_of_replicas": 1
      },
      "mappings": {
        "properties": {
          "@timestamp": {
            "type": "date"
          },
          "level": {
            "type": "keyword"
          },
          "message": {
            "type": "text"
          },
          "source": {
            "type": "keyword"
          }
        }
      }
    }
  }
}'
```

## Development and Testing

### Local Development Setup
```bash
# Start local Elasticsearch cluster
git clone https://github.com/cr7258/elasticsearch-mcp-server.git
cd elasticsearch-mcp-server
docker-compose -f docker-compose-elasticsearch.yml up -d

# Deploy against local cluster
mcpp deploy open-elastic-search \
  --config ENGINE_TYPE="elasticsearch" \
  --config ELASTICSEARCH_HOSTS="https://localhost:9200" \
  --config ELASTICSEARCH_USERNAME="elastic" \
  --config ELASTICSEARCH_PASSWORD="test123" \
  --config ELASTICSEARCH_VERIFY_CERTS="false"
```

### Testing OpenSearch
```bash
# Start local OpenSearch cluster
docker-compose -f docker-compose-opensearch.yml up -d

# Deploy against local OpenSearch
mcpp deploy open-elastic-search \
  --config ENGINE_TYPE="opensearch" \
  --config OPENSEARCH_HOSTS="https://localhost:9200" \
  --config OPENSEARCH_USERNAME="admin" \
  --config OPENSEARCH_PASSWORD="admin" \
  --config OPENSEARCH_VERIFY_CERTS="false"
```

## Best Practices

1. **Always use HTTPS** in production environments
2. **Use API keys** for Elasticsearch when possible (more secure than username/password)
3. **Enable SSL certificate verification** in production (`*_VERIFY_CERTS="true"`)
4. **Use index patterns** for time-based data (e.g., `logs-2024-01-*`)
5. **Implement proper error handling** in your applications
6. **Monitor cluster health** regularly using the cluster health tools
7. **Use aliases** for seamless index migrations and zero-downtime deployments
8. **Optimize queries** by using filters instead of queries when possible
9. **Set appropriate shard and replica counts** based on your data volume and cluster size
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
