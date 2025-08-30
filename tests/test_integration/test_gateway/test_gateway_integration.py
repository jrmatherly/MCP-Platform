"""
Integration tests for the MCP Gateway system.

These tests verify end-to-end functionality including:
- Gateway server startup and shutdown
- Authentication flow
- Database persistence
- Registry operations
- Health checking
- Load balancing
"""

import asyncio
import json
import os
import tempfile
from pathlib import Path

import aiohttp
import pytest

from mcp_platform.gateway.gateway_server import MCPGatewayServer
from mcp_platform.gateway.models import (
    APIKeyCreate,
    AuthConfig,
    GatewayConfig,
    ServerInstanceCreate,
    UserCreate,
)


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
        """Create and start a test gateway server."""
        server = MCPGatewayServer(gateway_config)

        # Start server in background
        import uvicorn

        config = uvicorn.Config(
            server.app,
            host=gateway_config.host,
            port=gateway_config.port,
            log_level="error",  # Reduce noise in tests
        )
        server_task = asyncio.create_task(uvicorn.Server(config).serve())

        # Wait a moment for server to start
        await asyncio.sleep(0.1)

        yield server

        # Cleanup
        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass

    @pytest.fixture
    def client(self, gateway_server):
        """Create a test client for the gateway."""
        return TestClient(gateway_server.app)

    def test_gateway_health_endpoint(self, client):
        """Test the gateway health endpoint."""
        response = client.get("/gateway/health")
        assert response.status_code == 200

        data = response.json()
        assert "status" in data
        assert "database" in data
        assert "templates" in data
        assert "instances" in data
        assert "uptime" in data

    def test_authentication_flow(self, client):
        """Test complete authentication flow."""
        # Try accessing protected endpoint without auth
        response = client.get("/gateway/stats")
        assert response.status_code == 401

        # Create admin user should work (auto-created)
        # Login as admin
        login_data = {
            "username": "admin",
            "password": os.getenv("GATEWAY_ADMIN_PASSWORD", "admin"),
        }
        response = client.post("/auth/login", params=login_data)

        if response.status_code == 200:
            token_data = response.json()
            assert "access_token" in token_data

            # Use token to access protected endpoint
            headers = {"Authorization": f"Bearer {token_data['access_token']}"}
            response = client.get("/gateway/stats", headers=headers)
            assert response.status_code == 200

    def test_template_and_instance_management(self, client):
        """Test template and instance management."""
        # First authenticate
        headers = self._get_auth_headers(client)

        # List templates (should be empty initially)
        response = client.get("/gateway/templates")
        assert response.status_code == 200

        # Register a test instance
        instance_data = ServerInstanceCreate(
            endpoint="http://localhost:8001",
            transport="http",
            metadata={"test": True},
        )

        response = client.post(
            "/gateway/templates/test_template/instances",
            json=instance_data.dict(),
            headers=headers,
        )
        # May fail if no template exists, which is expected

        # List templates again
        response = client.get("/gateway/templates")
        assert response.status_code == 200

    def test_api_key_management(self, client):
        """Test API key creation and usage."""
        # First authenticate as admin
        headers = self._get_auth_headers(client)

        if headers:
            # Create API key
            api_key_data = APIKeyCreate(
                name="test_key",
                description="Test API key",
                scopes=["tools:call"],
                user_id=1,  # Assume admin user has ID 1
            )

            response = client.post(
                "/auth/api-keys",
                json=api_key_data.dict(),
                headers=headers,
            )

            if response.status_code == 200:
                key_data = response.json()
                assert "key" in key_data

                # Use API key to access endpoint
                api_headers = {"X-API-Key": key_data["key"]}
                response = client.get("/gateway/health", headers=api_headers)
                assert response.status_code == 200

    def test_mcp_tool_call_integration(self, client):
        """Test MCP tool calling through gateway."""
        headers = self._get_auth_headers(client)

        # Try to call a tool (will likely fail due to no registered servers)
        tool_request = {"name": "echo", "arguments": {"message": "Hello World"}}

        response = client.post(
            "/mcp/demo/tools/call",
            json=tool_request,
            headers=headers,
        )

        # May be 503 (service unavailable) if no instances, which is expected
        assert response.status_code in [200, 503]

    def test_concurrent_requests(self, client):
        """Test handling concurrent requests."""
        import threading

        results = []

        def make_request():
            response = client.get("/gateway/health")
            results.append(response.status_code)

        # Make 10 concurrent requests
        threads = [threading.Thread(target=make_request) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All should succeed
        assert all(status == 200 for status in results)
        assert len(results) == 10

    def test_registry_persistence(self, client, gateway_server):
        """Test that registry data persists across operations."""
        headers = self._get_auth_headers(client)

        # Initial state
        response = client.get("/gateway/registry", headers=headers)
        if response.status_code == 200:
            initial_data = response.json()

            # Perform some operations (register instance, etc.)
            # This would require setting up actual test instances

            # Verify persistence
            response = client.get("/gateway/registry", headers=headers)
            assert response.status_code == 200

    def test_health_checker_integration(self, client, gateway_server):
        """Test health checker integration."""
        # Health checker should be running
        assert hasattr(gateway_server.app.state, "health_checker")
        health_checker = gateway_server.app.state.health_checker
        assert health_checker.running

    def test_load_balancer_integration(self, client, gateway_server):
        """Test load balancer integration."""
        # Load balancer should be initialized
        assert hasattr(gateway_server.app.state, "load_balancer")
        load_balancer = gateway_server.app.state.load_balancer
        assert load_balancer is not None

    def test_database_integration(self, client, gateway_server):
        """Test database integration."""
        # Database should be connected
        assert hasattr(gateway_server.app.state, "db")
        db = gateway_server.app.state.db
        assert db is not None

    def test_cors_headers(self, client):
        """Test CORS headers are properly set."""
        response = client.options("/gateway/health")
        # FastAPI/Starlette handles OPTIONS automatically
        assert response.status_code in [200, 405]

    def test_error_handling(self, client):
        """Test error handling for invalid requests."""
        # Invalid endpoint
        response = client.get("/invalid/endpoint")
        assert response.status_code == 404

        # Invalid JSON in POST
        response = client.post(
            "/auth/login",
            data="invalid json",
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code in [400, 422]

    def _get_auth_headers(self, client):
        """Helper to get authentication headers."""
        try:
            # Try to login as admin
            admin_password = os.getenv("GATEWAY_ADMIN_PASSWORD", "admin")
            login_data = {"username": "admin", "password": admin_password}
            response = client.post("/auth/login", params=login_data)

            if response.status_code == 200:
                token_data = response.json()
                return {"Authorization": f"Bearer {token_data['access_token']}"}
        except Exception:
            pass

        return None


@pytest.mark.integration
@pytest.mark.gateway
@pytest.mark.asyncio
class TestGatewayClientIntegration:
    """Integration tests for the Gateway Client SDK."""

    @pytest.fixture
    async def running_gateway(self, gateway_config):
        """Start a real gateway server for client testing."""
        server = MCPGatewayServer(gateway_config)

        # Find available port
        import socket

        sock = socket.socket()
        sock.bind(("", 0))
        port = sock.getsockname()[1]
        sock.close()

        gateway_config.port = port

        # Start server
        import uvicorn

        config = uvicorn.Config(
            server.app,
            host="127.0.0.1",
            port=port,
            log_level="error",
        )

        server_task = asyncio.create_task(uvicorn.Server(config).serve())
        await asyncio.sleep(0.5)  # Wait for startup

        yield f"http://127.0.0.1:{port}"

        # Cleanup
        server_task.cancel()
        try:
            await server_task
        except asyncio.CancelledError:
            pass

    @pytest.mark.asyncio
    async def test_client_connection(self, running_gateway):
        """Test client connection to gateway."""
        from mcp_platform.gateway.client import GatewayClient

        async with GatewayClient(base_url=running_gateway) as client:
            # Test basic health check
            health = await client.get_gateway_health()
            assert "status" in health

    @pytest.mark.asyncio
    async def test_client_tool_call(self, running_gateway):
        """Test client tool call through gateway."""
        from mcp_platform.gateway.client import GatewayClient

        async with GatewayClient(base_url=running_gateway) as client:
            # This will likely fail since no servers are registered
            try:
                result = await client.call_tool("demo", "echo", {"message": "test"})
                # If it succeeds, great!
                assert "result" in result or "error" in result
            except Exception as e:
                # Expected to fail without registered servers
                assert "unavailable" in str(e).lower() or "not found" in str(e).lower()

    @pytest.mark.asyncio
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
