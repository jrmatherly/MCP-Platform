"""
Unit tests for the Enhanced Gateway Server.
"""

import asyncio
import json
from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from mcp_platform.gateway.auth import AuthManager
from mcp_platform.gateway.database import DatabaseManager
from mcp_platform.gateway.gateway_server import (
    MCPGatewayServer,
    app,
    get_api_key_user,
    get_current_user,
    require_auth,
)
from mcp_platform.gateway.models import (
    APIKey,
    ServerInstance,
    ServerStatus,
    ServerTemplate,
    ToolCallRequest,
    ToolCallResponse,
    User,
    UserRole,
)
from mcp_platform.gateway.registry import GatewayRegistry


class TestMCPGatewayServer:
    """Test MCPGatewayServer functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.db_manager = Mock(spec=DatabaseManager)
        self.auth_manager = Mock(spec=AuthManager)
        self.registry = Mock(spec=GatewayRegistry)

        self.server = MCPGatewayServer(
            host="localhost",
            port=8080,
            db_manager=self.db_manager,
            auth_manager=self.auth_manager,
            registry=self.registry,
        )

    def test_server_initialization(self):
        """Test server initialization."""
        server = MCPGatewayServer()

        # Should have default values
        assert server.host == "0.0.0.0"
        assert server.port == 8080
        assert server.db_manager is not None
        assert server.auth_manager is not None
        assert server.registry is not None

    async def test_server_startup(self):
        """Test server startup process."""
        # Mock component initialization
        self.db_manager.initialize = AsyncMock()
        self.auth_manager.initialize = AsyncMock()
        self.registry.initialize = AsyncMock()

        await self.server.startup()

        # All components should be initialized
        self.db_manager.initialize.assert_called_once()
        self.auth_manager.initialize.assert_called_once()
        self.registry.initialize.assert_called_once()

    async def test_server_shutdown(self):
        """Test server shutdown process."""
        # Mock component cleanup
        self.registry.cleanup = AsyncMock()
        self.db_manager.close = AsyncMock()

        await self.server.shutdown()

        # Components should be cleaned up
        self.registry.cleanup.assert_called_once()
        self.db_manager.close.assert_called_once()

    def test_dependency_injection(self):
        """Test dependency injection setup."""
        # Dependencies should be properly injected
        assert hasattr(self.server, "get_db_manager")
        assert hasattr(self.server, "get_auth_manager")
        assert hasattr(self.server, "get_registry")

        # Test dependency functions
        assert self.server.get_db_manager() is self.db_manager
        assert self.server.get_auth_manager() is self.auth_manager
        assert self.server.get_registry() is self.registry


class TestAPIEndpoints:
    """Test API endpoints using TestClient."""

    def setup_method(self):
        """Set up test client."""
        # Mock dependencies
        self.db_manager = Mock(spec=DatabaseManager)
        self.auth_manager = Mock(spec=AuthManager)
        self.registry = Mock(spec=GatewayRegistry)

        # Override dependencies in app
        app.dependency_overrides[DatabaseManager] = lambda: self.db_manager
        app.dependency_overrides[AuthManager] = lambda: self.auth_manager
        app.dependency_overrides[GatewayRegistry] = lambda: self.registry

        self.client = TestClient(app)

    def teardown_method(self):
        """Clean up after tests."""
        app.dependency_overrides.clear()

    def test_health_endpoint(self):
        """Test health check endpoint."""
        # Mock registry stats
        self.registry.get_stats = AsyncMock(
            return_value={
                "templates": {"demo": {"total_instances": 2}},
                "instances": {"demo-1": {"status": "running"}},
                "total_requests": 100,
            }
        )

        response = self.client.get("/gateway/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "templates" in data
        assert "instances" in data

    def test_stats_endpoint_requires_auth(self):
        """Test that stats endpoint requires authentication."""
        response = self.client.get("/gateway/stats")
        assert response.status_code == 401

    def test_stats_endpoint_with_auth(self):
        """Test stats endpoint with authentication."""
        # Mock user authentication
        test_user = User(
            id="user-1",
            username="testuser",
            email="test@example.com",
            role=UserRole.USER,
        )

        with patch(
            "mcp_platform.gateway.gateway_server_v2.get_current_user",
            return_value=test_user,
        ):
            self.registry.get_stats = AsyncMock(
                return_value={
                    "total_requests": 1000,
                    "active_connections": 25,
                    "templates": {},
                    "load_balancer": {"requests_per_instance": {}},
                    "health_checker": {"running": True},
                }
            )

            response = self.client.get(
                "/gateway/stats", headers={"Authorization": "Bearer test_token"}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["total_requests"] == 1000

    def test_register_template_endpoint(self):
        """Test template registration endpoint."""
        test_template = {
            "name": "test_template",
            "command": ["python", "-m", "test_server"],
            "args": [],
            "env": {},
            "description": "Test template",
            "category": "testing",
        }

        # Mock admin user
        admin_user = User(
            id="admin-1",
            username="admin",
            email="admin@example.com",
            role=UserRole.ADMIN,
        )

        # Mock template registration
        registered_template = ServerTemplate(**test_template)
        self.registry.register_template = AsyncMock(return_value=registered_template)

        with patch(
            "mcp_platform.gateway.gateway_server_v2.get_current_user",
            return_value=admin_user,
        ):
            response = self.client.post(
                "/gateway/templates",
                json=test_template,
                headers={"Authorization": "Bearer admin_token"},
            )

            assert response.status_code == 201
            data = response.json()
            assert data["name"] == "test_template"

    def test_register_template_requires_admin(self):
        """Test that template registration requires admin role."""
        # Mock regular user (not admin)
        regular_user = User(
            id="user-1", username="user", email="user@example.com", role=UserRole.USER
        )

        test_template = {
            "name": "test_template",
            "command": ["python"],
            "args": [],
            "env": {},
        }

        with patch(
            "mcp_platform.gateway.gateway_server_v2.get_current_user",
            return_value=regular_user,
        ):
            response = self.client.post(
                "/gateway/templates",
                json=test_template,
                headers={"Authorization": "Bearer user_token"},
            )

            assert response.status_code == 403

    def test_list_templates_endpoint(self):
        """Test listing templates endpoint."""
        templates = {
            "demo": ServerTemplate(
                name="demo", command=["python", "-m", "demo"], args=[], env={}
            ),
            "filesystem": ServerTemplate(
                name="filesystem",
                command=["python", "-m", "filesystem"],
                args=[],
                env={},
            ),
        }

        self.registry.templates = templates

        response = self.client.get("/gateway/templates")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert any(t["name"] == "demo" for t in data)
        assert any(t["name"] == "filesystem" for t in data)

    def test_create_instance_endpoint(self):
        """Test instance creation endpoint."""
        test_user = User(
            id="user-1",
            username="testuser",
            email="test@example.com",
            role=UserRole.USER,
        )

        # Mock instance creation
        created_instance = ServerInstance(
            id="demo-1", template_name="demo", port=8080, status=ServerStatus.CREATED
        )
        self.registry.create_instance = AsyncMock(return_value=created_instance)

        with patch(
            "mcp_platform.gateway.gateway_server_v2.get_current_user",
            return_value=test_user,
        ):
            response = self.client.post(
                "/gateway/instances",
                json={"template_name": "demo"},
                headers={"Authorization": "Bearer test_token"},
            )

            assert response.status_code == 201
            data = response.json()
            assert data["template_name"] == "demo"
            assert data["status"] == "created"

    def test_list_instances_endpoint(self):
        """Test listing instances endpoint."""
        instances = {
            "demo-1": ServerInstance(
                id="demo-1",
                template_name="demo",
                port=8080,
                status=ServerStatus.RUNNING,
            ),
            "demo-2": ServerInstance(
                id="demo-2",
                template_name="demo",
                port=8081,
                status=ServerStatus.RUNNING,
            ),
        }

        self.registry.instances = instances

        test_user = User(
            id="user-1",
            username="testuser",
            email="test@example.com",
            role=UserRole.USER,
        )

        with patch(
            "mcp_platform.gateway.gateway_server_v2.get_current_user",
            return_value=test_user,
        ):
            response = self.client.get(
                "/gateway/instances", headers={"Authorization": "Bearer test_token"}
            )

            assert response.status_code == 200
            data = response.json()
            assert len(data) == 2

    def test_call_tool_endpoint(self):
        """Test tool calling endpoint."""
        # Mock tool call
        self.registry.call_tool = AsyncMock(
            return_value=ToolCallResponse(
                content=[{"type": "text", "text": "Hello, World!"}],
                isError=False,
                _meta={"instance_id": "demo-1"},
            )
        )

        test_user = User(
            id="user-1",
            username="testuser",
            email="test@example.com",
            role=UserRole.USER,
        )

        tool_call = {"name": "say_hello", "arguments": {"name": "World"}}

        with patch(
            "mcp_platform.gateway.gateway_server_v2.get_current_user",
            return_value=test_user,
        ):
            response = self.client.post(
                "/mcp/demo/tools/call",
                json=tool_call,
                headers={"Authorization": "Bearer test_token"},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["content"][0]["text"] == "Hello, World!"
            assert data["isError"] is False

    def test_list_tools_endpoint(self):
        """Test listing tools endpoint."""
        # Mock tools list
        self.registry.list_tools = AsyncMock(
            return_value=[
                {"name": "say_hello", "description": "Say hello"},
                {"name": "get_time", "description": "Get current time"},
            ]
        )

        response = self.client.get("/mcp/demo/tools/list")

        assert response.status_code == 200
        data = response.json()
        assert len(data["tools"]) == 2
        assert data["tools"][0]["name"] == "say_hello"

    def test_api_key_authentication(self):
        """Test API key authentication."""
        # Mock API key user
        api_key_user = User(
            id="api-user-1",
            username="api_user",
            email="api@example.com",
            role=UserRole.USER,
        )

        with patch(
            "mcp_platform.gateway.gateway_server_v2.get_api_key_user",
            return_value=api_key_user,
        ):
            response = self.client.get(
                "/gateway/stats", headers={"X-API-Key": "mcp_api_key_123"}
            )

            # Should not be 401 (unauthorized)
            assert response.status_code != 401


class TestAuthenticationDependencies:
    """Test authentication dependency functions."""

    def setup_method(self):
        """Set up test fixtures."""
        self.auth_manager = Mock(spec=AuthManager)

    async def test_get_current_user_valid_token(self):
        """Test getting current user with valid token."""
        # Mock token validation
        test_user = User(
            id="user-1",
            username="testuser",
            email="test@example.com",
            role=UserRole.USER,
        )
        self.auth_manager.validate_token = AsyncMock(return_value=test_user)

        # Test dependency function
        user = await get_current_user("Bearer valid_token", self.auth_manager)

        assert user == test_user
        self.auth_manager.validate_token.assert_called_once_with("valid_token")

    async def test_get_current_user_invalid_token(self):
        """Test getting current user with invalid token."""
        # Mock token validation failure
        self.auth_manager.validate_token = AsyncMock(return_value=None)

        # Should raise HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user("Bearer invalid_token", self.auth_manager)

        assert exc_info.value.status_code == 401

    async def test_get_current_user_missing_bearer(self):
        """Test getting current user with missing bearer prefix."""
        with pytest.raises(HTTPException) as exc_info:
            await get_current_user("invalid_token", self.auth_manager)

        assert exc_info.value.status_code == 401

    async def test_get_api_key_user_valid_key(self):
        """Test getting user with valid API key."""
        test_user = User(
            id="api-user-1",
            username="api_user",
            email="api@example.com",
            role=UserRole.USER,
        )
        self.auth_manager.validate_api_key = AsyncMock(return_value=test_user)

        user = await get_api_key_user("mcp_api_key_123", self.auth_manager)

        assert user == test_user
        self.auth_manager.validate_api_key.assert_called_once_with("mcp_api_key_123")

    async def test_get_api_key_user_invalid_key(self):
        """Test getting user with invalid API key."""
        self.auth_manager.validate_api_key = AsyncMock(return_value=None)

        with pytest.raises(HTTPException) as exc_info:
            await get_api_key_user("invalid_key", self.auth_manager)

        assert exc_info.value.status_code == 401

    async def test_require_auth_admin_role(self):
        """Test admin role requirement."""
        admin_user = User(
            id="admin-1",
            username="admin",
            email="admin@example.com",
            role=UserRole.ADMIN,
        )

        # Should not raise exception for admin
        result = await require_auth(admin_user, UserRole.ADMIN)
        assert result == admin_user

        # Should raise exception for non-admin
        regular_user = User(
            id="user-1", username="user", email="user@example.com", role=UserRole.USER
        )

        with pytest.raises(HTTPException) as exc_info:
            await require_auth(regular_user, UserRole.ADMIN)

        assert exc_info.value.status_code == 403


class TestErrorHandling:
    """Test error handling in server endpoints."""

    def setup_method(self):
        """Set up test client."""
        # Mock dependencies
        self.db_manager = Mock(spec=DatabaseManager)
        self.auth_manager = Mock(spec=AuthManager)
        self.registry = Mock(spec=GatewayRegistry)

        # Override dependencies in app
        app.dependency_overrides[DatabaseManager] = lambda: self.db_manager
        app.dependency_overrides[AuthManager] = lambda: self.auth_manager
        app.dependency_overrides[GatewayRegistry] = lambda: self.registry

        self.client = TestClient(app)

    def teardown_method(self):
        """Clean up after tests."""
        app.dependency_overrides.clear()

    def test_template_not_found_error(self):
        """Test template not found error handling."""
        self.registry.call_tool = AsyncMock(
            side_effect=Exception("Template 'nonexistent' not found")
        )

        test_user = User(
            id="user-1",
            username="testuser",
            email="test@example.com",
            role=UserRole.USER,
        )

        with patch(
            "mcp_platform.gateway.gateway_server_v2.get_current_user",
            return_value=test_user,
        ):
            response = self.client.post(
                "/mcp/nonexistent/tools/call",
                json={"name": "test_tool", "arguments": {}},
                headers={"Authorization": "Bearer test_token"},
            )

            assert response.status_code == 500  # Internal server error

    def test_validation_error_handling(self):
        """Test validation error handling."""
        test_user = User(
            id="user-1",
            username="testuser",
            email="test@example.com",
            role=UserRole.USER,
        )

        with patch(
            "mcp_platform.gateway.gateway_server_v2.get_current_user",
            return_value=test_user,
        ):
            # Invalid JSON payload
            response = self.client.post(
                "/gateway/instances",
                json={},  # Missing required template_name
                headers={"Authorization": "Bearer test_token"},
            )

            assert response.status_code == 422  # Validation error

    def test_database_error_handling(self):
        """Test database error handling."""
        # Mock database error
        self.registry.get_stats = AsyncMock(
            side_effect=Exception("Database connection failed")
        )

        test_user = User(
            id="user-1",
            username="testuser",
            email="test@example.com",
            role=UserRole.USER,
        )

        with patch(
            "mcp_platform.gateway.gateway_server_v2.get_current_user",
            return_value=test_user,
        ):
            response = self.client.get(
                "/gateway/stats", headers={"Authorization": "Bearer test_token"}
            )

            assert response.status_code == 500


class TestMiddleware:
    """Test middleware functionality."""

    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)

    def test_cors_middleware(self):
        """Test CORS middleware."""
        response = self.client.options("/gateway/health")

        # Should include CORS headers
        assert "access-control-allow-origin" in response.headers
        assert "access-control-allow-methods" in response.headers

    def test_request_logging_middleware(self):
        """Test request logging middleware."""
        # Mock logging
        with patch("mcp_platform.gateway.gateway_server_v2.logger") as mock_logger:
            response = self.client.get("/gateway/health")

            # Should log request
            assert mock_logger.info.called

    def test_rate_limiting_headers(self):
        """Test rate limiting headers are included."""
        response = self.client.get("/gateway/health")

        # Should include rate limiting info (if implemented)
        # This is a placeholder for future rate limiting implementation
        assert response.status_code == 200


class TestWebSocketEndpoints:
    """Test WebSocket endpoint functionality."""

    def test_websocket_connection(self):
        """Test WebSocket connection endpoint."""
        # Mock WebSocket authentication
        with patch(
            "mcp_platform.gateway.gateway_server_v2.get_current_user"
        ) as mock_auth:
            test_user = User(
                id="user-1",
                username="testuser",
                email="test@example.com",
                role=UserRole.USER,
            )
            mock_auth.return_value = test_user

            # Note: WebSocket testing requires special setup
            # This is a placeholder for WebSocket endpoint tests
            # In practice, you'd use pytest-asyncio and WebSocket test clients
            pass

    def test_websocket_authentication_required(self):
        """Test that WebSocket connections require authentication."""
        # This would test WebSocket authentication
        # Implementation depends on how WebSocket auth is handled
        pass


class TestServerConfiguration:
    """Test server configuration options."""

    def test_server_with_custom_config(self):
        """Test server with custom configuration."""
        server = MCPGatewayServer(host="custom.host", port=9090, debug=True)

        assert server.host == "custom.host"
        assert server.port == 9090

    def test_server_with_ssl_config(self):
        """Test server with SSL configuration."""
        server = MCPGatewayServer(
            ssl_keyfile="/path/to/key.pem", ssl_certfile="/path/to/cert.pem"
        )

        assert server.ssl_keyfile == "/path/to/key.pem"
        assert server.ssl_certfile == "/path/to/cert.pem"

    async def test_graceful_shutdown(self):
        """Test graceful shutdown process."""
        server = MCPGatewayServer()

        # Mock components
        server.registry = Mock()
        server.registry.cleanup = AsyncMock()
        server.db_manager = Mock()
        server.db_manager.close = AsyncMock()

        # Test shutdown
        await server.shutdown()

        # Should clean up all components
        server.registry.cleanup.assert_called_once()
        server.db_manager.close.assert_called_once()


class TestOpenAPIDocumentation:
    """Test OpenAPI documentation generation."""

    def setup_method(self):
        """Set up test client."""
        self.client = TestClient(app)

    def test_openapi_schema_generation(self):
        """Test OpenAPI schema generation."""
        response = self.client.get("/openapi.json")

        assert response.status_code == 200
        schema = response.json()

        # Should have basic OpenAPI structure
        assert "openapi" in schema
        assert "info" in schema
        assert "paths" in schema

    def test_docs_endpoint(self):
        """Test interactive docs endpoint."""
        response = self.client.get("/docs")

        assert response.status_code == 200
        assert "Swagger UI" in response.text

    def test_redoc_endpoint(self):
        """Test ReDoc documentation endpoint."""
        response = self.client.get("/redoc")

        assert response.status_code == 200
        assert "ReDoc" in response.text
