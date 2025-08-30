"""
Unit tests for the enhanced Gateway Registry.
"""

import asyncio
import json
from pathlib import Path
from typing import Any, Dict
from unittest.mock import AsyncMock, Mock, patch

import pytest

from mcp_platform.gateway.database import DatabaseManager
from mcp_platform.gateway.models import (
    InstanceConfig,
    LoadBalancerConfig,
    MCPConnection,
    ServerInstance,
    ServerStatus,
    ServerTemplate,
)
from mcp_platform.gateway.registry import (
    GatewayRegistry,
    HealthChecker,
    InstanceManager,
    LoadBalancer,
    RegistryError,
    TemplateManager,
)


class TestGatewayRegistry:
    """Test GatewayRegistry functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.db_manager = Mock(spec=DatabaseManager)
        self.registry = GatewayRegistry(
            json_registry_path="/tmp/test_registry.json", db_manager=self.db_manager
        )

    async def test_registry_initialization(self):
        """Test registry initialization."""
        registry = GatewayRegistry()

        # Should have default components
        assert isinstance(registry.template_manager, TemplateManager)
        assert isinstance(registry.instance_manager, InstanceManager)
        assert isinstance(registry.health_checker, HealthChecker)
        assert isinstance(registry.load_balancer, LoadBalancer)

        # Should initialize with empty state
        assert registry.templates == {}
        assert registry.instances == {}

    async def test_registry_with_database(self):
        """Test registry with database backend."""
        self.db_manager.health_check = AsyncMock(return_value=True)
        self.db_manager.get_all_templates = AsyncMock(return_value=[])
        self.db_manager.get_all_instances = AsyncMock(return_value=[])

        await self.registry.initialize()

        # Should check database health and load data
        self.db_manager.health_check.assert_called_once()
        self.db_manager.get_all_templates.assert_called_once()
        self.db_manager.get_all_instances.assert_called_once()

    async def test_registry_fallback_to_json(self):
        """Test registry falls back to JSON when database unavailable."""
        # Mock database as unavailable
        self.db_manager = None
        registry = GatewayRegistry(json_registry_path="/tmp/test_registry.json")

        # Create mock JSON file
        test_data = {"templates": {}, "instances": {}, "version": "2.0"}

        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("builtins.open", create=True) as mock_open,
        ):
            mock_open.return_value.__enter__.return_value.read.return_value = (
                json.dumps(test_data)
            )

            await registry.initialize()

            assert registry.templates == {}
            assert registry.instances == {}

    async def test_template_registration(self):
        """Test template registration."""
        template = ServerTemplate(
            name="test_template",
            command=["python", "-m", "test_server"],
            args=[],
            env={},
            description="Test template",
            category="testing",
        )

        # Mock database save
        self.db_manager.create_template = AsyncMock(return_value=template)

        await self.registry.register_template(template)

        # Should store in memory and database
        assert "test_template" in self.registry.templates
        assert self.registry.templates["test_template"] == template
        self.db_manager.create_template.assert_called_once_with(template)

    async def test_template_registration_validation(self):
        """Test template registration validation."""
        # Invalid template (missing required field)
        with pytest.raises(RegistryError, match="Template validation failed"):
            await self.registry.register_template(
                ServerTemplate(
                    name="",  # Empty name should fail
                    command=["python"],
                    args=[],
                    env={},
                )
            )

    async def test_instance_creation(self):
        """Test instance creation."""
        # Register template first
        template = ServerTemplate(
            name="test_template",
            command=["python", "-m", "test_server"],
            args=[],
            env={},
            description="Test template",
        )
        self.registry.templates["test_template"] = template

        # Mock database operations
        self.db_manager.create_instance = AsyncMock()

        instance = await self.registry.create_instance("test_template", port=8080)

        assert instance.template_name == "test_template"
        assert instance.port == 8080
        assert instance.status == ServerStatus.CREATED
        assert instance.id in self.registry.instances

        self.db_manager.create_instance.assert_called_once()

    async def test_instance_creation_nonexistent_template(self):
        """Test instance creation with nonexistent template."""
        with pytest.raises(RegistryError, match="Template 'nonexistent' not found"):
            await self.registry.create_instance("nonexistent")

    async def test_load_balancer_integration(self):
        """Test load balancer integration."""
        # Create instances
        template = ServerTemplate(
            name="test_template", command=["python"], args=[], env={}
        )
        self.registry.templates["test_template"] = template

        instance1 = ServerInstance(
            id="test-1",
            template_name="test_template",
            port=8080,
            status=ServerStatus.RUNNING,
        )
        instance2 = ServerInstance(
            id="test-2",
            template_name="test_template",
            port=8081,
            status=ServerStatus.RUNNING,
        )

        self.registry.instances["test-1"] = instance1
        self.registry.instances["test-2"] = instance2

        # Test load balancer selection
        selected = self.registry.load_balancer.select_instance(
            "test_template", self.registry.instances
        )
        assert selected in [instance1, instance2]

    async def test_health_checker_functionality(self):
        """Test health checker functionality."""
        # Create instance
        instance = ServerInstance(
            id="test-1",
            template_name="test_template",
            port=8080,
            status=ServerStatus.RUNNING,
        )
        self.registry.instances["test-1"] = instance

        # Mock health check
        with patch.object(
            self.registry.health_checker, "check_instance_health"
        ) as mock_check:
            mock_check.return_value = True

            # Start health checking
            await self.registry.start_health_checking()

            # Simulate health check cycle
            await asyncio.sleep(0.1)  # Small delay for async operations

            # Stop health checking
            await self.registry.stop_health_checking()

    async def test_stats_collection(self):
        """Test statistics collection."""
        # Add some test data
        template = ServerTemplate(
            name="test_template", command=["python"], args=[], env={}
        )
        self.registry.templates["test_template"] = template

        instance = ServerInstance(
            id="test-1",
            template_name="test_template",
            port=8080,
            status=ServerStatus.RUNNING,
        )
        self.registry.instances["test-1"] = instance

        stats = await self.registry.get_stats()

        assert stats["templates"]["test_template"]["total_instances"] == 1
        assert stats["templates"]["test_template"]["healthy_instances"] == 1
        assert stats["total_requests"] >= 0

    async def test_cleanup_functionality(self):
        """Test cleanup functionality."""
        # Create stopped instance
        instance = ServerInstance(
            id="test-1",
            template_name="test_template",
            port=8080,
            status=ServerStatus.STOPPED,
        )
        self.registry.instances["test-1"] = instance

        # Mock database deletion
        self.db_manager.delete_instance = AsyncMock()

        await self.registry.cleanup_stopped_instances()

        # Instance should be removed
        assert "test-1" not in self.registry.instances
        self.db_manager.delete_instance.assert_called_once_with("test-1")


class TestTemplateManager:
    """Test TemplateManager functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.manager = TemplateManager()

    def test_template_validation(self):
        """Test template validation."""
        # Valid template
        valid_template = ServerTemplate(
            name="valid_template",
            command=["python", "-m", "server"],
            args=[],
            env={"KEY": "value"},
        )

        assert self.manager.validate_template(valid_template) is True

        # Invalid template (empty name)
        invalid_template = ServerTemplate(name="", command=["python"], args=[], env={})

        assert self.manager.validate_template(invalid_template) is False

    def test_template_normalization(self):
        """Test template normalization."""
        template = ServerTemplate(
            name="Test Template", command=["python"], args=[], env={}  # Mixed case
        )

        normalized = self.manager.normalize_template(template)

        # Name should be lowercase
        assert normalized.name == "test template"

    def test_template_categorization(self):
        """Test automatic template categorization."""
        # Python template
        python_template = ServerTemplate(
            name="python_server", command=["python", "-m", "server"], args=[], env={}
        )

        category = self.manager.categorize_template(python_template)
        assert category == "python"

        # Node.js template
        node_template = ServerTemplate(
            name="node_server", command=["node", "server.js"], args=[], env={}
        )

        category = self.manager.categorize_template(node_template)
        assert category == "nodejs"

    def test_template_defaults(self):
        """Test template default values."""
        template = ServerTemplate(name="test", command=["python"], args=[], env={})

        with_defaults = self.manager.apply_defaults(template)

        assert with_defaults.description is not None
        assert with_defaults.category is not None
        assert isinstance(with_defaults.load_balancer, LoadBalancerConfig)


