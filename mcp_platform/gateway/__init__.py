"""
MCP Gateway - Unified proxy and load balancer for MCP servers.

This module provides a single HTTP endpoint for accessing all deployed MCP servers
with intelligent routing, load balancing, and health checking capabilities.

The gateway supports:
- HTTP and stdio MCP server proxying
- Multiple load balancing strategies (round-robin, least-connections, etc.)
- Health monitoring and automatic failover
- Dynamic server registration and discovery
- Integration with existing MCP Platform backends (Docker, Kubernetes)
"""

from .gateway_server import MCPGatewayServer
from .health_checker import HealthChecker
from .load_balancer import LoadBalancer, LoadBalancingStrategy
from .registry import ServerRegistry

__all__ = [
    "MCPGatewayServer",
    "LoadBalancer",
    "LoadBalancingStrategy",
    "ServerRegistry",
    "HealthChecker",
]
