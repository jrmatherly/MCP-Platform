"""
Unit tests for the Gateway Client SDK.
"""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest
from aiohttp import ClientResponse, ClientSession
from aiohttp.test_utils import make_mocked_coro

from mcp_platform.gateway.client import (
    GatewayClient,
    GatewayClientError,
    GatewayConnectionPool,
    MCPGatewayConnection,
    call_tool_simple,
)
from mcp_platform.gateway.models import GatewayStatsResponse, ToolCallResponse


class TestGatewayClient:
    """Test GatewayClient functionality."""

    def test_client_initialization(self):
        """Test client initialization with various parameters."""
        # Default initialization
        client = GatewayClient()
        assert client.base_url == "http://localhost:8080"
        assert client.api_key is None

        # Custom initialization
        client = GatewayClient(
            base_url="https://gateway.example.com",
            api_key="mcp_test_key_123",
            timeout=120,
        )
        assert client.base_url == "https://gateway.example.com"
        assert client.api_key == "mcp_test_key_123"
        assert client.timeout.total == 120

    def test_client_closes_properly(self):
        """Test that client closes session properly."""
        client = GatewayClient()
        assert not client._closed

        # After closing
        asyncio.run(client.close())
        assert client._closed

    async def test_context_manager(self):
        """Test client as async context manager."""
        async with GatewayClient() as client:
            assert not client._closed

        assert client._closed

    async def test_request_after_close_raises_error(self):
        """Test that requests after close raise error."""
        client = GatewayClient()
        await client.close()

        with pytest.raises(GatewayClientError, match="Client is closed"):
            await client.health_check()

    @patch("aiohttp.ClientSession.request")
    async def test_health_check(self, mock_request):
        """Test health check endpoint."""
        # Mock response
        mock_response = Mock(spec=ClientResponse)
        mock_response.status = 200
        mock_response.json = make_mocked_coro(
            return_value={
                "status": "healthy",
                "templates": 3,
                "instances": {"total": 10, "healthy": 8},
            }
        )
        mock_response.__aenter__ = make_mocked_coro(return_value=mock_response)
        mock_response.__aexit__ = make_mocked_coro(return_value=None)
        mock_request.return_value = mock_response

        client = GatewayClient()
        try:
            result = await client.health_check()

            assert result["status"] == "healthy"
            assert result["templates"] == 3
            assert result["instances"]["total"] == 10

            # Verify correct endpoint was called
            mock_request.assert_called_once()
            args, kwargs = mock_request.call_args
            assert args[0] == "GET"
            assert args[1] == "http://localhost:8080/gateway/health"
        finally:
            await client.close()

    @patch("aiohttp.ClientSession.request")
    async def test_get_stats(self, mock_request):
        """Test getting gateway statistics."""
        # Mock response
        mock_response = Mock(spec=ClientResponse)
        mock_response.status = 200
        mock_response.json = make_mocked_coro(
            return_value={
                "total_requests": 1000,
                "active_connections": 25,
                "templates": {"demo": {"total_instances": 3}},
                "load_balancer": {"requests_per_instance": {}},
                "health_checker": {"running": True},
            }
        )
        mock_response.__aenter__ = make_mocked_coro(return_value=mock_response)
        mock_response.__aexit__ = make_mocked_coro(return_value=None)
        mock_request.return_value = mock_response

        client = GatewayClient(api_key="mcp_test_key")
        try:
            result = await client.get_stats()

            assert isinstance(result, GatewayStatsResponse)
            assert result.total_requests == 1000
            assert result.active_connections == 25

            # Verify authentication header was included
            mock_request.assert_called_once()
            args, kwargs = mock_request.call_args
            assert "json" not in kwargs  # GET request shouldn't have JSON body
        finally:
            await client.close()

    @patch("aiohttp.ClientSession.request")
    async def test_list_tools(self, mock_request):
        """Test listing tools for a template."""
        # Mock response
        mock_response = Mock(spec=ClientResponse)
        mock_response.status = 200
        mock_response.json = make_mocked_coro(
            return_value={
                "tools": [
                    {"name": "say_hello", "description": "Say hello"},
                    {"name": "get_info", "description": "Get information"},
                ]
            }
        )
        mock_response.__aenter__ = make_mocked_coro(return_value=mock_response)
        mock_response.__aexit__ = make_mocked_coro(return_value=None)
        mock_request.return_value = mock_response

        client = GatewayClient()
        try:
            tools = await client.list_tools("demo")

            assert len(tools) == 2
            assert tools[0]["name"] == "say_hello"
            assert tools[1]["name"] == "get_info"

            # Verify correct endpoint was called
            mock_request.assert_called_once()
            args, kwargs = mock_request.call_args
            assert args[1] == "http://localhost:8080/mcp/demo/tools/list"
        finally:
            await client.close()

    @patch("aiohttp.ClientSession.request")
    async def test_call_tool(self, mock_request):
        """Test calling a tool through the gateway."""
        # Mock response
        mock_response = Mock(spec=ClientResponse)
        mock_response.status = 200
        mock_response.json = make_mocked_coro(
            return_value={
                "content": [{"type": "text", "text": "Hello, World!"}],
                "isError": False,
                "_gateway_info": {"instance_id": "demo-1"},
            }
        )
        mock_response.__aenter__ = make_mocked_coro(return_value=mock_response)
        mock_response.__aexit__ = make_mocked_coro(return_value=None)
        mock_request.return_value = mock_response

        client = GatewayClient()
        try:
            result = await client.call_tool("demo", "say_hello", {"name": "World"})

            assert isinstance(result, ToolCallResponse)
            assert result.content[0]["text"] == "Hello, World!"
            assert result.isError is False

            # Verify correct payload was sent
            mock_request.assert_called_once()
            args, kwargs = mock_request.call_args
            assert args[0] == "POST"
            assert args[1] == "http://localhost:8080/mcp/demo/tools/call"
            assert kwargs["json"] == {
                "name": "say_hello",
                "arguments": {"name": "World"},
            }
        finally:
            await client.close()

    @patch("aiohttp.ClientSession.request")
    async def test_error_handling(self, mock_request):
        """Test error handling for failed requests."""
        # Mock error response
        mock_response = Mock(spec=ClientResponse)
        mock_response.status = 404
        mock_response.text = make_mocked_coro(return_value="Template not found")
        mock_response.__aenter__ = make_mocked_coro(return_value=mock_response)
        mock_response.__aexit__ = make_mocked_coro(return_value=None)
        mock_request.return_value = mock_response

        client = GatewayClient()
        try:
            with pytest.raises(
                GatewayClientError, match="Request failed with status 404"
            ):
                await client.list_tools("nonexistent")
        finally:
            await client.close()

    @patch("aiohttp.ClientSession.request")
    async def test_batch_tool_calls(self, mock_request):
        """Test batch tool calling functionality."""
        # Mock successful responses
        mock_response = Mock(spec=ClientResponse)
        mock_response.status = 200
        mock_response.json = make_mocked_coro(
            return_value={
                "content": [{"type": "text", "text": "Success"}],
                "isError": False,
            }
        )
        mock_response.__aenter__ = make_mocked_coro(return_value=mock_response)
        mock_response.__aexit__ = make_mocked_coro(return_value=None)
        mock_request.return_value = mock_response

        client = GatewayClient()
        try:
            calls = [
                {"template_name": "demo", "tool_name": "tool1", "arguments": {}},
                {"template_name": "demo", "tool_name": "tool2", "arguments": {}},
            ]

            results = await client.call_tools_batch(calls)

            assert len(results) == 2
            assert all(isinstance(r, ToolCallResponse) for r in results)
            assert all(not r.isError for r in results)

            # Should have made 2 requests
            assert mock_request.call_count == 2
        finally:
            await client.close()

    async def test_authentication_headers(self):
        """Test that authentication headers are properly set."""
        client = GatewayClient(api_key="mcp_test_key_123")

        # Check headers in session
        auth_header = client._session.headers.get("Authorization")
        assert auth_header == "Bearer mcp_test_key_123"

        await client.close()