class TestInstanceManager:
    """Test InstanceManager functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.manager = InstanceManager()

    def test_instance_id_generation(self):
        """Test instance ID generation."""
        id1 = self.manager.generate_instance_id("test_template")
        id2 = self.manager.generate_instance_id("test_template")

        # IDs should be unique
        assert id1 != id2

        # IDs should contain template name
        assert "test_template" in id1
        assert "test_template" in id2

    def test_port_allocation(self):
        """Test port allocation."""
        existing_instances = {
            "test-1": ServerInstance(
                id="test-1",
                template_name="test",
                port=8080,
                status=ServerStatus.RUNNING,
            )
        }

        port = self.manager.allocate_port(existing_instances)
        assert port != 8080  # Should not conflict
        assert 8000 <= port <= 65535  # Should be in valid range

    def test_instance_validation(self):
        """Test instance validation."""
        # Valid instance
        valid_instance = ServerInstance(
            id="test-1", template_name="test", port=8080, status=ServerStatus.CREATED
        )

        assert self.manager.validate_instance(valid_instance) is True

        # Invalid instance (invalid port)
        invalid_instance = ServerInstance(
            id="test-1",
            template_name="test",
            port=70000,  # Invalid port
            status=ServerStatus.CREATED,
        )

        assert self.manager.validate_instance(invalid_instance) is False

    def test_instance_config_generation(self):
        """Test instance configuration generation."""
        template = ServerTemplate(
            name="test_template",
            command=["python", "-m", "server"],
            args=[],
            env={"ENV": "test"},
        )

        instance = ServerInstance(
            id="test-1",
            template_name="test_template",
            port=8080,
            status=ServerStatus.CREATED,
        )

        config = self.manager.generate_instance_config(template, instance)

        assert isinstance(config, InstanceConfig)
        assert config.command == template.command
        assert config.env["ENV"] == "test"
        assert config.env["PORT"] == "8080"  # Port should be added to env


class TestHealthChecker:
    """Test HealthChecker functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.health_checker = HealthChecker()

    async def test_instance_health_check(self):
        """Test individual instance health check."""
        instance = ServerInstance(
            id="test-1", template_name="test", port=8080, status=ServerStatus.RUNNING
        )

        # Mock successful health check
        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_response = Mock()
            mock_response.status = 200
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)
            mock_get.return_value = mock_response

            result = await self.health_checker.check_instance_health(instance)
            assert result is True

    async def test_health_check_failure(self):
        """Test health check failure handling."""
        instance = ServerInstance(
            id="test-1", template_name="test", port=8080, status=ServerStatus.RUNNING
        )

        # Mock failed health check
        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_get.side_effect = Exception("Connection failed")

            result = await self.health_checker.check_instance_health(instance)
            assert result is False

    async def test_batch_health_checks(self):
        """Test batch health checking."""
        instances = {
            "test-1": ServerInstance(
                id="test-1",
                template_name="test",
                port=8080,
                status=ServerStatus.RUNNING,
            ),
            "test-2": ServerInstance(
                id="test-2",
                template_name="test",
                port=8081,
                status=ServerStatus.RUNNING,
            ),
        }

        # Mock health checks
        with patch.object(self.health_checker, "check_instance_health") as mock_check:
            mock_check.side_effect = [True, False]  # First healthy, second unhealthy

            results = await self.health_checker.check_all_instances(instances)

            assert results["test-1"] is True
            assert results["test-2"] is False
            assert mock_check.call_count == 2

    def test_health_check_timeout_configuration(self):
        """Test health check timeout configuration."""
        health_checker = HealthChecker(timeout=5.0)
        assert health_checker.timeout == 5.0

        # Default timeout
        default_checker = HealthChecker()
        assert default_checker.timeout > 0


