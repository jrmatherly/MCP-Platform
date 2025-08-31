"""
Unit tests for gateway load balancer.

Tests load balancing strategies, connection tracking, and instance selection.
"""

import time
from typing import List
from unittest.mock import Mock, patch

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
from mcp_platform.gateway.models import LoadBalancerConfig
from mcp_platform.gateway.registry import ServerInstance


class TestLoadBalancingStrategies:
    """Test load balancing strategy implementations."""

    def setup_method(self):
        """Set up test fixtures."""
        self.instances = [
            ServerInstance(
                id=1,
                name="server1",
                host="localhost",
                port=8001,
                status="running",
                health_score=0.9,
                weight=1,
            ),
            ServerInstance(
                id=2,
                name="server2",
                host="localhost",
                port=8002,
                status="running",
                health_score=0.8,
                weight=2,
            ),
            ServerInstance(
                id=3,
                name="server3",
                host="localhost",
                port=8003,
                status="running",
                health_score=0.7,
                weight=1,
            ),
        ]

    def test_load_balancing_strategy_enum(self):
        """Test LoadBalancingStrategy enum values."""
        strategies = LoadBalancingStrategy

        assert strategies.ROUND_ROBIN.value == "round_robin"
        assert strategies.LEAST_CONNECTIONS.value == "least_connections"
        assert strategies.WEIGHTED_ROUND_ROBIN.value == "weighted"
        assert strategies.HEALTH_BASED.value == "health_based"
        assert strategies.RANDOM.value == "random"

    def test_base_strategy_abstract(self):
        """Test that BaseBalancingStrategy cannot be instantiated."""
        with pytest.raises(TypeError):
            BaseBalancingStrategy("test")

    def test_round_robin_strategy(self):
        """Test round robin strategy implementation."""
        strategy = RoundRobinStrategy()

        # Test sequential selection
        selected1 = strategy.select_instance(self.instances)
        selected2 = strategy.select_instance(self.instances)
        selected3 = strategy.select_instance(self.instances)
        selected4 = strategy.select_instance(self.instances)

        # Should cycle through instances
        assert selected1 == self.instances[0]
        assert selected2 == self.instances[1]
        assert selected3 == self.instances[2]
        assert selected4 == self.instances[0]  # Back to first

    def test_round_robin_empty_list(self):
        """Test round robin with empty instance list."""
        strategy = RoundRobinStrategy()

        result = strategy.select_instance([])
        assert result is None

    def test_least_connections_strategy(self):
        """Test least connections strategy."""
        strategy = LeastConnectionsStrategy()

        # All instances start with 0 connections
        selected1 = strategy.select_instance(self.instances)
        assert selected1 in self.instances

        # Track a connection to first instance
        strategy.track_connection(selected1)

        # Next selection should avoid the busy instance
        selected2 = strategy.select_instance(self.instances)
        assert selected2 != selected1

        # Release connection
        strategy.release_connection(selected1)

    def test_weighted_round_robin_strategy(self):
        """Test weighted round robin strategy."""
        strategy = WeightedRoundRobinStrategy()

        # Track selections to verify weight distribution
        selections = []
        for _ in range(8):  # Total weight = 4, so 8 selections = 2 cycles
            selected = strategy.select_instance(self.instances)
            selections.append(selected)

        # Server2 has weight 2, should appear twice as often
        server1_count = selections.count(self.instances[0])  # weight 1
        server2_count = selections.count(self.instances[1])  # weight 2
        server3_count = selections.count(self.instances[2])  # weight 1

        # In 2 cycles: server1=2, server2=4, server3=2
        assert server1_count == 2
        assert server2_count == 4
        assert server3_count == 2

    def test_random_strategy(self):
        """Test random strategy."""
        strategy = RandomStrategy()

        # Test multiple selections
        selections = []
        for _ in range(10):
            selected = strategy.select_instance(self.instances)
            selections.append(selected)

        # All selections should be from our instances
        assert all(instance in self.instances for instance in selections)

        # With random, we should get different instances (high probability)
        unique_selections = set(selections)
        assert len(unique_selections) > 1

    def test_health_based_strategy(self):
        """Test health-based strategy."""
        strategy = HealthBasedStrategy()

        # Should prefer higher health score instances
        selected = strategy.select_instance(self.instances)

        # First instance has highest health score (0.9)
        assert selected == self.instances[0]

    def test_health_based_with_unhealthy_instances(self):
        """Test health-based strategy with some unhealthy instances."""
        # Create instances with different health scores
        unhealthy_instances = [
            ServerInstance(id=1, name="healthy", health_score=0.9, status="running"),
            ServerInstance(id=2, name="unhealthy", health_score=0.1, status="running"),
        ]

        strategy = HealthBasedStrategy()

        # Should consistently pick the healthy instance
        for _ in range(5):
            selected = strategy.select_instance(unhealthy_instances)
            assert selected.name == "healthy"


