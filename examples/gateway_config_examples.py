"""
MCP Gateway Configuration Examples

This file demonstrates various configuration scenarios for the MCP Gateway.
Copy and modify these examples for your specific use case.
"""

import json
from pathlib import Path

# Example 1: Basic Gateway Registry Configuration
BASIC_REGISTRY = {
    "templates": {
        "demo": {
            "instances": [
                {
                    "id": "demo-1",
                    "template_name": "demo",
                    "endpoint": "http://localhost:7071",
                    "transport": "http",
                    "backend": "docker",
                    "container_id": "mcp-demo-1",
                    "is_healthy": True,
                    "last_health_check": "2024-01-01T00:00:00",
                    "health_check_count": 0,
                    "error_count": 0,
                    "metadata": {"weight": 1},
                }
            ],
            "load_balancer": {
                "strategy": "round_robin",
                "health_check_interval": 30,
                "max_retries": 3,
            },
        }
    },
    "global_config": {
        "default_health_check_interval": 30,
        "max_concurrent_health_checks": 10,
        "default_max_retries": 3,
    },
}

# Example 2: High Availability Setup with Multiple Backends
HA_REGISTRY = {
    "templates": {
        "filesystem": {
            "instances": [
                # Docker instances
                {
                    "id": "fs-docker-1",
                    "template_name": "filesystem",
                    "endpoint": "http://localhost:7072",
                    "transport": "http",
                    "backend": "docker",
                    "container_id": "mcp-filesystem-1",
                    "is_healthy": True,
                    "metadata": {"weight": 2, "region": "us-east-1"},
                },
                {
                    "id": "fs-docker-2",
                    "template_name": "filesystem",
                    "endpoint": "http://localhost:7073",
                    "transport": "http",
                    "backend": "docker",
                    "container_id": "mcp-filesystem-2",
                    "is_healthy": True,
                    "metadata": {"weight": 2, "region": "us-east-1"},
                },
                # Kubernetes instances
                {
                    "id": "fs-k8s-1",
                    "template_name": "filesystem",
                    "endpoint": "http://mcp-filesystem.default.svc.cluster.local:8080",
                    "transport": "http",
                    "backend": "kubernetes",
                    "pod_name": "mcp-filesystem-7b8c9d",
                    "namespace": "default",
                    "is_healthy": True,
                    "metadata": {"weight": 3, "region": "us-west-2"},
                },
            ],
            "load_balancer": {
                "strategy": "weighted",  # Favor k8s instance
                "health_check_interval": 15,  # More frequent health checks
                "max_retries": 2,
            },
        },
        "web-search": {
            "instances": [
                {
                    "id": "search-1",
                    "template_name": "web-search",
                    "command": ["python", "-m", "mcp_server_web_search"],
                    "transport": "stdio",
                    "backend": "docker",
                    "container_id": "mcp-websearch-1",
                    "working_dir": "/app",
                    "env_vars": {"SEARCH_API_KEY": "your-api-key", "MAX_RESULTS": "10"},
                    "is_healthy": True,
                    "metadata": {"weight": 1},
                }
            ],
            "load_balancer": {
                "strategy": "least_connections",
                "health_check_interval": 45,
                "max_retries": 3,
            },
        },
    },
    "global_config": {
        "default_health_check_interval": 30,
        "max_concurrent_health_checks": 5,
        "default_max_retries": 2,
    },
}

# Example 3: Development Environment with Mixed Transports
DEV_REGISTRY = {
    "templates": {
        "local-dev": {
            "instances": [
                # Local HTTP server for testing
                {
                    "id": "dev-http",
                    "template_name": "local-dev",
                    "endpoint": "http://localhost:3000",
                    "transport": "http",
                    "backend": "local",
                    "is_healthy": True,
                    "metadata": {"environment": "development"},
                },
                # Local stdio server for debugging
                {
                    "id": "dev-stdio",
                    "template_name": "local-dev",
                    "command": ["python", "local_mcp_server.py"],
                    "transport": "stdio",
                    "backend": "local",
                    "working_dir": "/Users/dev/mcp-servers",
                    "env_vars": {"DEBUG": "true"},
                    "is_healthy": True,
                    "metadata": {"environment": "development"},
                },
            ],
            "load_balancer": {
                "strategy": "round_robin",
                "health_check_interval": 10,  # Fast checks for dev
                "max_retries": 1,
            },
        }
    }
}

