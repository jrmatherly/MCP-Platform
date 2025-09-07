"""
Integration tests for MCP Gateway functionality.

Tests complete workflows combining multiple gateway components.
"""

import asyncio
from datetime import timedelta
from pathlib import Path
from unittest.mock import Mock

import pytest

from mcp_platform.gateway.auth import AuthenticationError, AuthManager
from mcp_platform.gateway.models import (
    AuthConfig,
    ServerInstance,
    ServerStatus,
    TransportType,
)
from mcp_platform.gateway.registry import ServerRegistry

pytestmark = pytest.mark.integration


class TestGatewayIntegration:
    """Test integration between gateway components."""

    @pytest.mark.asyncio
    async def test_registry_auth_integration(self):
        """Test registry operations with authentication context."""
        registry = ServerRegistry()

        # Register a server
        instance_data = {
            "id": "test-instance",
            "endpoint": "http://localhost:8000",
            "template_name": "test-template",
            "transport": TransportType.HTTP,
            "command": ["python", "server.py"],
        }

        instance = await registry.register_server("test-template", instance_data)

        # Verify the instance was created
        assert instance.id == "test-instance"
        assert instance.template_name == "test-template"

        # Check that we can retrieve it
        retrieved = await registry.get_instance("test-template", "test-instance")
        assert retrieved is not None
        assert retrieved.id == instance.id

    @pytest.mark.asyncio
    async def test_registry_file_persistence_integration(self):
        """Test registry file persistence across restarts."""
        fallback_path = "/tmp/test_registry.json"

        try:
            # Create first registry and add data
            registry1 = ServerRegistry(fallback_file=fallback_path)

            instance_data = {
                "id": "persistent-instance",
                "endpoint": "http://localhost:9000",
                "template_name": "persistent-template",
                "transport": TransportType.HTTP,
                "command": ["python", "app.py"],
            }

            await registry1.register_server("persistent-template", instance_data)

            # Verify the file was created and has content
            assert Path(fallback_path).exists()

            # Create second registry from same file
            registry2 = ServerRegistry(fallback_file=fallback_path)

            # Verify data was loaded
            templates = await registry2.list_templates()
            assert "persistent-template" in templates

            instances = await registry2.list_instances("persistent-template")
            assert len(instances) == 1
            assert instances[0].id == "persistent-instance"

        finally:
            if Path(fallback_path).exists():
                Path(fallback_path).unlink()

    @pytest.mark.asyncio
    async def test_registry_health_management_workflow(self):
        """Test complete health management workflow."""
        registry = ServerRegistry()

        # Register multiple instances
        for i in range(3):
            instance_data = {
                "id": f"instance-{i}",
                "endpoint": f"http://localhost:800{i}",
                "template_name": "health-test",
                "transport": TransportType.HTTP,
                "command": ["python", "server.py"],
            }
            await registry.register_server("health-test", instance_data)

        # Verify all instances are initially unknown status
        instances = await registry.list_instances("health-test")
        assert len(instances) == 3
        for instance in instances:
            assert instance.status == ServerStatus.UNKNOWN

        # Mark some as healthy, some as unhealthy
        await registry.update_instance_health("health-test", "instance-0", True)
        await registry.update_instance_health("health-test", "instance-1", False)
        # instance-2 remains unknown

        # Check healthy instances
        healthy = await registry.get_healthy_instances("health-test")
        assert len(healthy) == 1
        assert healthy[0].id == "instance-0"

        # Get stats
        stats = await registry.get_registry_stats()
        assert stats["total_instances"] == 3
        assert stats["healthy_instances"] == 1
        assert stats["unhealthy_instances"] == 2  # unhealthy + unknown

    @pytest.mark.asyncio
    async def test_auth_token_lifecycle(self):
        """Test complete authentication token lifecycle."""

        mock_db = Mock()
        config = AuthConfig(secret_key="test-secret-key-for-testing")
        auth_manager = AuthManager(config=config, db=mock_db)

        # Create a token
        payload = {"user_id": "test-user", "role": "admin"}
        token = auth_manager.create_access_token(payload)

        assert token is not None
        assert len(token) > 0

        # Verify the token
        decoded = auth_manager.verify_token(token)
        assert decoded is not None
        assert decoded["user_id"] == "test-user"
        assert decoded["role"] == "admin"
        assert "exp" in decoded

        # Test token with custom expiration
        short_token = auth_manager.create_access_token(
            payload, expires_delta=timedelta(minutes=1)
        )
        short_decoded = auth_manager.verify_token(short_token)
        assert short_decoded is not None

    @pytest.mark.asyncio
    async def test_registry_template_management_workflow(self):
        """Test complete template management workflow."""
        registry = ServerRegistry()

        # Start with empty registry
        templates = await registry.list_templates()
        assert len(templates) == 0

        # Register instances for multiple templates
        template_names = ["web-server", "api-server", "worker"]

        for template_name in template_names:
            for i in range(2):  # 2 instances per template
                instance_data = {
                    "id": f"{template_name}-{i}",
                    "endpoint": f"http://localhost:{8000 + i}",
                    "template_name": template_name,
                    "transport": TransportType.HTTP,
                    "command": ["python", f"{template_name}.py"],
                }
                await registry.register_server(template_name, instance_data)

        # Verify all templates exist
        templates = await registry.list_templates()
        assert len(templates) == 3
        for name in template_names:
            assert name in templates

        # Verify instance counts
        for template_name in template_names:
            instances = await registry.list_instances(template_name)
            assert len(instances) == 2

        # Get all instances
        all_instances = await registry.list_all_instances()
        assert len(all_instances) == 6  # 3 templates * 2 instances

        # Remove all instances from one template
        web_instances = await registry.list_instances("web-server")
        for instance in web_instances:
            await registry.deregister_server("web-server", instance.id)

        # Template should be gone
        templates = await registry.list_templates()
        assert "web-server" not in templates
        assert len(templates) == 2

    @pytest.mark.asyncio
    async def test_server_instance_state_transitions(self):
        """Test server instance state transitions."""
        instance = ServerInstance(
            id="state-test",
            endpoint="http://localhost:8000",
            template_name="test-template",
            transport=TransportType.HTTP,
            command=["python", "server.py"],
        )

        # Initial state
        assert instance.status == ServerStatus.UNKNOWN
        assert instance.consecutive_failures == 0

        # Mark as healthy
        instance.update_health_status(True)
        assert instance.status == ServerStatus.HEALTHY
        assert instance.consecutive_failures == 0

        # Mark as unhealthy
        instance.update_health_status(False)
        assert instance.status == ServerStatus.UNHEALTHY
        assert instance.consecutive_failures == 1

        # Another failure
        instance.update_health_status(False)
        assert instance.status == ServerStatus.UNHEALTHY
        assert instance.consecutive_failures == 2

        # Recovery
        instance.update_health_status(True)
        assert instance.status == ServerStatus.HEALTHY
        assert instance.consecutive_failures == 0

    def test_model_validation_integration(self):
        """Test model validation across different scenarios."""
        # Test command validation - currently string stays as string
        instance1 = ServerInstance(
            id="test-1", template_name="test", command="single-command"
        )
        # The validation might not be applied in this case
        assert instance1.command == "single-command"

        # Test with list command
        instance2 = ServerInstance(
            id="test-2", template_name="test", command=["python", "-m", "server"]
        )
        assert instance2.command == ["python", "-m", "server"]

        # Test with None command
        instance3 = ServerInstance(id="test-3", template_name="test", command=None)
        assert instance3.command is None

    @pytest.mark.asyncio
    async def test_registry_concurrent_operations(self):
        """Test registry with concurrent operations."""
        registry = ServerRegistry()

        # Simulate concurrent registrations
        async def register_instance(i):
            instance_data = {
                "id": f"concurrent-{i}",
                "endpoint": f"http://localhost:{8000 + i}",
                "template_name": "concurrent-test",
                "transport": TransportType.HTTP,
                "command": ["python", "server.py"],
            }
            return await registry.register_server("concurrent-test", instance_data)

        # Register 5 instances concurrently
        tasks = [register_instance(i) for i in range(5)]
        results = await asyncio.gather(*tasks)

        # Verify all were registered
        assert len(results) == 5
        for i, instance in enumerate(results):
            assert instance.id == f"concurrent-{i}"

        # Verify in registry
        instances = await registry.list_instances("concurrent-test")
        assert len(instances) == 5

        # Concurrent health updates
        async def update_health(instance_id, is_healthy):
            return await registry.update_instance_health(
                "concurrent-test", instance_id, is_healthy
            )

        health_tasks = [update_health(f"concurrent-{i}", i % 2 == 0) for i in range(5)]
        health_results = await asyncio.gather(*health_tasks)

        # All should succeed
        assert all(health_results)

        # Check final state
        healthy = await registry.get_healthy_instances("concurrent-test")
        assert len(healthy) == 3  # 0, 2, 4 are healthy


