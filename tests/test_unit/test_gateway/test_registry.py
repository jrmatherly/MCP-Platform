"""
Unit tests for gateway registry.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from mcp_platform.gateway.registry import (
    LoadBalancerConfig,
    ServerInstance,
    ServerRegistry,
    ServerTemplate,
)

pytestmark = pytest.mark.unit


class TestServerInstance:
    """Unit tests for ServerInstance class."""

    def test_server_instance_creation(self):
        """Test creating a server instance."""
        instance = ServerInstance(
            id="test-instance-1",
            template_name="demo",
            endpoint="http://localhost:7071",
            transport="http",
            backend="docker",
        )

        assert instance.id == "test-instance-1"
        assert instance.template_name == "demo"
        assert instance.endpoint == "http://localhost:7071"
        assert instance.transport == "http"
        assert instance.backend == "docker"
        assert instance.status == "unknown"
        assert instance.consecutive_failures == 0

    def test_server_instance_stdio(self):
        """Test creating a stdio server instance."""
        instance = ServerInstance(
            id="test-stdio-1",
            template_name="filesystem",
            command=["python", "server.py"],
            transport="stdio",
            backend="docker",
            working_dir="/app",
            env_vars={"DATA_DIR": "/data"},
        )

        assert instance.command == ["python", "server.py"]
        assert instance.transport == "stdio"
        assert instance.working_dir == "/app"
        assert instance.env_vars == {"DATA_DIR": "/data"}

    def test_health_status_updates(self):
        """Test health status updates."""
        instance = ServerInstance(
            id="test-health", template_name="demo", endpoint="http://localhost:7071"
        )

        # Initially unknown
        assert instance.status == "unknown"
        assert not instance.is_healthy()

        # Mark as healthy
        instance.update_health_status(True)
        assert instance.status == "healthy"
        assert instance.is_healthy()
        assert instance.consecutive_failures == 0
        assert instance.last_health_check is not None

        # Mark as unhealthy
        instance.update_health_status(False)
        assert instance.status == "unhealthy"
        assert not instance.is_healthy()
        assert instance.consecutive_failures == 1

        # Another failure
        instance.update_health_status(False)
        assert instance.consecutive_failures == 2

    def test_to_from_dict(self):
        """Test serialization to/from dictionary."""
        instance = ServerInstance(
            id="test-dict",
            template_name="demo",
            endpoint="http://localhost:7071",
            transport="http",
            backend="docker",
            metadata={"version": "1.0"},
        )

        # Convert to dict
        instance_dict = instance.to_dict()
        assert isinstance(instance_dict, dict)
        assert instance_dict["id"] == "test-dict"
        assert instance_dict["template_name"] == "demo"
        assert instance_dict["metadata"] == {"version": "1.0"}

        # Convert back from dict
        restored = ServerInstance.from_dict(instance_dict)
        assert restored.id == instance.id
        assert restored.template_name == instance.template_name
        assert restored.endpoint == instance.endpoint
        assert restored.metadata == instance.metadata


class TestLoadBalancerConfig:
    """Unit tests for LoadBalancerConfig class."""

    def test_default_config(self):
        """Test default load balancer configuration."""
        config = LoadBalancerConfig()

        assert config.strategy == "round_robin"
        assert config.health_check_interval == 30
        assert config.max_retries == 3
        assert config.pool_size == 3
        assert config.timeout == 60

    def test_custom_config(self):
        """Test custom load balancer configuration."""
        config = LoadBalancerConfig(
            strategy="least_connections",
            health_check_interval=60,
            max_retries=5,
            pool_size=5,
            timeout=120,
        )

        assert config.strategy == "least_connections"
        assert config.health_check_interval == 60
        assert config.max_retries == 5
        assert config.pool_size == 5
        assert config.timeout == 120

    def test_to_from_dict(self):
        """Test serialization to/from dictionary."""
        config = LoadBalancerConfig(
            strategy="weighted", health_check_interval=45, max_retries=4
        )

        # Convert to dict
        config_dict = config.to_dict()
        assert isinstance(config_dict, dict)
        assert config_dict["strategy"] == "weighted"
        assert config_dict["health_check_interval"] == 45

        # Convert back from dict
        restored = LoadBalancerConfig.from_dict(config_dict)
        assert restored.strategy == config.strategy
        assert restored.health_check_interval == config.health_check_interval
        assert restored.max_retries == config.max_retries


class TestServerTemplate:
    """Unit tests for ServerTemplate class."""

    def test_template_creation(self):
        """Test creating a server template."""
        instance1 = ServerInstance(
            id="demo-1", template_name="demo", endpoint="http://localhost:7071"
        )
        instance2 = ServerInstance(
            id="demo-2", template_name="demo", endpoint="http://localhost:7072"
        )

        template = ServerTemplate(
            name="demo",
            instances=[instance1, instance2],
            load_balancer=LoadBalancerConfig(),
        )

        assert template.name == "demo"
        assert len(template.instances) == 2
        assert isinstance(template.load_balancer, LoadBalancerConfig)

    def test_healthy_instances(self):
        """Test getting healthy instances."""
        instance1 = ServerInstance(id="healthy", template_name="demo")
        instance1.update_health_status(True)

        instance2 = ServerInstance(id="unhealthy", template_name="demo")
        instance2.update_health_status(False)

        template = ServerTemplate(
            name="demo",
            instances=[instance1, instance2],
            load_balancer=LoadBalancerConfig(),
        )

        healthy = template.get_healthy_instances()
        assert len(healthy) == 1
        assert healthy[0].id == "healthy"

    def test_add_remove_instances(self):
        """Test adding and removing instances."""
        template = ServerTemplate(
            name="demo", instances=[], load_balancer=LoadBalancerConfig()
        )

        # Add instance
        instance = ServerInstance(id="test", template_name="demo")
        template.add_instance(instance)
        assert len(template.instances) == 1
        assert template.get_instance_by_id("test") == instance

        # Add duplicate ID (should replace)
        instance2 = ServerInstance(
            id="test", template_name="demo", endpoint="http://new"
        )
        template.add_instance(instance2)
        assert len(template.instances) == 1  # Still 1, replaced
        assert template.get_instance_by_id("test").endpoint == "http://new"

        # Remove instance
        removed = template.remove_instance("test")
        assert removed
        assert len(template.instances) == 0
        assert template.get_instance_by_id("test") is None

        # Remove non-existent
        removed = template.remove_instance("nonexistent")
        assert not removed

    def test_to_from_dict(self):
        """Test template serialization."""
        instance = ServerInstance(id="test", template_name="demo")
        config = LoadBalancerConfig(strategy="least_connections")

        template = ServerTemplate(
            name="demo", instances=[instance], load_balancer=config
        )

        # Convert to dict
        template_dict = template.to_dict()
        assert "instances" in template_dict
        assert "load_balancer" in template_dict
        assert len(template_dict["instances"]) == 1

        # Convert back from dict
        restored = ServerTemplate.from_dict("demo", template_dict)
        assert restored.name == "demo"
        assert len(restored.instances) == 1
        assert restored.instances[0].id == "test"
        assert restored.load_balancer.strategy == "least_connections"


class TestServerRegistry:
    """Unit tests for ServerRegistry class."""

    def test_in_memory_registry(self):
        """Test registry without persistence."""
        registry = ServerRegistry()

        # Should start empty
        assert len(registry.templates) == 0
        assert registry.list_templates() == []
        assert registry.list_all_instances() == []

    def test_register_server(self):
        """Test registering a server."""
        registry = ServerRegistry()

        instance = ServerInstance(
            id="test-1", template_name="demo", endpoint="http://localhost:7071"
        )

        # Register server
        registry.register_server("demo", instance)

        # Verify registration
        assert "demo" in registry.templates
        template = registry.get_template("demo")
        assert template is not None
        assert len(template.instances) == 1
        assert template.instances[0].id == "test-1"

        # Verify lists
        assert registry.list_templates() == ["demo"]
        instances = registry.list_all_instances()
        assert len(instances) == 1
        assert instances[0].id == "test-1"

    def test_deregister_server(self):
        """Test deregistering a server."""
        registry = ServerRegistry()

        instance = ServerInstance(id="test-1", template_name="demo")
        registry.register_server("demo", instance)

        # Deregister
        success = registry.deregister_server("demo", "test-1")
        assert success

        # Verify removal
        assert len(registry.templates) == 0  # Template removed when empty
        assert registry.list_templates() == []

        # Deregister non-existent
        success = registry.deregister_server("demo", "nonexistent")
        assert not success

    def test_health_updates(self):
        """Test health status updates."""
        registry = ServerRegistry()

        instance = ServerInstance(id="test-1", template_name="demo")
        registry.register_server("demo", instance)

        # Update health
        success = registry.update_instance_health("demo", "test-1", True)
        assert success

        # Verify update
        updated_instance = registry.get_instance("demo", "test-1")
        assert updated_instance.is_healthy()

        # Update non-existent
        success = registry.update_instance_health("demo", "nonexistent", True)
        assert not success

    def test_healthy_instances(self):
        """Test getting healthy instances."""
        registry = ServerRegistry()

        # Add healthy instance
        healthy = ServerInstance(id="healthy", template_name="demo")
        healthy.update_health_status(True)
        registry.register_server("demo", healthy)

        # Add unhealthy instance
        unhealthy = ServerInstance(id="unhealthy", template_name="demo")
        unhealthy.update_health_status(False)
        registry.register_server("demo", unhealthy)

        # Get healthy instances
        healthy_instances = registry.get_healthy_instances("demo")
        assert len(healthy_instances) == 1
        assert healthy_instances[0].id == "healthy"

        # Non-existent template
        assert registry.get_healthy_instances("nonexistent") == []

    def test_registry_stats(self):
        """Test registry statistics."""
        registry = ServerRegistry()

        # Empty registry
        stats = registry.get_registry_stats()
        assert stats["total_templates"] == 0
        assert stats["total_instances"] == 0
        assert stats["healthy_instances"] == 0

        # Add instances
        healthy = ServerInstance(id="healthy", template_name="demo")
        healthy.update_health_status(True)
        registry.register_server("demo", healthy)

        unhealthy = ServerInstance(id="unhealthy", template_name="demo")
        unhealthy.update_health_status(False)
        registry.register_server("demo", unhealthy)

        # Check stats
        stats = registry.get_registry_stats()
        assert stats["total_templates"] == 1
        assert stats["total_instances"] == 2
        assert stats["healthy_instances"] == 1
        assert stats["unhealthy_instances"] == 1
        assert "demo" in stats["templates"]
        assert stats["templates"]["demo"]["total_instances"] == 2
        assert stats["templates"]["demo"]["healthy_instances"] == 1

    def test_clear_unhealthy_instances(self):
        """Test clearing unhealthy instances."""
        registry = ServerRegistry()

        # Add instances with failures
        instance1 = ServerInstance(id="failing-1", template_name="demo")
        instance1.consecutive_failures = 6  # Above threshold
        registry.register_server("demo", instance1)

        instance2 = ServerInstance(id="failing-2", template_name="demo")
        instance2.consecutive_failures = 3  # Below threshold
        registry.register_server("demo", instance2)

        instance3 = ServerInstance(id="healthy", template_name="demo")
        instance3.consecutive_failures = 0
        registry.register_server("demo", instance3)

        # Clear unhealthy (max_failures = 5)
        removed_count = registry.clear_unhealthy_instances(max_failures=5)

        assert removed_count == 1
        assert len(registry.get_template("demo").instances) == 2
        assert registry.get_instance("demo", "failing-1") is None
        assert registry.get_instance("demo", "failing-2") is not None
        assert registry.get_instance("demo", "healthy") is not None

    def test_persistence(self):
        """Test registry persistence to file."""
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as f:
            registry_file = f.name

        try:
            # Create registry with file
            registry = ServerRegistry(registry_file)

            instance = ServerInstance(id="persistent", template_name="demo")
            registry.register_server("demo", instance)

            # Create new registry with same file
            registry2 = ServerRegistry(registry_file)

            # Should load existing data
            assert len(registry2.templates) == 1
            assert "demo" in registry2.templates
            assert registry2.get_instance("demo", "persistent") is not None

        finally:
            # Cleanup
            Path(registry_file).unlink(missing_ok=True)
