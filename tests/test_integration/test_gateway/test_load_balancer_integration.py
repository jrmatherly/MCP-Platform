"""
Load balancer integration tests.
"""

import pytest

from mcp_platform.gateway.load_balancer import LoadBalancer, LoadBalancingStrategy
from mcp_platform.gateway.models import ServerInstance, ServerStatus

pytestmark = pytest.mark.integration


class TestLoadBalancerIntegration:
    """Test load balancer integration scenarios."""

    def test_load_balancer_with_registry_integration(self):
        """Test load balancer working with instances from registry."""

        # Create load balancer
        load_balancer = LoadBalancer(LoadBalancingStrategy.ROUND_ROBIN)

        # Create test instances
        instance1 = ServerInstance(
            id="server1", template_name="test", status=ServerStatus.HEALTHY
        )
        instance2 = ServerInstance(
            id="server2", template_name="test", status=ServerStatus.HEALTHY
        )
        instances = [instance1, instance2]

        # Test instance selection with actual API
        selected = load_balancer.select_instance(instances)
        assert selected in instances

        # Test request tracking
        load_balancer.record_request_start(selected)
        stats = load_balancer.get_load_balancer_stats()
        assert stats["requests_per_instance"][selected.id] == 1

    def test_load_balancer_failover_behavior(self):
        """Test load balancer behavior during server failures."""
        lb = LoadBalancer(LoadBalancingStrategy.ROUND_ROBIN)

        # Start with healthy instances
        healthy_instances = [
            ServerInstance(
                id="server1", template_name="test", status=ServerStatus.HEALTHY
            ),
            ServerInstance(
                id="server2", template_name="test", status=ServerStatus.HEALTHY
            ),
        ]

        # Get an instance from healthy list
        selected1 = lb.select_instance(healthy_instances)
        assert selected1 is not None
        assert selected1 in healthy_instances

        # Simulate server failure - only one instance left
        failed_instances = [healthy_instances[1]]  # Only server2 remains

        # Should still get a valid instance
        selected2 = lb.select_instance(failed_instances)
        assert selected2 == failed_instances[0]

        # Simulate complete failure - no instances
        # Should return None when no instances available
        selected3 = lb.select_instance([])
        assert selected3 is None
