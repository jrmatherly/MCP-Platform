"""
Load Balancer for MCP Gateway.

Implements multiple load balancing strategies for distributing requests
across MCP server instances with health awareness and connection tracking.
"""

import logging
import random
import threading
import time
from abc import ABC, abstractmethod
from collections import defaultdict
from enum import Enum
from typing import Dict, List, Optional

from .registry import ServerInstance

logger = logging.getLogger(__name__)


class LoadBalancingStrategy(Enum):
    """Available load balancing strategies."""

    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED_ROUND_ROBIN = "weighted"
    HEALTH_BASED = "health_based"
    RANDOM = "random"


class BaseBalancingStrategy(ABC):
    """Base class for load balancing strategies."""

    def __init__(self, name: str):
        self.name = name
        self._lock = threading.RLock()

    @abstractmethod
    def select_instance(
        self, instances: List[ServerInstance]
    ) -> Optional[ServerInstance]:
        """
        Select a server instance from the available instances.

        Args:
            instances: List of available healthy server instances

        Returns:
            Selected server instance or None if no instances available
        """
        pass

    @abstractmethod
    def record_request(self, instance: ServerInstance):
        """Record that a request was sent to an instance."""
        pass

    @abstractmethod
    def record_completion(self, instance: ServerInstance, success: bool):
        """Record that a request completed (successfully or not)."""
        pass


class RoundRobinStrategy(BaseBalancingStrategy):
    """Round-robin load balancing strategy."""

    def __init__(self):
        super().__init__("round_robin")
        self._counters: Dict[str, int] = defaultdict(int)  # template_name -> counter

    def select_instance(
        self, instances: List[ServerInstance]
    ) -> Optional[ServerInstance]:
        if not instances:
            return None

        with self._lock:
            # Use template name to maintain separate counters per template
            template_name = instances[0].template_name
            counter = self._counters[template_name]
            selected = instances[counter % len(instances)]
            self._counters[template_name] = (counter + 1) % len(instances)
            return selected

    def record_request(self, instance: ServerInstance):
        # No tracking needed for round-robin
        pass

    def record_completion(self, instance: ServerInstance, success: bool):
        # No tracking needed for round-robin
        pass


class LeastConnectionsStrategy(BaseBalancingStrategy):
    """Least connections load balancing strategy."""

    def __init__(self):
        super().__init__("least_connections")
        self._active_connections: Dict[str, int] = defaultdict(
            int
        )  # instance_id -> count

    def select_instance(
        self, instances: List[ServerInstance]
    ) -> Optional[ServerInstance]:
        if not instances:
            return None

        with self._lock:
            # Find instance with least active connections
            min_connections = float("inf")
            selected = None

            for instance in instances:
                connections = self._active_connections[instance.id]
                if connections < min_connections:
                    min_connections = connections
                    selected = instance

            return selected

    def record_request(self, instance: ServerInstance):
        with self._lock:
            self._active_connections[instance.id] += 1

    def record_completion(self, instance: ServerInstance, success: bool):
        with self._lock:
            if self._active_connections[instance.id] > 0:
                self._active_connections[instance.id] -= 1


class WeightedRoundRobinStrategy(BaseBalancingStrategy):
    """Weighted round-robin load balancing strategy."""

    def __init__(self):
        super().__init__("weighted")
        self._current_weights: Dict[str, int] = defaultdict(
            int
        )  # template_name -> counter

    def _get_instance_weight(self, instance: ServerInstance) -> int:
        """Get weight for an instance from metadata."""
        if not instance.instance_metadata:
            return 1
        return instance.instance_metadata.get("weight", 1)

    def select_instance(
        self, instances: List[ServerInstance]
    ) -> Optional[ServerInstance]:
        if not instances:
            return None

        with self._lock:
            # Simple weighted round-robin: select based on weight ratio
            total_weight = sum(self._get_instance_weight(inst) for inst in instances)
            if total_weight == 0:
                return instances[0]  # Fallback to first instance

            # Build a list where each instance appears proportional to its weight
            weighted_instances = []
            for instance in instances:
                weight = self._get_instance_weight(instance)
                weighted_instances.extend([instance] * weight)

            if not weighted_instances:
                return instances[0]  # Fallback

            # Use template-specific counter for round-robin within weighted list
            template_name = instances[0].template_name
            counter = self._current_weights.get(template_name, 0)
            selected = weighted_instances[counter % len(weighted_instances)]
            self._current_weights[template_name] = (counter + 1) % len(
                weighted_instances
            )

            return selected

    def record_request(self, instance: ServerInstance):
        # Weight-based selection doesn't need request tracking
        pass

    def record_completion(self, instance: ServerInstance, success: bool):
        # Weight-based selection doesn't need completion tracking
        pass


class HealthBasedStrategy(BaseBalancingStrategy):
    """Health-based load balancing with preference for healthiest instances."""

    def __init__(self):
        super().__init__("health_based")
        self._failure_counts: Dict[str, int] = defaultdict(
            int
        )  # instance_id -> recent_failures
        self._last_cleanup = time.time()

    def select_instance(
        self, instances: List[ServerInstance]
    ) -> Optional[ServerInstance]:
        if not instances:
            return None

        with self._lock:
            self._cleanup_old_failures()

            # Sort by health score (lower failure count = better)
            instances_by_health = sorted(
                instances,
                key=lambda inst: (
                    inst.consecutive_failures,  # Primary: total consecutive failures
                    self._failure_counts[inst.id],  # Secondary: recent failures
                    random.random(),  # Tertiary: random for tie-breaking
                ),
            )

            return instances_by_health[0]

    def record_request(self, instance: ServerInstance):
        # Health-based doesn't track requests, only outcomes
        pass

    def record_completion(self, instance: ServerInstance, success: bool):
        if not success:
            with self._lock:
                self._failure_counts[instance.id] += 1

    def _cleanup_old_failures(self):
        """Reset failure counts periodically."""
        now = time.time()
        if now - self._last_cleanup > 300:  # 5 minutes
            self._failure_counts.clear()
            self._last_cleanup = now