class TestMCPGatewayConnection:
    """Test MCPGatewayConnection functionality."""

    def test_connection_initialization(self):
        """Test connection initialization."""
        connection = MCPGatewayConnection("demo")
        assert connection.template_name == "demo"
        assert connection.gateway_url == "http://localhost:8080"
        assert connection.api_key is None
        assert connection._connection is None

        # With custom parameters
        connection2 = MCPGatewayConnection(
            "filesystem", "https://custom-gateway.com", "mcp_api_key"
        )
        assert connection2.template_name == "filesystem"
        assert connection2.gateway_url == "https://custom-gateway.com"
        assert connection2.api_key == "mcp_api_key"

    async def test_context_manager(self):
        """Test connection as context manager."""
        with patch("mcp_platform.gateway.client.MCPConnection") as mock_mcp:
            mock_mcp_instance = Mock()
            mock_mcp_instance.connect_http_smart = make_mocked_coro(return_value=True)
            mock_mcp_instance.disconnect = make_mocked_coro()
            mock_mcp.return_value = mock_mcp_instance

            async with MCPGatewayConnection("demo") as conn:
                assert conn._connection is not None

            # Should have called disconnect
            mock_mcp_instance.disconnect.assert_called_once()

    async def test_connection_failure(self):
        """Test handling connection failures."""
        with patch("mcp_platform.gateway.client.MCPConnection") as mock_mcp:
            mock_mcp_instance = Mock()
            mock_mcp_instance.connect_http_smart = make_mocked_coro(return_value=False)
            mock_mcp.return_value = mock_mcp_instance

            connection = MCPGatewayConnection("demo")
            success = await connection.connect()

            assert success is False
            assert connection._connection is None

    async def test_operations_require_connection(self):
        """Test that operations require active connection."""
        connection = MCPGatewayConnection("demo")

        with pytest.raises(GatewayClientError, match="Not connected"):
            await connection.list_tools()

        with pytest.raises(GatewayClientError, match="Not connected"):
            await connection.call_tool("test_tool")

    @patch("mcp_platform.gateway.client.MCPConnection")
    async def test_tool_operations(self, mock_mcp):
        """Test tool operations through connection."""
        # Mock MCP connection
        mock_mcp_instance = Mock()
        mock_mcp_instance.connect_http_smart = make_mocked_coro(return_value=True)
        mock_mcp_instance.disconnect = make_mocked_coro()
        mock_mcp_instance.list_tools = make_mocked_coro(
            return_value={"tools": [{"name": "test_tool"}]}
        )
        mock_mcp_instance.call_tool = make_mocked_coro(
            return_value={"content": [{"type": "text", "text": "Result"}]}
        )
        mock_mcp.return_value = mock_mcp_instance

        connection = MCPGatewayConnection("demo")
        await connection.connect()

        try:
            # Test list tools
            tools = await connection.list_tools()
            assert tools == [{"name": "test_tool"}]

            # Test call tool
            result = await connection.call_tool("test_tool", {"arg": "value"})
            assert result["content"][0]["text"] == "Result"

            # Verify MCP methods were called correctly
            mock_mcp_instance.list_tools.assert_called_once()
            mock_mcp_instance.call_tool.assert_called_once_with(
                "test_tool", {"arg": "value"}
            )
        finally:
            await connection.disconnect()