class TestLoadBalancer:
    """Test LoadBalancer functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.load_balancer = LoadBalancer()

    def test_round_robin_strategy(self):
        """Test round-robin load balancing strategy."""
        instances = {
            "test-1": ServerInstance(
                id="test-1",
                template_name="test",
                port=8080,
                status=ServerStatus.RUNNING,
            ),
            "test-2": ServerInstance(
                id="test-2",
                template_name="test",
                port=8081,
                status=ServerStatus.RUNNING,
            ),
            "test-3": ServerInstance(
                id="test-3",
                template_name="test",
                port=8082,
                status=ServerStatus.RUNNING,
            ),
        }

        # Configure round-robin
        config = LoadBalancerConfig(strategy="round_robin")
        self.load_balancer.configure("test", config)

        # Test round-robin selection
        selections = []
        for _ in range(6):  # Two full rounds
            selected = self.load_balancer.select_instance("test", instances)
            selections.append(selected.id)

        # Should cycle through instances
        assert selections[:3] == selections[3:]  # Second round same as first

    def test_least_connections_strategy(self):
        """Test least connections load balancing strategy."""
        instances = {
            "test-1": ServerInstance(
                id="test-1",
                template_name="test",
                port=8080,
                status=ServerStatus.RUNNING,
            ),
            "test-2": ServerInstance(
                id="test-2",
                template_name="test",
                port=8081,
                status=ServerStatus.RUNNING,
            ),
        }

        # Configure least connections
        config = LoadBalancerConfig(strategy="least_connections")
        self.load_balancer.configure("test", config)

        # Simulate connections
        self.load_balancer.record_request("test-1")
        self.load_balancer.record_request("test-1")
        self.load_balancer.record_request("test-2")

        # Should select instance with fewer connections
        selected = self.load_balancer.select_instance("test", instances)
        assert selected.id == "test-2"

    def test_weighted_strategy(self):
        """Test weighted load balancing strategy."""
        instances = {
            "test-1": ServerInstance(
                id="test-1",
                template_name="test",
                port=8080,
                status=ServerStatus.RUNNING,
                config=InstanceConfig(weight=1),
            ),
            "test-2": ServerInstance(
                id="test-2",
                template_name="test",
                port=8081,
                status=ServerStatus.RUNNING,
                config=InstanceConfig(weight=3),
            ),
        }

        # Configure weighted strategy
        config = LoadBalancerConfig(strategy="weighted")
        self.load_balancer.configure("test", config)

        # Test weighted selection over many requests
        selections = []
        for _ in range(100):
            selected = self.load_balancer.select_instance("test", instances)
            selections.append(selected.id)

        # test-2 should be selected more often (3:1 ratio)
        test2_count = selections.count("test-2")
        test1_count = selections.count("test-1")

        # Should be roughly 3:1 ratio (allowing for randomness)
        assert test2_count > test1_count * 2

    def test_health_filtering(self):
        """Test filtering unhealthy instances."""
        instances = {
            "test-1": ServerInstance(
                id="test-1",
                template_name="test",
                port=8080,
                status=ServerStatus.RUNNING,
            ),
            "test-2": ServerInstance(
                id="test-2",
                template_name="test",
                port=8081,
                status=ServerStatus.UNHEALTHY,
            ),
            "test-3": ServerInstance(
                id="test-3",
                template_name="test",
                port=8082,
                status=ServerStatus.STOPPED,
            ),
        }

        selected = self.load_balancer.select_instance("test", instances)

        # Should only select healthy instance
        assert selected.id == "test-1"

    def test_no_healthy_instances(self):
        """Test behavior when no healthy instances available."""
        instances = {
            "test-1": ServerInstance(
                id="test-1",
                template_name="test",
                port=8080,
                status=ServerStatus.UNHEALTHY,
            )
        }

        selected = self.load_balancer.select_instance("test", instances)
        assert selected is None

    def test_request_tracking(self):
        """Test request tracking and statistics."""
        # Record some requests
        self.load_balancer.record_request("test-1")
        self.load_balancer.record_request("test-1")
        self.load_balancer.record_request("test-2")

        stats = self.load_balancer.get_stats()

        assert stats["requests_per_instance"]["test-1"] == 2
        assert stats["requests_per_instance"]["test-2"] == 1
        assert stats["total_requests"] == 3

    def test_configuration_per_template(self):
        """Test per-template load balancer configuration."""
        # Configure different strategies for different templates
        config1 = LoadBalancerConfig(strategy="round_robin")
        config2 = LoadBalancerConfig(strategy="least_connections")

        self.load_balancer.configure("template1", config1)
        self.load_balancer.configure("template2", config2)

        # Configurations should be independent
        assert self.load_balancer.configs["template1"].strategy == "round_robin"
        assert self.load_balancer.configs["template2"].strategy == "least_connections"


class TestRegistryPersistence:
    """Test registry persistence functionality."""

    async def test_json_backup_creation(self):
        """Test JSON backup creation."""
        registry = GatewayRegistry(json_registry_path="/tmp/test_backup.json")

        # Add some data
        template = ServerTemplate(
            name="test_template", command=["python"], args=[], env={}
        )
        registry.templates["test_template"] = template

        # Create backup
        with patch("builtins.open", create=True) as mock_open:
            mock_file = Mock()
            mock_open.return_value.__enter__.return_value = mock_file

            await registry._save_to_json()

            # Should have written JSON data
            mock_file.write.assert_called_once()
            written_data = mock_file.write.call_args[0][0]
            data = json.loads(written_data)

            assert "templates" in data
            assert "test_template" in data["templates"]

    async def test_json_recovery(self):
        """Test recovery from JSON backup."""
        test_data = {
            "templates": {
                "test_template": {
                    "name": "test_template",
                    "command": ["python"],
                    "args": [],
                    "env": {},
                    "description": "Test template",
                    "category": "testing",
                }
            },
            "instances": {},
            "version": "2.0",
        }

        registry = GatewayRegistry(json_registry_path="/tmp/test_recovery.json")

        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("builtins.open", create=True) as mock_open,
        ):
            mock_open.return_value.__enter__.return_value.read.return_value = (
                json.dumps(test_data)
            )

            await registry._load_from_json()

            assert "test_template" in registry.templates
            assert registry.templates["test_template"].name == "test_template"

    async def test_concurrent_access(self):
        """Test concurrent access to registry."""
        registry = GatewayRegistry()

        # Simulate concurrent template registrations
        templates = [
            ServerTemplate(name=f"template_{i}", command=["python"], args=[], env={})
            for i in range(10)
        ]

        # Mock database operations
        registry.db_manager = Mock(spec=DatabaseManager)
        registry.db_manager.create_template = AsyncMock()

        # Register templates concurrently
        tasks = [registry.register_template(template) for template in templates]

        await asyncio.gather(*tasks)

        # All templates should be registered
        assert len(registry.templates) == 10
        assert registry.db_manager.create_template.call_count == 10
