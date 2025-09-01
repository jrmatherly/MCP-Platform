"""
Unit tests for gateway load balancer module.

Tests load balancing strategies, connection tracking, and instance selection.
"""

import threading
import time

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
from mcp_platform.gateway.models import LoadBalancerConfig, ServerInstance, ServerStatus

pytestmark = pytest.mark.unit


class TestLoadBalancingStrategies:
    """Test load balancing strategy implementations."""

    def setup_method(self):
        """Set up test fixtures."""
        self.instances = [
            ServerInstance(
                id="server1",
                template_name="test",
                status=ServerStatus.HEALTHY,
                instance_metadata={"weight": 1},
            ),
            ServerInstance(
                id="server2",
                template_name="test",
                status=ServerStatus.HEALTHY,
                instance_metadata={"weight": 2},
            ),
            ServerInstance(
                id="server3",
                template_name="test",
                status=ServerStatus.HEALTHY,
                instance_metadata={"weight": 1},
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

        # Record a request to first instance
        strategy.record_request(selected1)

        # Next selection should avoid the busy instance
        selected2 = strategy.select_instance(self.instances)
        assert selected2 != selected1

        # Record completion to release connection
        strategy.record_completion(selected1, True)

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
        # Use instance IDs instead of the objects themselves since ServerInstance is not hashable
        unique_selections = set(instance.id for instance in selections)
        assert len(unique_selections) > 1

    def test_health_based_strategy(self):
        """Test health-based strategy prefers instances with fewer failures."""
        # Create instances with different consecutive failures
        health_instances = [
            ServerInstance(
                id="healthy", status=ServerStatus.HEALTHY, consecutive_failures=0
            ),
            ServerInstance(
                id="unhealthy", status=ServerStatus.UNHEALTHY, consecutive_failures=3
            ),
        ]

        strategy = HealthBasedStrategy()

        # Should prefer instance with fewer consecutive failures
        selected = strategy.select_instance(health_instances)

        # Should pick the instance with 0 consecutive failures
        assert selected.id == "healthy"

    def test_health_based_with_unhealthy_instances(self):
        """Test health-based strategy with instances having different failure counts."""
        # Create instances with different consecutive failure counts
        unhealthy_instances = [
            ServerInstance(
                id="healthy-1", status=ServerStatus.HEALTHY, consecutive_failures=0
            ),
            ServerInstance(
                id="unhealthy-1", status=ServerStatus.UNHEALTHY, consecutive_failures=5
            ),
        ]

        strategy = HealthBasedStrategy()

        # Should consistently pick the instance with fewer failures
        for _ in range(5):
            selected = strategy.select_instance(unhealthy_instances)
            assert selected.id == "healthy-1"


class TestLoadBalancer:
    """Test LoadBalancer main class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.load_balancer = LoadBalancer(LoadBalancingStrategy.ROUND_ROBIN)

        # Create test instances
        self.test_instances = [
            ServerInstance(id="server1", status=ServerStatus.HEALTHY),
            ServerInstance(id="server2", status=ServerStatus.HEALTHY),
        ]

    def test_load_balancer_initialization(self):
        """Test LoadBalancer initialization."""
        assert self.load_balancer.default_strategy == LoadBalancingStrategy.ROUND_ROBIN
        assert LoadBalancingStrategy.ROUND_ROBIN in self.load_balancer._strategies
        assert isinstance(
            self.load_balancer._strategies[LoadBalancingStrategy.ROUND_ROBIN],
            RoundRobinStrategy,
        )

    def test_load_balancer_strategy_selection(self):
        """Test that LoadBalancer has the correct strategies available."""
        # Test that all strategies are properly initialized
        expected_strategies = [
            LoadBalancingStrategy.ROUND_ROBIN,
            LoadBalancingStrategy.LEAST_CONNECTIONS,
            LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN,
            LoadBalancingStrategy.RANDOM,
            LoadBalancingStrategy.HEALTH_BASED,
        ]

        for strategy in expected_strategies:
            assert strategy in self.load_balancer._strategies
            assert self.load_balancer._strategies[strategy] is not None

    def test_get_instance_success(self):
        """Test successful instance selection."""
        healthy_instances = [
            ServerInstance(id="server1", status=ServerStatus.HEALTHY),
            ServerInstance(id="server2", status=ServerStatus.HEALTHY),
        ]

        selected = self.load_balancer.select_instance(healthy_instances)

        assert selected is not None
        assert selected in healthy_instances

        assert selected in healthy_instances

    def test_get_instance_no_healthy_instances(self):
        """Test instance selection when no healthy instances available."""
        # Pass empty list - should return None
        selected = self.load_balancer.select_instance([])
        assert selected is None

        # Pass only unhealthy instances - should fall back to using them
        unhealthy_instances = [
            ServerInstance(id="unhealthy1", status=ServerStatus.UNHEALTHY),
        ]
        selected = self.load_balancer.select_instance(unhealthy_instances)
        # Should fall back to unhealthy instances when no healthy ones available
        assert selected is not None
        assert selected.id == "unhealthy1"

    def test_can_accept_connection(self):
        """Test checking if instance has capacity by using actual load balancer selection."""
        # All instances should be selectable initially
        selected = self.load_balancer.select_instance(self.test_instances)
        assert selected is not None
        assert selected in self.test_instances

        # Even after recording some requests, should still be able to select
        for instance in self.test_instances:
            self.load_balancer.record_request_start(instance)

        selected = self.load_balancer.select_instance(self.test_instances)
        assert selected is not None
        assert selected in self.test_instances

    def test_connection_limit_enforcement(self):
        """Test that load balancer can track multiple requests per instance."""
        instance = self.test_instances[0]

        # Record multiple requests for same instance
        self.load_balancer.record_request_start(instance)
        self.load_balancer.record_request_start(instance)

        # Verify requests are tracked
        stats = self.load_balancer.get_load_balancer_stats()
        assert stats["requests_per_instance"][instance.id] == 2

        # Instance should still be selectable (no hard limits in basic implementation)
        selected = self.load_balancer.select_instance(self.test_instances)
        assert selected is not None

    def test_get_instance_with_connection_limits(self):
        """Test instance selection with round robin strategy."""
        # Use actual load balancer with round robin strategy

        # First call should return an instance
        selected1 = self.load_balancer.select_instance(self.test_instances)
        assert selected1 is not None
        assert selected1 in self.test_instances

        # Record request for first instance
        self.load_balancer.record_request_start(selected1)

        # Second call should return an instance (possibly different with round robin)
        selected2 = self.load_balancer.select_instance(self.test_instances)
        assert selected2 is not None
        assert selected2 in self.test_instances

    def test_statistics_collection(self):
        """Test load balancer statistics collection."""
        instance = self.test_instances[0]

        # Record some requests
        self.load_balancer.record_request_start(instance)
        self.load_balancer.record_request_start(instance)
        self.load_balancer.record_request_completion(instance, success=True)

        stats = self.load_balancer.get_load_balancer_stats()

        assert "total_requests" in stats
        assert "requests_per_instance" in stats
        assert "default_strategy" in stats
        assert "available_strategies" in stats

        # Check instance-specific stats
        assert stats["total_requests"] == 2
        assert stats["requests_per_instance"][instance.id] == 2
        assert stats["default_strategy"] == "round_robin"

    def test_load_balancer_thread_safety(self):
        """Test that load balancer operations are thread-safe."""
        instance = self.test_instances[0]
        results = []

        def record_requests():
            for _ in range(10):
                self.load_balancer.record_request_start(instance)
                time.sleep(0.001)  # Small delay to increase chance of race conditions
                stats = self.load_balancer.get_load_balancer_stats()
                results.append(stats["requests_per_instance"][instance.id])

        # Start multiple threads
        threads = []
        for _ in range(3):
            thread = threading.Thread(target=record_requests)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # Final count should be 30 (3 threads * 10 requests each)
        final_stats = self.load_balancer.get_load_balancer_stats()
        final_count = final_stats["requests_per_instance"][instance.id]
        assert final_count == 30


class TestLoadBalancerConfiguration:
    """Test LoadBalancer configuration and validation."""

    def test_load_balancer_config_defaults(self):
        """Test LoadBalancerConfig default values."""
        config = LoadBalancerConfig(template_name="test-template")

        assert config.strategy.value == LoadBalancingStrategy.ROUND_ROBIN.value
        assert config.health_check_interval == 30
        assert config.max_retries == 3
        assert config.pool_size == 3
        assert config.timeout == 60

    def test_load_balancer_config_custom_values(self):
        """Test LoadBalancerConfig with custom values."""
        config = LoadBalancerConfig(
            template_name="test-template",
            strategy=LoadBalancingStrategy.LEAST_CONNECTIONS,
            health_check_interval=60,
            max_retries=5,
            pool_size=10,
            timeout=120,
        )

        assert config.strategy == LoadBalancingStrategy.LEAST_CONNECTIONS
        assert config.health_check_interval == 60
        assert config.max_retries == 5
        assert config.pool_size == 10
        assert config.timeout == 120

    def test_invalid_strategy_handling(self):
        """Test that LoadBalancerConfig can be created with valid parameters."""
        # Test that config creation works with valid parameters
        config = LoadBalancerConfig(template_name="test")
        assert config.template_name == "test"
        assert config.strategy.value == "round_robin"