class TestGatewayErrorHandling:
    """Test error handling across gateway components."""

    @pytest.mark.asyncio
    async def test_registry_error_scenarios(self):
        """Test registry error handling."""
        registry = ServerRegistry()

        # Try to get non-existent template
        template = await registry.get_template("non-existent")
        assert template is None

        # Try to get non-existent instance
        instance = await registry.get_instance("non-existent", "also-non-existent")
        assert instance is None

        # Try to deregister non-existent instance
        result = await registry.deregister_server("non-existent", "also-non-existent")
        assert result is False

        # Try to update health of non-existent instance
        result = await registry.update_instance_health(
            "non-existent", "also-non-existent", True
        )
        assert result is False

    def test_auth_error_scenarios(self):
        """Test authentication error handling."""

        mock_db = Mock()
        config = AuthConfig(secret_key="test-secret-key-for-testing")
        auth_manager = AuthManager(config=config, db=mock_db)

        # Test invalid token - verify_token raises exceptions
        try:
            auth_manager.verify_token("invalid.token.here")
            raise AssertionError("Should have raised an exception")
        except AuthenticationError:
            pass  # Expected

        # Test malformed token
        try:
            auth_manager.verify_token("not-a-jwt-at-all")
            raise AssertionError("Should have raised an exception")
        except AuthenticationError:
            pass  # Expected

        # Test empty token
        try:
            auth_manager.verify_token("")
            raise AssertionError("Should have raised an exception")
        except AuthenticationError:
            pass  # Expected
