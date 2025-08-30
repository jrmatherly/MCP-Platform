"""
Unit tests for gateway load balancer.
"""

import time
from unittest.mock import Mock

import pytest

from mcp_platform.gateway.load_balancer import (
    BaseBalancingStrategy,
    HealthBasedStrategy,
    LeastConnectionsStrategy,
    LoadBalancer,
    LoadBalancingStrategy,
    RandomStrategy,
    RoundRobinStrategy,
    WeightedRoundRobinStrategy,
)
from mcp_platform.gateway.registry import ServerInstance

pytestmark = pytest.mark.unit


class TestRoundRobinStrategy:
    """Unit tests for round-robin load balancing strategy."""

    def test_round_robin_selection(self):
        """Test round-robin instance selection."""
        strategy = RoundRobinStrategy()

        instances = [
            ServerInstance(id="inst-1", template_name="demo"),
            ServerInstance(id="inst-2", template_name="demo"),
            ServerInstance(id="inst-3", template_name="demo"),
        ]

        # Should cycle through instances
        selected1 = strategy.select_instance(instances)
        selected2 = strategy.select_instance(instances)
        selected3 = strategy.select_instance(instances)
        selected4 = strategy.select_instance(instances)

        assert selected1.id == "inst-1"
        assert selected2.id == "inst-2"
        assert selected3.id == "inst-3"
        assert selected4.id == "inst-1"  # Back to first

    def test_round_robin_empty_list(self):
        """Test round-robin with empty instance list."""
        strategy = RoundRobinStrategy()
        assert strategy.select_instance([]) is None

    def test_round_robin_single_instance(self):
        """Test round-robin with single instance."""
        strategy = RoundRobinStrategy()
        instance = ServerInstance(id="single", template_name="demo")

        # Should always return the same instance
        assert strategy.select_instance([instance]) == instance
        assert strategy.select_instance([instance]) == instance

    def test_round_robin_separate_templates(self):
        """Test round-robin maintains separate counters per template."""
        strategy = RoundRobinStrategy()

        demo_instances = [
            ServerInstance(id="demo-1", template_name="demo"),
            ServerInstance(id="demo-2", template_name="demo"),
        ]

        fs_instances = [
            ServerInstance(id="fs-1", template_name="filesystem"),
            ServerInstance(id="fs-2", template_name="filesystem"),
        ]

        # Select from demo template
        demo_selected1 = strategy.select_instance(demo_instances)
        demo_selected2 = strategy.select_instance(demo_instances)

        # Select from filesystem template
        fs_selected1 = strategy.select_instance(fs_instances)
        fs_selected2 = strategy.select_instance(fs_instances)

        # Each template should have its own counter
        assert demo_selected1.id == "demo-1"
        assert demo_selected2.id == "demo-2"
        assert fs_selected1.id == "fs-1"
        assert fs_selected2.id == "fs-2"


class TestLeastConnectionsStrategy:
    """Unit tests for least connections load balancing strategy."""

    def test_least_connections_selection(self):
        """Test least connections instance selection."""
        strategy = LeastConnectionsStrategy()

        instances = [
            ServerInstance(id="inst-1", template_name="demo"),
            ServerInstance(id="inst-2", template_name="demo"),
            ServerInstance(id="inst-3", template_name="demo"),
        ]

        # Initially all have 0 connections, should select first
        selected = strategy.select_instance(instances)
        assert selected.id == "inst-1"

        # Record request for inst-1
        strategy.record_request(selected)

        # Now inst-2 and inst-3 have fewer connections
        selected = strategy.select_instance(instances)
        assert selected.id == "inst-2"

        # Record request for inst-2
        strategy.record_request(selected)

        # Now inst-3 has fewest connections
        selected = strategy.select_instance(instances)
        assert selected.id == "inst-3"

    def test_least_connections_completion(self):
        """Test connection tracking with completion."""
        strategy = LeastConnectionsStrategy()
        instance = ServerInstance(id="test", template_name="demo")

        # Record request
        strategy.record_request(instance)
        assert strategy._active_connections[instance.id] == 1

        # Record completion
        strategy.record_completion(instance, True)
        assert strategy._active_connections[instance.id] == 0

        # Multiple requests
        strategy.record_request(instance)
        strategy.record_request(instance)
        assert strategy._active_connections[instance.id] == 2

        # One completion
        strategy.record_completion(instance, False)
        assert strategy._active_connections[instance.id] == 1


