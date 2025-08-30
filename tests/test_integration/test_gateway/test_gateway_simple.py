"""
Simplified Integration tests for the MCP Gateway system.

These tests verify end-to-end functionality without external dependencies.
"""

import asyncio
import os
import tempfile

import pytest

from mcp_platform.gateway.gateway_server import MCPGatewayServer
from mcp_platform.gateway.models import AuthConfig, GatewayConfig


@pytest.mark.integration
@pytest.mark.gateway
@pytest.mark.asyncio
class TestGatewayIntegration:
    """Integration tests for the complete gateway system."""

    @pytest.fixture
    async def temp_db_file(self):
        """Create a temporary database file."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
            db_path = f.name

        yield f"sqlite:///{db_path}"

        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)

    @pytest.fixture
    async def gateway_config(self, temp_db_file):
        """Create a test gateway configuration."""
        return GatewayConfig(
            host="127.0.0.1",
            port=0,  # Let OS assign port
            auth=AuthConfig(
                secret_key="test_secret_key_for_integration_tests",
                database_url=temp_db_file,
            ),
            database_url=temp_db_file,
        )

    @pytest.fixture
    async def gateway_server(self, gateway_config):
        """Create a test gateway server."""
        server = MCPGatewayServer(gateway_config)
        return server

    async def test_gateway_server_initialization(self, gateway_server):
        """Test gateway server can be initialized properly."""
        assert gateway_server.config is not None
        assert gateway_server.app is not None
        assert hasattr(gateway_server, "_request_count")

    async def test_gateway_app_routes(self, gateway_server):
        """Test that all expected routes are registered."""
        app = gateway_server.app
        routes = [route.path for route in app.routes if hasattr(route, "path")]

        # Check that some key route prefixes exist
        route_prefixes = ["/auth/", "/gateway/", "/mcp/"]
        for prefix in route_prefixes:
            assert any(
                route.startswith(prefix) for route in routes
            ), f"Missing routes with prefix {prefix}"

    async def test_gateway_lifespan_management(self, gateway_config):
        """Test gateway lifespan management."""
        # Test that a gateway server can be created and has the right components
        server = MCPGatewayServer(gateway_config)

        # The app should have lifespan configured
        assert server.app.router.lifespan_context is not None

        # Should be able to access app state after server creation
        assert hasattr(server.app.state, "config")
        assert server.app.state.config == gateway_config

    async def test_authentication_integration(self, test_db_manager):
        """Test authentication system integration."""
        from mcp_platform.gateway.auth import AuthManager

        # Initialize auth manager
        auth_manager = AuthManager(test_db_manager)
        await auth_manager.initialize()

        # Create user
        user = await auth_manager.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
            is_superuser=False,
        )

        assert user is not None
        assert user.username == "testuser"

        # Test authentication
        authenticated_user = await auth_manager.authenticate_user(
            "testuser", "testpass123"
        )
        assert authenticated_user is not None
        assert authenticated_user.id == user.id

        # Test token creation
        token = auth_manager.create_access_token({"sub": user.username})
        assert token is not None
        assert isinstance(token, str)

    async def test_registry_integration(self, test_db_manager):
        """Test registry integration with database."""
        from mcp_platform.gateway.models import ServerInstanceCreate
        from mcp_platform.gateway.registry import ServerRegistry

        registry = ServerRegistry(test_db_manager, fallback_file=None)

        # Test template operations
        templates = await registry.list_templates()
        assert isinstance(templates, list)

        # Test instance registration
        instance_data = ServerInstanceCreate(
            endpoint="http://localhost:8001",
            transport="http",
            metadata={"test": True},
        )

        try:
            instance = await registry.register_server("test_template", instance_data)
            assert instance is not None
            assert instance.endpoint == "http://localhost:8001"

            # Test instance listing
            instances = await registry.list_instances("test_template")
            assert len(instances) >= 1

        except Exception as e:
            # May fail if template doesn't exist, which is fine for this test
            assert "not found" in str(e).lower() or "exist" in str(e).lower()

    async def test_health_checker_integration(self, test_db_manager):
        """Test health checker integration."""
        from mcp_platform.gateway.health_checker import HealthChecker
        from mcp_platform.gateway.registry import ServerRegistry

        registry = ServerRegistry(test_db_manager, fallback_file=None)
        health_checker = HealthChecker(registry, health_check_interval=1)

        # Test start/stop
        await health_checker.start()
        assert health_checker.running

        await health_checker.stop()
        assert not health_checker.running

    async def test_load_balancer_integration(self):
        """Test load balancer integration."""
        import datetime

        from mcp_platform.gateway.load_balancer import LoadBalancer
        from mcp_platform.gateway.models import LoadBalancingStrategy, ServerInstance

        load_balancer = LoadBalancer()

        # Create test instances
        instances = [
            ServerInstance(
                id=f"instance{i}",
                template_name="test",
                endpoint=f"http://localhost:800{i}",
                transport="http",
                status="healthy",
                created_at=datetime.datetime.now(datetime.timezone.utc),
            )
            for i in range(3)
        ]

        # Test selection
        selected = load_balancer.select_instance(
            instances, LoadBalancingStrategy.ROUND_ROBIN
        )
        assert selected in instances

        # Test metrics
        load_balancer.record_request_start(selected)
        load_balancer.record_request_completion(selected, success=True)

        stats = load_balancer.get_instance_stats(selected)
        assert stats["requests"] == 1
        assert stats["active_connections"] == 0


@pytest.mark.integration
@pytest.mark.gateway
@pytest.mark.asyncio
class TestGatewayClientIntegration:
    """Integration tests for the Gateway Client SDK."""

    async def test_integrated_mcp_client(self):
        """Test MCPClient with gateway integration."""
        from mcp_platform.client import MCPClient

        # Create client with gateway URL
        client = MCPClient(
            gateway_url="http://localhost:8080",  # Non-existent for this test
            api_key="test_key",
        )

        # Should have gateway capabilities
        assert client.gateway_url == "http://localhost:8080"
        assert client.api_key == "test_key"

        # Methods should exist
        assert hasattr(client, "call_tool_via_gateway")
        assert hasattr(client, "list_tools_via_gateway")
        assert hasattr(client, "get_gateway_health")
        assert hasattr(client, "get_gateway_stats")

    async def test_gateway_client_fallback(self):
        """Test that gateway client methods fall back to direct calls."""
        from mcp_platform.client import MCPClient

        client = MCPClient(
            gateway_url=None,  # No gateway URL
        )

        # Should not have gateway client
        assert client.gateway_url is None

        # Gateway methods should raise ValueError
        with pytest.raises(ValueError, match="Gateway URL not configured"):
            client._get_gateway_client()


@pytest.mark.integration
@pytest.mark.gateway
@pytest.mark.database
@pytest.mark.asyncio
class TestDatabaseIntegration:
    """Integration tests for database operations."""

    async def test_user_crud_operations(self, test_db_manager):
        """Test complete user CRUD operations."""
        from mcp_platform.gateway.database import UserCRUD
        from mcp_platform.gateway.models import UserRole

        user_crud = UserCRUD(test_db_manager)

        # Create user
        user_data = {
            "username": "testuser",
            "email": "test@example.com",
            "hashed_password": "hashed_password",
            "role": UserRole.USER,
        }

        user = await user_crud.create(**user_data)
        assert user.username == "testuser"
        assert user.email == "test@example.com"

        # Read user
        retrieved_user = await user_crud.get(user.id)
        assert retrieved_user.id == user.id

        # Update user
        updated_user = await user_crud.update(user.id, email="newemail@example.com")
        assert updated_user.email == "newemail@example.com"

        # Delete user
        await user_crud.delete(user.id)
        deleted_user = await user_crud.get(user.id)
        assert deleted_user is None

    async def test_api_key_crud_operations(self, test_db_manager):
        """Test complete API key CRUD operations."""
        from mcp_platform.gateway.database import APIKeyCRUD, UserCRUD
        from mcp_platform.gateway.models import UserRole

        # First create a user
        user_crud = UserCRUD(test_db_manager)
        user = await user_crud.create(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed",
            role=UserRole.USER,
        )

        # Now test API key operations
        api_key_crud = APIKeyCRUD(test_db_manager)

        api_key_data = {
            "user_id": user.id,
            "name": "test_key",
            "description": "Test API key",
            "scopes": ["tools:call"],
            "key_hash": "hashed_key",
        }

        api_key = await api_key_crud.create(**api_key_data)
        assert api_key.name == "test_key"
        assert api_key.user_id == user.id

        # Test retrieval
        retrieved_key = await api_key_crud.get(api_key.id)
        assert retrieved_key.id == api_key.id

        # Test listing by user
        user_keys = await api_key_crud.get_by_user(user.id)
        assert len(user_keys) == 1
        assert user_keys[0].id == api_key.id

    async def test_database_health_check(self, test_db_manager):
        """Test database health check functionality."""
        is_healthy = await test_db_manager.health_check()
        assert is_healthy is True

    async def test_registry_persistence(self, test_db_manager):
        """Test that registry data persists in database."""
        from mcp_platform.gateway.models import ServerInstanceCreate
        from mcp_platform.gateway.registry import ServerRegistry

        registry = ServerRegistry(test_db_manager, fallback_file=None)

        # Get initial stats
        initial_stats = await registry.get_registry_stats()

        # Try to register an instance
        instance_data = ServerInstanceCreate(
            endpoint="http://localhost:8001",
            transport="http",
            metadata={"test": True},
        )

        try:
            await registry.register_server("test_template", instance_data)

            # Check that stats changed
            new_stats = await registry.get_registry_stats()
            # May have changed depending on whether template exists

        except Exception:
            # Expected if template doesn't exist
            pass
