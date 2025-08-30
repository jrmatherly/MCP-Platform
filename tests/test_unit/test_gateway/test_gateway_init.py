"""
Unit tests for gateway package initialization.
"""

import pytest

pytestmark = pytest.mark.unit


class TestGatewayPackage:
    """Unit tests for gateway package imports."""

    def test_gateway_imports(self):
        """Test that all gateway components can be imported."""
        from mcp_platform.gateway import (
            HealthChecker,
            LoadBalancer,
            LoadBalancingStrategy,
            MCPGatewayServer,
            ServerRegistry,
        )

        # Test that classes can be instantiated
        registry = ServerRegistry()
        assert registry is not None

        load_balancer = LoadBalancer()
        assert load_balancer is not None

        health_checker = HealthChecker(registry)
        assert health_checker is not None

        # Test enum
        assert LoadBalancingStrategy.ROUND_ROBIN is not None
        assert LoadBalancingStrategy.LEAST_CONNECTIONS is not None

        # Test gateway server (just class, don't start it)
        assert MCPGatewayServer is not None

    def test_gateway_in_main_package(self):
        """Test that gateway components are exposed in main package."""
        from mcp_platform import (
            HealthChecker,
            LoadBalancer,
            MCPGatewayServer,
            ServerRegistry,
        )

        assert HealthChecker is not None
        assert LoadBalancer is not None
        assert MCPGatewayServer is not None
        assert ServerRegistry is not None