class TestWeightedRoundRobinStrategy:
    """Unit tests for weighted round-robin load balancing strategy."""

    def test_weighted_selection(self):
        """Test weighted round-robin selection."""
        strategy = WeightedRoundRobinStrategy()

        instances = [
            ServerInstance(
                id="heavy",
                template_name="demo",
                transport="http",
                backend="docker",
                endpoint="http://localhost:8001",
                metadata={"weight": 3},
            ),
            ServerInstance(
                id="light",
                template_name="demo",
                transport="http",
                backend="docker",
                endpoint="http://localhost:8002",
                metadata={"weight": 1},
            ),
        ]

        # Select multiple times and count
        selections = []
        for i in range(8):  # Total weight is 4, so 8 selections = 2 cycles
            selected = strategy.select_instance(instances)
            if selected:  # Check if selection is not None
                selections.append(selected.id)

        # Heavy instance should appear more often than light instance
        heavy_count = selections.count("heavy")
        light_count = selections.count("light")

        # With weights 3:1, heavy should appear 3 times for every 1 time light appears
        # In 8 selections, we expect: heavy=6, light=2
        assert heavy_count == 6
        assert light_count == 2
        assert len(selections) == 8  # All selections should be valid
        assert light_count == 2  # 1 per cycle * 2 cycles

    def test_weighted_no_metadata(self):
        """Test weighted strategy with instances without weight metadata."""
        strategy = WeightedRoundRobinStrategy()

        instances = [
            ServerInstance(id="no-weight", template_name="demo"),
            ServerInstance(id="also-no-weight", template_name="demo"),
        ]

        # Should work like normal round-robin (default weight = 1)
        selected1 = strategy.select_instance(instances)
        selected2 = strategy.select_instance(instances)

        assert selected1.id != selected2.id


class TestHealthBasedStrategy:
    """Unit tests for health-based load balancing strategy."""

    def test_health_based_selection(self):
        """Test health-based selection prefers healthier instances."""
        strategy = HealthBasedStrategy()

        # Create instances with different health states
        healthy = ServerInstance(id="healthy", template_name="demo")
        healthy.consecutive_failures = 0

        failing = ServerInstance(id="failing", template_name="demo")
        failing.consecutive_failures = 2

        instances = [failing, healthy]  # Deliberately put failing first

        # Should select healthy instance despite order
        selected = strategy.select_instance(instances)
        assert selected.id == "healthy"

    def test_health_based_failure_tracking(self):
        """Test health-based strategy tracks failures."""
        strategy = HealthBasedStrategy()
        instance = ServerInstance(id="test", template_name="demo")

        # Initially no recent failures
        assert strategy._failure_counts[instance.id] == 0

        # Record failed completion
        strategy.record_completion(instance, False)
        assert strategy._failure_counts[instance.id] == 1

        # Record successful completion (no change in recent failures)
        strategy.record_completion(instance, True)
        assert strategy._failure_counts[instance.id] == 1

        # Record another failure
        strategy.record_completion(instance, False)
        assert strategy._failure_counts[instance.id] == 2


class TestRandomStrategy:
    """Unit tests for random load balancing strategy."""

    def test_random_selection(self):
        """Test random instance selection."""
        strategy = RandomStrategy()

        instances = [
            ServerInstance(id="inst-1", template_name="demo"),
            ServerInstance(id="inst-2", template_name="demo"),
            ServerInstance(id="inst-3", template_name="demo"),
        ]

        # Should always return an instance from the list
        for _ in range(10):
            selected = strategy.select_instance(instances)
            assert selected in instances

    def test_random_empty_list(self):
        """Test random selection with empty list."""
        strategy = RandomStrategy()
        assert strategy.select_instance([]) is None


