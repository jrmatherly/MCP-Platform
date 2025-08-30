"""
Unit tests for gateway integration.
"""

from unittest.mock import Mock, patch

import pytest

from mcp_platform.gateway.integration import GatewayIntegration
from mcp_platform.gateway.registry import ServerRegistry

pytestmark = pytest.mark.unit


class TestGatewayIntegration:
    """Unit tests for GatewayIntegration class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.registry = ServerRegistry()
        self.mock_backend_manager = Mock()
        self.integration = GatewayIntegration(self.registry, self.mock_backend_manager)

    def test_deployment_to_server_instance_http(self):
        """Test converting HTTP deployment to server instance."""
        deployment_info = {
            "id": "abc123",
            "template": "demo",
            "status": "running",
            "backend_type": "docker",
            "endpoint": "http://localhost:7071",
            "container_id": "mcp-demo-abc123",
            "config": {"greeting": "Hello"},
            "env_vars": {"LOG_LEVEL": "INFO"},
        }

        instance = self.integration._deployment_to_server_instance(deployment_info)

        assert instance is not None
        assert instance.id == "demo-abc123"
        assert instance.template_name == "demo"
        assert instance.endpoint == "http://localhost:7071"
        assert instance.transport == "http"
        assert instance.backend == "docker"
        assert instance.container_id == "mcp-demo-abc123"
        assert instance.deployment_id == "abc123"
        assert instance.env_vars == {"LOG_LEVEL": "INFO"}
        assert instance.metadata["config"] == {"greeting": "Hello"}

    def test_deployment_to_server_instance_stdio(self):
        """Test converting stdio deployment to server instance."""
        deployment_info = {
            "id": "def456",
            "template": "filesystem",
            "status": "running",
            "backend_type": "docker",
            "container_id": "mcp-filesystem-def456",
            "command": ["python", "server.py"],
            "config": {"data_dir": "/data"},
        }

        instance = self.integration._deployment_to_server_instance(deployment_info)

        assert instance is not None
        assert instance.id == "filesystem-def456"
        assert instance.template_name == "filesystem"
        assert instance.endpoint is None
        assert instance.command == ["python", "server.py"]
        assert instance.transport == "stdio"
        assert instance.container_id == "mcp-filesystem-def456"

    def test_deployment_to_server_instance_missing_fields(self):
        """Test conversion with missing required fields."""
        # Missing deployment ID
        deployment_info = {"template": "demo", "status": "running"}

        instance = self.integration._deployment_to_server_instance(deployment_info)
        assert instance is None

        # Missing template name
        deployment_info = {"id": "abc123", "status": "running"}

        instance = self.integration._deployment_to_server_instance(deployment_info)
        assert instance is None

    def test_register_deployment(self):
        """Test registering a deployment."""
        deployment_info = {
            "id": "abc123",
            "template": "demo",
            "status": "running",
            "endpoint": "http://localhost:7071",
        }

        success = self.integration.register_deployment("demo", deployment_info)

        assert success
        assert "demo" in self.registry.templates
        template = self.registry.get_template("demo")
        assert len(template.instances) == 1
        assert template.instances[0].deployment_id == "abc123"

    def test_register_deployment_update_existing(self):
        """Test updating existing deployment registration."""
        deployment_info = {
            "id": "abc123",
            "template": "demo",
            "status": "running",
            "endpoint": "http://localhost:7071",
        }

        # Register first time
        self.integration.register_deployment("demo", deployment_info)

        # Update with new endpoint
        deployment_info["endpoint"] = "http://localhost:7072"
        self.integration.register_deployment("demo", deployment_info)

        # Should still have only one instance, but updated
        template = self.registry.get_template("demo")
        assert len(template.instances) == 1
        assert template.instances[0].endpoint == "http://localhost:7072"

    def test_deregister_deployment(self):
        """Test deregistering a deployment."""
        deployment_info = {
            "id": "abc123",
            "template": "demo",
            "status": "running",
            "endpoint": "http://localhost:7071",
        }

        # Register first
        self.integration.register_deployment("demo", deployment_info)
        assert len(self.registry.templates) == 1

        # Deregister
        success = self.integration.deregister_deployment("demo", "abc123")

        assert success
        assert len(self.registry.templates) == 0  # Template removed when empty

    def test_deregister_deployment_not_found(self):
        """Test deregistering non-existent deployment."""
        success = self.integration.deregister_deployment("demo", "nonexistent")
        assert not success

    def test_get_load_balancer_config_http(self):
        """Test load balancer config for HTTP deployment."""
        deployment_info = {"endpoint": "http://localhost:7071"}

        config = self.integration._get_load_balancer_config(deployment_info)

        assert config.strategy == "round_robin"
        assert config.health_check_interval == 30
        assert config.timeout == 60

    def test_get_load_balancer_config_stdio(self):
        """Test load balancer config for stdio deployment."""
        deployment_info = {"command": ["python", "server.py"]}

        config = self.integration._get_load_balancer_config(deployment_info)

        assert config.strategy == "round_robin"
        assert config.health_check_interval == 30  # Default interval
        assert config.pool_size == 3
        assert config.timeout == 60  # Default timeout

    def test_get_load_balancer_config_from_deployment(self):
        """Test load balancer config from deployment metadata."""
        deployment_info = {
            "load_balancer": {
                "strategy": "least_connections",
                "health_check_interval": 45,
                "max_retries": 5,
            }
        }

        config = self.integration._get_load_balancer_config(deployment_info)

        assert config.strategy == "least_connections"
        assert config.health_check_interval == 45
        assert config.max_retries == 5

    def test_sync_with_deployments(self):
        """Test syncing registry with current deployments."""
        # Mock deployments
        mock_deployments = [
            {
                "id": "abc123",
                "template": "demo",
                "status": "running",
                "endpoint": "http://localhost:7071",
                "backend_type": "docker",
            },
            {
                "id": "def456",
                "template": "filesystem",
                "status": "running",
                "command": ["python", "server.py"],
                "backend_type": "docker",
            },
            {
                "id": "ghi789",
                "template": "demo",
                "status": "stopped",  # Not running, should be ignored
                "endpoint": "http://localhost:7072",
                "backend_type": "docker",
            },
        ]

        self.mock_backend_manager.get_all_deployments.return_value = mock_deployments

        # Perform sync
        self.integration.sync_with_deployments()

        # Verify results
        assert len(self.registry.templates) == 2  # demo and filesystem
        assert "demo" in self.registry.templates
        assert "filesystem" in self.registry.templates

        demo_template = self.registry.get_template("demo")
        assert len(demo_template.instances) == 1  # Only running deployment

        fs_template = self.registry.get_template("filesystem")
        assert len(fs_template.instances) == 1

    def test_cleanup_stale_registrations(self):
        """Test cleanup of stale registrations."""
        # Register some instances manually
        from mcp_platform.gateway.registry import ServerInstance

        stale_instance = ServerInstance(
            id="stale", template_name="demo", deployment_id="old123"
        )
        current_instance = ServerInstance(
            id="current", template_name="demo", deployment_id="current456"
        )

        self.registry.register_server("demo", stale_instance)
        self.registry.register_server("demo", current_instance)

        # Mock that only current instance is found in deployments
        found_instances = {("demo", "current")}

        # Perform cleanup
        self.integration._cleanup_stale_registrations(found_instances)

        # Verify stale instance was removed
        template = self.registry.get_template("demo")
        assert len(template.instances) == 1
        assert template.instances[0].id == "current"

    def test_get_integration_stats(self):
        """Test getting integration statistics."""
        # Mock deployments and registry
        mock_deployments = [
            {"backend_type": "docker", "status": "running"},
            {"backend_type": "docker", "status": "stopped"},
            {"backend_type": "kubernetes", "status": "running"},
        ]

        self.mock_backend_manager.get_all_deployments.return_value = mock_deployments

        # Add some registry data
        from mcp_platform.gateway.registry import ServerInstance

        instance = ServerInstance(id="test", template_name="demo")
        self.registry.register_server("demo", instance)

        # Get stats
        stats = self.integration.get_integration_stats()

        assert stats["deployments"]["total"] == 3
        assert stats["deployments"]["by_backend"]["docker"]["total"] == 2
        assert stats["deployments"]["by_backend"]["docker"]["running"] == 1
        assert stats["deployments"]["by_backend"]["kubernetes"]["total"] == 1
        assert stats["deployments"]["by_backend"]["kubernetes"]["running"] == 1
        assert stats["registry"]["total_instances"] == 1
        assert stats["sync_ratio"]["registered_instances"] == 1
        assert stats["sync_ratio"]["running_deployments"] == 2