class TestLoadBalancer:
    """Test LoadBalancer main class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.config = LoadBalancerConfig(
            strategy=LoadBalancingStrategy.ROUND_ROBIN,
            health_check_interval=30,
            max_connections_per_instance=100,
        )
        self.load_balancer = LoadBalancer(self.config)

        self.mock_registry = Mock()
        self.load_balancer.registry = self.mock_registry

    def test_load_balancer_initialization(self):
        """Test LoadBalancer initialization."""
        assert self.load_balancer.config == self.config
        assert isinstance(self.load_balancer.strategy, RoundRobinStrategy)
        assert self.load_balancer.connection_counts == {}

    def test_load_balancer_strategy_selection(self):
        """Test that LoadBalancer selects the correct strategy."""
        # Test different strategies
        configs_and_types = [
            (LoadBalancingStrategy.ROUND_ROBIN, RoundRobinStrategy),
            (LoadBalancingStrategy.LEAST_CONNECTIONS, LeastConnectionsStrategy),
            (LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN, WeightedRoundRobinStrategy),
            (LoadBalancingStrategy.RANDOM, RandomStrategy),
            (LoadBalancingStrategy.HEALTH_BASED, HealthBasedStrategy),
        ]

        for strategy_enum, strategy_class in configs_and_types:
            config = LoadBalancerConfig(strategy=strategy_enum)
            lb = LoadBalancer(config)
            assert isinstance(lb.strategy, strategy_class)

    def test_get_instance_success(self):
        """Test successful instance selection."""
        healthy_instances = [
            ServerInstance(id=1, name="server1", status="running"),
            ServerInstance(id=2, name="server2", status="running"),
        ]

        self.mock_registry.get_healthy_instances.return_value = healthy_instances

        selected = self.load_balancer.get_instance()

        assert selected in healthy_instances
        self.mock_registry.get_healthy_instances.assert_called_once()

    def test_get_instance_no_healthy_instances(self):
        """Test instance selection when no healthy instances available."""
        self.mock_registry.get_healthy_instances.return_value = []

        selected = self.load_balancer.get_instance()

        assert selected is None

    def test_connection_tracking(self):
        """Test connection tracking functionality."""
        instance = ServerInstance(id=1, name="test", status="running")

        # Initially no connections
        assert self.load_balancer.get_connection_count(instance) == 0

        # Track a connection
        self.load_balancer.track_connection(instance)
        assert self.load_balancer.get_connection_count(instance) == 1

        # Track another connection
        self.load_balancer.track_connection(instance)
        assert self.load_balancer.get_connection_count(instance) == 2

        # Release a connection
        self.load_balancer.release_connection(instance)
        assert self.load_balancer.get_connection_count(instance) == 1

        # Release another connection
        self.load_balancer.release_connection(instance)
        assert self.load_balancer.get_connection_count(instance) == 0

    def test_connection_limit_enforcement(self):
        """Test that connection limits are enforced."""
        config = LoadBalancerConfig(
            strategy=LoadBalancingStrategy.ROUND_ROBIN, max_connections_per_instance=2
        )
        lb = LoadBalancer(config)

        instance = ServerInstance(id=1, name="test", status="running")

        # First two connections should succeed
        assert lb.can_accept_connection(instance) is True
        lb.track_connection(instance)

        assert lb.can_accept_connection(instance) is True
        lb.track_connection(instance)

        # Third connection should be rejected
        assert lb.can_accept_connection(instance) is False

    def test_get_instance_with_connection_limits(self):
        """Test instance selection respects connection limits."""
        config = LoadBalancerConfig(
            strategy=LoadBalancingStrategy.ROUND_ROBIN, max_connections_per_instance=1
        )
        lb = LoadBalancer(config)
        lb.registry = self.mock_registry

        instances = [
            ServerInstance(id=1, name="server1", status="running"),
            ServerInstance(id=2, name="server2", status="running"),
        ]

        self.mock_registry.get_healthy_instances.return_value = instances

        # First call should return an instance
        selected1 = lb.get_instance()
        assert selected1 is not None

        # Max out connections on first instance
        lb.track_connection(selected1)

        # Second call should return the other instance
        selected2 = lb.get_instance()
        assert selected2 is not None
        assert selected2 != selected1

    def test_statistics_collection(self):
        """Test load balancer statistics collection."""
        instance = ServerInstance(id=1, name="test", status="running")

        # Track some connections
        self.load_balancer.track_connection(instance)
        self.load_balancer.track_connection(instance)
        self.load_balancer.release_connection(instance)

        stats = self.load_balancer.get_statistics()

        assert "total_requests" in stats
        assert "active_connections" in stats
        assert "instance_stats" in stats

        # Check instance-specific stats
        instance_stats = stats["instance_stats"]
        assert str(instance.id) in instance_stats
        assert instance_stats[str(instance.id)]["active_connections"] == 1

    def test_load_balancer_thread_safety(self):
        """Test that load balancer operations are thread-safe."""
        import threading
        import time

        instance = ServerInstance(id=1, name="test", status="running")
        results = []

        def track_connections():
            for _ in range(10):
                self.load_balancer.track_connection(instance)
                time.sleep(0.001)  # Small delay to increase chance of race conditions
                results.append(self.load_balancer.get_connection_count(instance))

        # Start multiple threads
        threads = []
        for _ in range(3):
            thread = threading.Thread(target=track_connections)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Final count should be 30 (3 threads * 10 connections each)
        final_count = self.load_balancer.get_connection_count(instance)
        assert final_count == 30


class TestLoadBalancerConfiguration:
    """Test LoadBalancer configuration and validation."""

    def test_load_balancer_config_defaults(self):
        """Test LoadBalancerConfig default values."""
        config = LoadBalancerConfig()

        assert config.strategy == LoadBalancingStrategy.ROUND_ROBIN
        assert config.health_check_interval == 30
        assert config.max_connections_per_instance == 100

    def test_load_balancer_config_custom_values(self):
        """Test LoadBalancerConfig with custom values."""
        config = LoadBalancerConfig(
            strategy=LoadBalancingStrategy.LEAST_CONNECTIONS,
            health_check_interval=60,
            max_connections_per_instance=50,
        )

        assert config.strategy == LoadBalancingStrategy.LEAST_CONNECTIONS
        assert config.health_check_interval == 60
        assert config.max_connections_per_instance == 50

    def test_invalid_strategy_handling(self):
        """Test handling of invalid strategy configuration."""
        # This should be caught by pydantic validation
        with pytest.raises(ValueError):
            LoadBalancerConfig(strategy="invalid_strategy")


class TestLoadBalancerIntegration:
    """Test load balancer integration scenarios."""

    def test_load_balancer_with_registry_integration(self):
        """Test load balancer working with server registry."""
        from mcp_platform.gateway.registry import ServerRegistry

        # Create real registry and load balancer
        registry = ServerRegistry()
        config = LoadBalancerConfig(strategy=LoadBalancingStrategy.ROUND_ROBIN)
        load_balancer = LoadBalancer(config)
        load_balancer.registry = registry

        # Add some test instances to registry
        instance1 = ServerInstance(id=1, name="server1", status="running")
        instance2 = ServerInstance(id=2, name="server2", status="running")

        # Mock the registry methods
        with patch.object(registry, "get_healthy_instances") as mock_healthy:
            mock_healthy.return_value = [instance1, instance2]

            # Test instance selection
            selected = load_balancer.get_instance()
            assert selected in [instance1, instance2]

            # Test connection tracking
            load_balancer.track_connection(selected)
            assert load_balancer.get_connection_count(selected) == 1

    def test_load_balancer_failover_behavior(self):
        """Test load balancer behavior during server failures."""
        config = LoadBalancerConfig(strategy=LoadBalancingStrategy.ROUND_ROBIN)
        lb = LoadBalancer(config)
        lb.registry = Mock()

        # Start with healthy instances
        healthy_instances = [
            ServerInstance(id=1, name="server1", status="running"),
            ServerInstance(id=2, name="server2", status="running"),
        ]
        lb.registry.get_healthy_instances.return_value = healthy_instances

        # Get an instance
        selected1 = lb.get_instance()
        assert selected1 is not None

        # Simulate server failure - only one instance left
        failed_instances = [healthy_instances[1]]  # Only server2 remains
        lb.registry.get_healthy_instances.return_value = failed_instances

        # Should still get a valid instance
        selected2 = lb.get_instance()
        assert selected2 == failed_instances[0]

        # Simulate complete failure
        lb.registry.get_healthy_instances.return_value = []

        # Should return None when no instances available
        selected3 = lb.get_instance()
        assert selected3 is None