class TestGatewayConnectionPool:
    """Test GatewayConnectionPool functionality."""

    def test_pool_initialization(self):
        """Test connection pool initialization."""
        pool = GatewayConnectionPool()
        assert pool.gateway_url == "http://localhost:8080"
        assert pool.api_key is None
        assert pool.max_connections == 10
        assert pool._pools == {}
        assert pool._semaphores == {}

        # Custom initialization
        pool2 = GatewayConnectionPool(
            "https://custom.com", "api_key", max_connections=20
        )
        assert pool2.gateway_url == "https://custom.com"
        assert pool2.api_key == "api_key"
        assert pool2.max_connections == 20

    async def test_semaphore_creation(self):
        """Test semaphore creation for templates."""
        pool = GatewayConnectionPool(max_connections=5)

        # First access should create semaphore
        semaphore1 = pool._get_semaphore("demo")
        assert semaphore1._value == 5

        # Second access should return same semaphore
        semaphore2 = pool._get_semaphore("demo")
        assert semaphore1 is semaphore2

        # Different template should get different semaphore
        semaphore3 = pool._get_semaphore("filesystem")
        assert semaphore3 is not semaphore1

    @patch("mcp_platform.gateway.client.MCPGatewayConnection")
    async def test_connection_pool_usage(self, mock_connection_class):
        """Test getting connections from pool."""
        # Mock connection
        mock_connection = Mock()
        mock_connection.connect = make_mocked_coro()
        mock_connection_class.return_value = mock_connection

        pool = GatewayConnectionPool()

        # First connection should create new one
        async with pool.get_connection("demo") as conn:
            assert conn is mock_connection
            mock_connection.connect.assert_called_once()

        # Second connection should reuse from pool
        mock_connection.connect.reset_mock()
        async with pool.get_connection("demo") as conn:
            assert conn is mock_connection
            # Connect should not be called again (reused from pool)
            mock_connection.connect.assert_not_called()

    async def test_close_all_connections(self):
        """Test closing all connections in pool."""
        pool = GatewayConnectionPool()

        # Mock some connections in pools
        mock_conn1 = Mock()
        mock_conn1.disconnect = make_mocked_coro()
        mock_conn2 = Mock()
        mock_conn2.disconnect = make_mocked_coro()

        pool._pools["demo"] = [mock_conn1]
        pool._pools["filesystem"] = [mock_conn2]

        await pool.close_all()

        # All connections should be disconnected
        mock_conn1.disconnect.assert_called_once()
        mock_conn2.disconnect.assert_called_once()

        # Pools should be cleared
        assert pool._pools == {}
        assert pool._semaphores == {}


