"""
Comprehensive unit tests for mcp_platform.gateway.registry module.

Tests cover server registry functionality, template management, instance registration,
health monitoring, and database persistence with fallback mechanisms.
"""

import asyncio
import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from mcp_platform.gateway.models import (
    LoadBalancerConfig,
    ServerInstance,
    ServerStatus,
    ServerTemplate,
    TransportType,
)
from mcp_platform.gateway.registry import RegistryError, ServerRegistry


class TestServerRegistry:
    """Test server registry core functionality."""

    def test_registry_initialization_memory_mode(self):
        """Test registry initialization in memory mode."""
        registry = ServerRegistry()
        assert registry.db is None
        assert registry._use_memory is True
        assert registry.instance_crud is None
        assert registry.template_crud is None
        assert isinstance(registry._memory_templates, dict)

    def test_registry_initialization_with_database(self):
        """Test registry initialization with database."""
        mock_db = Mock()
        registry = ServerRegistry(db=mock_db)
        assert registry.db is mock_db
        assert registry._use_memory is False
        assert registry.instance_crud is not None
        assert registry.template_crud is not None

    def test_registry_initialization_with_fallback_file(self):
        """Test registry initialization with fallback file."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            fallback_path = f.name

        registry = ServerRegistry(fallback_file=fallback_path)
        assert registry.fallback_file == Path(fallback_path)

        # Cleanup
        Path(fallback_path).unlink()

    @pytest.mark.asyncio
    async def test_ensure_template_exists_memory_mode(self):
        """Test template creation in memory mode."""
        registry = ServerRegistry()

        template = await registry._ensure_template_exists("test-template")

        assert template.name == "test-template"
        assert template.instances == []
        assert template.load_balancer is None
        assert "test-template" in registry._memory_templates

    @pytest.mark.asyncio
    async def test_ensure_template_exists_database_mode(self):
        """Test template creation in database mode."""
        mock_db = Mock()
        mock_template_crud = Mock()
        mock_template_crud.get = AsyncMock(return_value=None)
        mock_template_crud.create = AsyncMock()

        with patch(
            "mcp_platform.gateway.registry.ServerTemplateCRUD",
            return_value=mock_template_crud,
        ):
            registry = ServerRegistry(db=mock_db)
            registry.template_crud = mock_template_crud

            # Mock the template creation
            expected_template = ServerTemplate(name="test-template", instances=[])
            mock_template_crud.create.return_value = expected_template

            template = await registry._ensure_template_exists("test-template")

            assert template.name == "test-template"
            mock_template_crud.get.assert_called_once_with("test-template")
            mock_template_crud.create.assert_called_once()

    def test_load_from_file_no_file(self):
        """Test loading from file when no file exists."""
        registry = ServerRegistry()
        # Should not raise any exception
        registry._load_from_file()
        assert len(registry._memory_templates) == 0

    def test_load_from_file_valid_data(self):
        """Test loading valid data from file."""
        test_data = {
            "servers": {
                "test-template": {
                    "instances": [
                        {
                            "id": "instance-1",
                            "endpoint": "http://localhost:8000",
                            "template_name": "test-template",
                            "transport": "http",
                            "command": ["python", "server.py"],
                            "status": "HEALTHY",
                            "created_at": datetime.now(timezone.utc).isoformat(),
                            "last_seen": datetime.now(timezone.utc).isoformat(),
                        }
                    ]
                }
            }
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(test_data, f)
            fallback_path = f.name

        try:
            registry = ServerRegistry(fallback_file=fallback_path)
            assert "test-template" in registry._memory_templates
            template = registry._memory_templates["test-template"]
            assert len(template.instances) == 1
            assert template.instances[0].id == "instance-1"
        finally:
            Path(fallback_path).unlink()

    def test_save_to_file_memory_mode(self):
        """Test saving to file in memory mode."""
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            fallback_path = f.name

        try:
            registry = ServerRegistry(fallback_file=fallback_path)

            # Add a template
            template = ServerTemplate(name="test-template", instances=[])
            registry._memory_templates["test-template"] = template

            registry._save_to_file()

            # Verify file was written
            assert Path(fallback_path).exists()
            with open(fallback_path, "r") as f:
                data = json.load(f)

            assert "servers" in data
            assert "test-template" in data["servers"]
            assert "last_updated" in data
        finally:
            Path(fallback_path).unlink()


class TestServerRegistryOperations:
    """Test server registry CRUD operations."""

    @pytest.mark.asyncio
    async def test_register_server_memory_mode(self):
        """Test server registration in memory mode."""
        registry = ServerRegistry()

        instance_data = {
            "id": "test-instance",
            "endpoint": "http://localhost:8000",
            "template_name": "test-template",
            "transport": TransportType.HTTP,
            "command": ["python", "server.py"],
        }

        result = await registry.register_server("test-template", instance_data)

        assert isinstance(result, ServerInstance)
        assert result.id == "test-instance"
        assert "test-template" in registry._memory_templates
        template = registry._memory_templates["test-template"]
        assert len(template.instances) == 1
        assert template.instances[0].id == "test-instance"

    @pytest.mark.asyncio
    async def test_deregister_server_memory_mode(self):
        """Test server deregistration in memory mode."""
        registry = ServerRegistry()

        # First register a server
        instance_data = {
            "id": "test-instance",
            "endpoint": "http://localhost:8000",
            "template_name": "test-template",
            "transport": TransportType.HTTP,
            "command": ["python", "server.py"],
        }
        await registry.register_server("test-template", instance_data)

        # Verify registration worked
        assert "test-template" in registry._memory_templates
        assert len(registry._memory_templates["test-template"].instances) == 1

        # Then deregister it
        result = await registry.deregister_server("test-template", "test-instance")

        assert result is True
        # Template should be deleted when no instances remain
        assert "test-template" not in registry._memory_templates

    @pytest.mark.asyncio
    async def test_deregister_server_not_found(self):
        """Test deregistration of non-existent server."""
        registry = ServerRegistry()

        result = await registry.deregister_server("test-template", "non-existent")

        assert result is False

    @pytest.mark.asyncio
    async def test_get_template_memory_mode(self):
        """Test getting template in memory mode."""
        registry = ServerRegistry()

        # Create a template
        template = ServerTemplate(name="test-template", instances=[])
        registry._memory_templates["test-template"] = template

        result = await registry.get_template("test-template")

        assert result is not None
        assert result.name == "test-template"

    @pytest.mark.asyncio
    async def test_get_template_not_found(self):
        """Test getting non-existent template."""
        registry = ServerRegistry()

        result = await registry.get_template("non-existent")

        assert result is None

    @pytest.mark.asyncio
    async def test_get_healthy_instances(self):
        """Test getting healthy instances."""
        registry = ServerRegistry()

        # Create instances with different health statuses
        healthy_instance = ServerInstance(
            id="healthy-instance",
            endpoint="http://localhost:8000",
            template_name="test-template",
            transport=TransportType.HTTP,
            command=["python", "server.py"],
            status=ServerStatus.HEALTHY,
        )

        unhealthy_instance = ServerInstance(
            id="unhealthy-instance",
            endpoint="http://localhost:8001",
            template_name="test-template",
            transport=TransportType.HTTP,
            command=["python", "server.py"],
            status=ServerStatus.UNHEALTHY,
        )

        template = ServerTemplate(
            name="test-template", instances=[healthy_instance, unhealthy_instance]
        )
        registry._memory_templates["test-template"] = template

        healthy_instances = await registry.get_healthy_instances("test-template")

        assert len(healthy_instances) == 1
        assert healthy_instances[0].id == "healthy-instance"

    @pytest.mark.asyncio
    async def test_get_instance(self):
        """Test getting specific instance."""
        registry = ServerRegistry()

        instance = ServerInstance(
            id="test-instance",
            endpoint="http://localhost:8000",
            template_name="test-template",
            transport=TransportType.HTTP,
            command=["python", "server.py"],
        )

        template = ServerTemplate(name="test-template", instances=[instance])
        registry._memory_templates["test-template"] = template

        result = await registry.get_instance("test-template", "test-instance")

        assert result is not None
        assert result.id == "test-instance"

    @pytest.mark.asyncio
    async def test_list_templates(self):
        """Test listing all templates."""
        registry = ServerRegistry()

        template1 = ServerTemplate(name="template1", instances=[])
        template2 = ServerTemplate(name="template2", instances=[])
        registry._memory_templates["template1"] = template1
        registry._memory_templates["template2"] = template2

        templates = await registry.list_templates()

        assert len(templates) == 2
        assert "template1" in templates
        assert "template2" in templates

    @pytest.mark.asyncio
    async def test_list_instances(self):
        """Test listing instances for a template."""
        registry = ServerRegistry()

        instance1 = ServerInstance(
            id="instance1",
            endpoint="http://localhost:8000",
            template_name="test-template",
            transport=TransportType.HTTP,
            command=["python", "server.py"],
        )

        instance2 = ServerInstance(
            id="instance2",
            endpoint="http://localhost:8001",
            template_name="test-template",
            transport=TransportType.HTTP,
            command=["python", "server.py"],
        )

        template = ServerTemplate(
            name="test-template", instances=[instance1, instance2]
        )
        registry._memory_templates["test-template"] = template

        instances = await registry.list_instances("test-template")

        assert len(instances) == 2
        assert instances[0].id == "instance1"
        assert instances[1].id == "instance2"

    @pytest.mark.asyncio
    async def test_list_all_instances(self):
        """Test listing all instances across templates."""
        registry = ServerRegistry()

        instance1 = ServerInstance(
            id="instance1",
            endpoint="http://localhost:8000",
            template_name="template1",
            transport=TransportType.HTTP,
            command=["python", "server.py"],
        )

        instance2 = ServerInstance(
            id="instance2",
            endpoint="http://localhost:8001",
            template_name="template2",
            transport=TransportType.HTTP,
            command=["python", "server.py"],
        )

        template1 = ServerTemplate(name="template1", instances=[instance1])
        template2 = ServerTemplate(name="template2", instances=[instance2])
        registry._memory_templates["template1"] = template1
        registry._memory_templates["template2"] = template2

        all_instances = await registry.list_all_instances()

        assert len(all_instances) == 2


class TestServerRegistryHealthManagement:
    """Test health monitoring and management features."""

    @pytest.mark.asyncio
    async def test_update_instance_health(self):
        """Test updating instance health status."""
        registry = ServerRegistry()

        instance = ServerInstance(
            id="test-instance",
            endpoint="http://localhost:8000",
            template_name="test-template",
            transport=TransportType.HTTP,
            command=["python", "server.py"],
            status=ServerStatus.HEALTHY,
        )

        template = ServerTemplate(name="test-template", instances=[instance])
        registry._memory_templates["test-template"] = template

        result = await registry.update_instance_health(
            "test-template", "test-instance", False
        )

        assert result is True
        updated_instance = registry._memory_templates["test-template"].instances[0]
        assert updated_instance.status == ServerStatus.UNHEALTHY

    @pytest.mark.asyncio
    async def test_get_registry_stats(self):
        """Test getting registry statistics."""
        registry = ServerRegistry()

        # Create multiple templates and instances
        healthy_instance = ServerInstance(
            id="healthy",
            endpoint="http://localhost:8000",
            template_name="template1",
            transport=TransportType.HTTP,
            command=["python", "server.py"],
            status=ServerStatus.HEALTHY,
        )

        unhealthy_instance = ServerInstance(
            id="unhealthy",
            endpoint="http://localhost:8001",
            template_name="template1",
            transport=TransportType.HTTP,
            command=["python", "server.py"],
            status=ServerStatus.UNHEALTHY,
        )

        template1 = ServerTemplate(
            name="template1", instances=[healthy_instance, unhealthy_instance]
        )
        template2 = ServerTemplate(name="template2", instances=[])
        registry._memory_templates["template1"] = template1
        registry._memory_templates["template2"] = template2

        stats = await registry.get_registry_stats()

        assert stats["total_templates"] == 2
        assert stats["total_instances"] == 2
        assert stats["healthy_instances"] == 1
        assert stats["unhealthy_instances"] == 1

    @pytest.mark.asyncio
    async def test_clear_unhealthy_instances(self):
        """Test clearing unhealthy instances."""
        registry = ServerRegistry()

        # Create instances with high failure counts
        healthy_instance = ServerInstance(
            id="healthy",
            endpoint="http://localhost:8000",
            template_name="test-template",
            transport=TransportType.HTTP,
            command=["python", "server.py"],
            status=ServerStatus.HEALTHY,
            consecutive_failures=2,
        )

        unhealthy_instance = ServerInstance(
            id="unhealthy",
            endpoint="http://localhost:8001",
            template_name="test-template",
            transport=TransportType.HTTP,
            command=["python", "server.py"],
            status=ServerStatus.UNHEALTHY,
            consecutive_failures=10,
        )

        template = ServerTemplate(
            name="test-template", instances=[healthy_instance, unhealthy_instance]
        )
        registry._memory_templates["test-template"] = template

        cleared_count = await registry.clear_unhealthy_instances(max_failures=5)

        assert cleared_count == 1
        remaining_instances = registry._memory_templates["test-template"].instances
        assert len(remaining_instances) == 1
        assert remaining_instances[0].id == "healthy"


class TestRegistryError:
    """Test registry error handling."""

    def test_registry_error_creation(self):
        """Test RegistryError exception creation."""
        error = RegistryError("Test error message")
        assert str(error) == "Test error message"
        assert isinstance(error, Exception)

    def test_registry_error_inheritance(self):
        """Test RegistryError inheritance."""
        error = RegistryError("Test error")
        assert isinstance(error, Exception)
        assert error.__class__.__name__ == "RegistryError"