class RandomStrategy(BaseBalancingStrategy):
    """Random load balancing strategy."""

    def __init__(self):
        super().__init__("random")

    def select_instance(
        self, instances: List[ServerInstance]
    ) -> Optional[ServerInstance]:
        if not instances:
            return None
        return random.choice(instances)

    def record_request(self, instance: ServerInstance):
        # Random selection doesn't need tracking
        pass

    def record_completion(self, instance: ServerInstance, success: bool):
        # Random selection doesn't need tracking
        pass


class LoadBalancer:
    """
    Main load balancer that manages multiple strategies and server selection.

    Provides health-aware load balancing with configurable strategies
    and automatic failover capabilities.
    """

    def __init__(
        self,
        default_strategy: LoadBalancingStrategy = LoadBalancingStrategy.ROUND_ROBIN,
    ):
        """
        Initialize load balancer.

        Args:
            default_strategy: Default load balancing strategy to use
        """
        self.default_strategy = default_strategy
        self._strategies: Dict[LoadBalancingStrategy, BaseBalancingStrategy] = {
            LoadBalancingStrategy.ROUND_ROBIN: RoundRobinStrategy(),
            LoadBalancingStrategy.LEAST_CONNECTIONS: LeastConnectionsStrategy(),
            LoadBalancingStrategy.WEIGHTED_ROUND_ROBIN: WeightedRoundRobinStrategy(),
            LoadBalancingStrategy.HEALTH_BASED: HealthBasedStrategy(),
            LoadBalancingStrategy.RANDOM: RandomStrategy(),
        }

        # Request tracking
        self._request_count: Dict[str, int] = defaultdict(
            int
        )  # instance_id -> request_count
        self._lock = threading.RLock()

    def select_instance(
        self,
        instances: List[ServerInstance],
        strategy: Optional[LoadBalancingStrategy] = None,
    ) -> Optional[ServerInstance]:
        """
        Select an instance using the specified strategy.

        Args:
            instances: List of available server instances
            strategy: Load balancing strategy to use (defaults to configured strategy)

        Returns:
            Selected server instance or None if no healthy instances available
        """
        if not instances:
            logger.warning("No instances available for load balancing")
            return None

        # Filter to only healthy instances
        healthy_instances = [inst for inst in instances if inst.is_healthy()]
        if not healthy_instances:
            logger.warning(
                "No healthy instances available, falling back to all instances"
            )
            healthy_instances = instances  # Fallback to all if none are healthy

        # Use specified strategy or default
        strategy = strategy or self.default_strategy
        balancing_strategy = self._strategies.get(strategy)

        if not balancing_strategy:
            logger.error(f"Unknown load balancing strategy: {strategy}")
            balancing_strategy = self._strategies[LoadBalancingStrategy.ROUND_ROBIN]

        selected = balancing_strategy.select_instance(healthy_instances)

        if selected:
            logger.debug(
                f"Selected instance {selected.id} using {strategy.value} strategy "
                f"from {len(healthy_instances)} healthy instances"
            )
        else:
            logger.warning("Load balancer failed to select any instance")

        return selected

    def record_request_start(
        self, instance: ServerInstance, strategy: Optional[LoadBalancingStrategy] = None
    ):
        """
        Record that a request is starting for an instance.

        Args:
            instance: Server instance handling the request
            strategy: Strategy used for selection
        """
        with self._lock:
            self._request_count[instance.id] += 1

        # Notify strategy
        strategy = strategy or self.default_strategy
        balancing_strategy = self._strategies.get(strategy)
        if balancing_strategy:
            balancing_strategy.record_request(instance)

        logger.debug(f"Request started for instance {instance.id}")

    def record_request_completion(
        self,
        instance: ServerInstance,
        success: bool,
        strategy: Optional[LoadBalancingStrategy] = None,
    ):
        """
        Record that a request completed for an instance.

        Args:
            instance: Server instance that handled the request
            success: Whether the request was successful
            strategy: Strategy used for selection
        """
        # Notify strategy
        strategy = strategy or self.default_strategy
        balancing_strategy = self._strategies.get(strategy)
        if balancing_strategy:
            balancing_strategy.record_completion(instance, success)

        logger.debug(
            f"Request completed for instance {instance.id}, success: {success}"
        )

    def get_load_balancer_stats(self) -> Dict[str, any]:
        """Get load balancer statistics."""
        with self._lock:
            total_requests = sum(self._request_count.values())

            return {
                "default_strategy": self.default_strategy.value,
                "available_strategies": [
                    strategy.value for strategy in self._strategies.keys()
                ],
                "total_requests": total_requests,
                "requests_per_instance": dict(self._request_count),
                "strategy_stats": {
                    strategy.value: {
                        "name": balancer.name,
                        "type": type(balancer).__name__,
                    }
                    for strategy, balancer in self._strategies.items()
                },
            }

    def reset_stats(self):
        """Reset all load balancer statistics."""
        with self._lock:
            self._request_count.clear()

        # Reset strategy-specific stats
        for strategy in self._strategies.values():
            if hasattr(strategy, "_active_connections"):
                strategy._active_connections.clear()
            if hasattr(strategy, "_failure_counts"):
                strategy._failure_counts.clear()
            if hasattr(strategy, "_current_weights"):
                strategy._current_weights.clear()
            if hasattr(strategy, "_counters"):
                strategy._counters.clear()

        logger.info("Load balancer statistics reset")