class TestConvenienceFunctions:
    """Test convenience functions."""

    async def test_create_gateway_client(self):
        """Test create_gateway_client function."""
        from mcp_platform.gateway.client import create_gateway_client

        client = await create_gateway_client()
        assert isinstance(client, GatewayClient)
        assert client.base_url == "http://localhost:8080"
        await client.close()

        # With custom parameters
        client2 = await create_gateway_client(
            "https://custom.com", "api_key", timeout=120
        )
        assert client2.base_url == "https://custom.com"
        assert client2.api_key == "api_key"
        await client2.close()

    @patch("mcp_platform.gateway.client.GatewayClient")
    async def test_call_tool_simple(self, mock_client_class):
        """Test call_tool_simple function."""
        # Mock client
        mock_client = Mock()
        mock_client.__aenter__ = make_mocked_coro(return_value=mock_client)
        mock_client.__aexit__ = make_mocked_coro(return_value=None)
        mock_client.call_tool = make_mocked_coro(
            return_value=ToolCallResponse(
                content=[{"type": "text", "text": "Simple result"}], isError=False
            )
        )
        mock_client_class.return_value = mock_client

        result = await call_tool_simple("demo", "test_tool", {"arg": "value"})

        assert isinstance(result, ToolCallResponse)
        assert result.content[0]["text"] == "Simple result"

        # Verify client was created with correct parameters
        mock_client_class.assert_called_once_with("http://localhost:8080", None)
        mock_client.call_tool.assert_called_once_with(
            "demo", "test_tool", {"arg": "value"}
        )


class TestErrorHandling:
    """Test error handling in client SDK."""

    async def test_network_errors(self):
        """Test handling of network errors."""
        with patch("aiohttp.ClientSession.request") as mock_request:
            import aiohttp

            mock_request.side_effect = aiohttp.ClientError("Network error")

            client = GatewayClient()
            try:
                with pytest.raises(
                    GatewayClientError, match="Request failed: Network error"
                ):
                    await client.health_check()
            finally:
                await client.close()

    async def test_timeout_handling(self):
        """Test handling of request timeouts."""
        with patch("aiohttp.ClientSession.request") as mock_request:
            import asyncio

            mock_request.side_effect = asyncio.TimeoutError()

            client = GatewayClient(timeout=1)
            try:
                with pytest.raises(GatewayClientError, match="Request failed"):
                    await client.health_check()
            finally:
                await client.close()

    async def test_batch_error_handling(self):
        """Test error handling in batch operations."""
        client = GatewayClient()

        # Mock one successful and one failed call
        with patch.object(client, "call_tool") as mock_call:
            successful_response = ToolCallResponse(
                content=[{"type": "text", "text": "Success"}], isError=False
            )
            mock_call.side_effect = [successful_response, Exception("Call failed")]

            calls = [
                {"template_name": "demo", "tool_name": "tool1", "arguments": {}},
                {"template_name": "demo", "tool_name": "tool2", "arguments": {}},
            ]

            try:
                results = await client.call_tools_batch(calls)

                assert len(results) == 2
                assert results[0] == successful_response
                assert results[1].isError is True
                assert "Call failed" in results[1].content[0]["text"]
            finally:
                await client.close()


class TestConfigurationAndHeaders:
    """Test client configuration and header handling."""

    def test_base_url_normalization(self):
        """Test base URL normalization."""
        # Trailing slash should be removed
        client = GatewayClient("http://localhost:8080/")
        assert client.base_url == "http://localhost:8080"

        # Multiple trailing slashes
        client2 = GatewayClient("http://localhost:8080///")
        assert client2.base_url == "http://localhost:8080"

    def test_default_headers(self):
        """Test default headers are set correctly."""
        client = GatewayClient()

        headers = client._session.headers
        assert headers["Content-Type"] == "application/json"

    def test_authentication_header(self):
        """Test authentication header is set when API key provided."""
        client = GatewayClient(api_key="mcp_test_key_123")

        headers = client._session.headers
        assert headers["Authorization"] == "Bearer mcp_test_key_123"

    def test_custom_connector_settings(self):
        """Test custom connector settings."""
        client = GatewayClient(max_connections=50, max_connections_per_host=10)

        connector = client._session.connector
        assert connector.limit == 50
        assert connector.limit_per_host == 10