# Example 4: Production Setup with Health-Based Load Balancing
PROD_REGISTRY = {
    "templates": {
        "api-gateway": {
            "instances": [
                {
                    "id": "api-prod-1",
                    "template_name": "api-gateway",
                    "endpoint": "https://api1.mycompany.com/mcp",
                    "transport": "http",
                    "backend": "kubernetes",
                    "pod_name": "api-gateway-deployment-abc123",
                    "namespace": "production",
                    "is_healthy": True,
                    "metadata": {
                        "weight": 3,
                        "tier": "production",
                        "datacenter": "dc1",
                    },
                },
                {
                    "id": "api-prod-2",
                    "template_name": "api-gateway",
                    "endpoint": "https://api2.mycompany.com/mcp",
                    "transport": "http",
                    "backend": "kubernetes",
                    "pod_name": "api-gateway-deployment-def456",
                    "namespace": "production",
                    "is_healthy": True,
                    "metadata": {
                        "weight": 3,
                        "tier": "production",
                        "datacenter": "dc2",
                    },
                },
                {
                    "id": "api-staging",
                    "template_name": "api-gateway",
                    "endpoint": "https://staging-api.mycompany.com/mcp",
                    "transport": "http",
                    "backend": "kubernetes",
                    "pod_name": "api-gateway-staging-xyz789",
                    "namespace": "staging",
                    "is_healthy": True,
                    "metadata": {
                        "weight": 1,  # Lower weight for staging
                        "tier": "staging",
                        "datacenter": "dc1",
                    },
                },
            ],
            "load_balancer": {
                "strategy": "health_based",  # Route to healthiest instances
                "health_check_interval": 20,
                "max_retries": 3,
            },
        }
    },
    "global_config": {
        "default_health_check_interval": 30,
        "max_concurrent_health_checks": 20,
        "default_max_retries": 3,
    },
}


def save_config_example(config_name: str, config_data: dict, output_dir: Path = None):
    """Save a configuration example to a file."""
    if output_dir is None:
        output_dir = Path.home() / ".mcp" / "examples"

    output_dir.mkdir(parents=True, exist_ok=True)
    config_file = output_dir / f"{config_name}_registry.json"

    with open(config_file, "w") as f:
        json.dump(config_data, f, indent=2)

    print(f"✅ Saved {config_name} configuration to {config_file}")
    return config_file


def create_all_examples():
    """Create all configuration examples."""
    examples = [
        ("basic", BASIC_REGISTRY),
        ("ha", HA_REGISTRY),
        ("dev", DEV_REGISTRY),
        ("prod", PROD_REGISTRY),
    ]

    for name, config in examples:
        save_config_example(name, config)


# CLI usage examples
CLI_EXAMPLES = """
# MCP Gateway CLI Examples

## Starting the Gateway

# Start with default settings
mcpp gateway start

# Start with custom host/port
mcpp gateway start --host 0.0.0.0 --port 9000

# Start with auto-sync from deployments
mcpp gateway start --sync

# Start with custom registry file
mcpp gateway start --registry-file /path/to/custom_registry.json

## Managing Server Instances

# Register a new HTTP server
mcpp gateway register mytemplate --endpoint http://localhost:8080

# Register a stdio server
mcpp gateway register mytemplate --command "python server.py" --working-dir /app

# Deregister a specific instance
mcpp gateway deregister mytemplate --instance-id mytemplate-1

# Deregister all instances of a template
mcpp gateway deregister mytemplate --all

## Monitoring and Status

# Check gateway status
mcpp gateway status

# Check status with detailed health info
mcpp gateway status --verbose

# Sync with current deployments
mcpp gateway sync

# Clean up unhealthy instances
mcpp gateway cleanup

## Configuration Examples

# Use a specific load balancing strategy
mcpp gateway register mytemplate --endpoint http://localhost:8080 --lb-strategy weighted

# Set custom health check interval
mcpp gateway register mytemplate --endpoint http://localhost:8080 --health-interval 60

# Add metadata for filtering/routing
mcpp gateway register mytemplate --endpoint http://localhost:8080 --metadata '{"region":"us-east","tier":"prod"}'

## Using the Gateway HTTP API

# List all available tools from a template (load balanced)
curl http://localhost:8080/mcp/mytemplate/tools/list

# Call a specific tool (load balanced)
curl -X POST http://localhost:8080/mcp/mytemplate/tools/call \\
  -H "Content-Type: application/json" \\
  -d '{"name": "read_file", "arguments": {"path": "/app/data.txt"}}'

# Check template health
curl http://localhost:8080/mcp/mytemplate/health

# Get gateway health
curl http://localhost:8080/gateway/health

# Get full registry status
curl http://localhost:8080/gateway/registry

# Get load balancer stats
curl http://localhost:8080/gateway/stats
"""


if __name__ == "__main__":
    print("Creating MCP Gateway configuration examples...")
    create_all_examples()

    print("\n" + "=" * 60)
    print(CLI_EXAMPLES)