class TestLoadBalancer:
    """Unit tests for main LoadBalancer class."""

    def test_load_balancer_initialization(self):
        """Test load balancer initialization."""
        lb = LoadBalancer()

        assert lb.default_strategy == LoadBalancingStrategy.ROUND_ROBIN
        assert len(lb._strategies) == 5  # All available strategies
        assert LoadBalancingStrategy.ROUND_ROBIN in lb._strategies
        assert LoadBalancingStrategy.LEAST_CONNECTIONS in lb._strategies

    def test_load_balancer_custom_default(self):
        """Test load balancer with custom default strategy."""
        lb = LoadBalancer(default_strategy=LoadBalancingStrategy.LEAST_CONNECTIONS)
        assert lb.default_strategy == LoadBalancingStrategy.LEAST_CONNECTIONS

    def test_select_instance_healthy_only(self):
        """Test instance selection filters to healthy instances."""
        lb = LoadBalancer()

        healthy = ServerInstance(id="healthy", template_name="demo")
        healthy.update_health_status(True)

        unhealthy = ServerInstance(id="unhealthy", template_name="demo")
        unhealthy.update_health_status(False)

        instances = [unhealthy, healthy]

        # Should select healthy instance only
        selected = lb.select_instance(instances)
        assert selected.id == "healthy"

    def test_select_instance_fallback_to_all(self):
        """Test instance selection falls back to all instances if none healthy."""
        lb = LoadBalancer()

        unhealthy1 = ServerInstance(id="unhealthy-1", template_name="demo")
        unhealthy1.update_health_status(False)

        unhealthy2 = ServerInstance(id="unhealthy-2", template_name="demo")
        unhealthy2.update_health_status(False)

        instances = [unhealthy1, unhealthy2]

        # Should fall back to selecting from all instances
        selected = lb.select_instance(instances)
        assert selected in instances

    def test_select_instance_custom_strategy(self):
        """Test instance selection with custom strategy."""
        lb = LoadBalancer()

        instances = [
            ServerInstance(id="inst-1", template_name="demo"),
            ServerInstance(id="inst-2", template_name="demo"),
        ]

        # Select with least connections strategy
        selected = lb.select_instance(
            instances, LoadBalancingStrategy.LEAST_CONNECTIONS
        )
        assert selected in instances

    def test_request_tracking(self):
        """Test request start and completion tracking."""
        lb = LoadBalancer()
        instance = ServerInstance(id="test", template_name="demo")

        # Record request start
        lb.record_request_start(instance)
        assert lb._request_count[instance.id] == 1

        # Record completion
        lb.record_request_completion(instance, True)

        # Another request
        lb.record_request_start(instance)
        assert lb._request_count[instance.id] == 2

    def test_load_balancer_stats(self):
        """Test load balancer statistics."""
        lb = LoadBalancer()
        instance = ServerInstance(id="test", template_name="demo")

        # Initial stats
        stats = lb.get_load_balancer_stats()
        assert stats["default_strategy"] == "round_robin"
        assert stats["total_requests"] == 0
        assert len(stats["available_strategies"]) == 5

        # After some requests
        lb.record_request_start(instance)
        lb.record_request_start(instance)

        stats = lb.get_load_balancer_stats()
        assert stats["total_requests"] == 2
        assert instance.id in stats["requests_per_instance"]
        assert stats["requests_per_instance"][instance.id] == 2

    def test_reset_stats(self):
        """Test resetting load balancer statistics."""
        lb = LoadBalancer()
        instance = ServerInstance(id="test", template_name="demo")

        # Generate some stats
        lb.record_request_start(instance)
        assert lb._request_count[instance.id] == 1

        # Reset
        lb.reset_stats()
        assert lb._request_count[instance.id] == 0

        stats = lb.get_load_balancer_stats()
        assert stats["total_requests"] == 0

    def test_unknown_strategy_fallback(self):
        """Test fallback to round-robin for unknown strategy."""
        lb = LoadBalancer()

        # Mock an unknown strategy
        unknown_strategy = Mock()
        unknown_strategy.value = "unknown_strategy"

        instances = [ServerInstance(id="test", template_name="demo")]

        # Should fall back to round-robin
        selected = lb.select_instance(instances, unknown_strategy)
        assert selected is not None
