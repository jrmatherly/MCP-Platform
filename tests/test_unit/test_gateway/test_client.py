"""
Comprehensive unit tests for mcp_platform.gateway.client module.

Tests cover gateway client functionality, connection management, API calls,
error handling, and session management.
"""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import aiohttp
import pytest

from mcp_platform.gateway.client import GatewayClient, GatewayClientError


class TestGatewayClientError:
    """Test gateway client error handling."""

    def test_gateway_client_error_creation(self):
        """Test GatewayClientError exception creation."""
        error = GatewayClientError("Test error message")
        assert str(error) == "Test error message"
        assert isinstance(error, Exception)

    def test_gateway_client_error_inheritance(self):
        """Test GatewayClientError inheritance."""
        error = GatewayClientError("Test error")
        assert isinstance(error, Exception)
        assert error.__class__.__name__ == "GatewayClientError"


class TestGatewayClient:
    """Test gateway client core functionality."""

    def test_gateway_client_initialization_defaults(self):
        """Test gateway client initialization with default values."""
        client = GatewayClient()
        assert client.base_url == "http://localhost:8080"
        assert client.api_key is None
        assert client._session is None

    def test_gateway_client_initialization_custom(self):
        """Test gateway client initialization with custom values."""
        client = GatewayClient(
            base_url="https://example.com:9000/",
            api_key="test-key",
            timeout=120,
            max_connections=50,
        )
        assert client.base_url == "https://example.com:9000"
        assert client.api_key == "test-key"

    def test_gateway_client_base_url_normalization(self):
        """Test base URL trailing slash removal."""
        client = GatewayClient(base_url="http://localhost:8080/")
        assert client.base_url == "http://localhost:8080"

    @pytest.mark.asyncio
    async def test_context_manager_lifecycle(self):
        """Test gateway client context manager lifecycle."""
        client = GatewayClient()

        async with client:
            # Session should be created when entering context
            assert client._session is not None
            assert not client._closed

        # Session should be closed when exiting context
        assert client._closed

    @pytest.mark.asyncio
    async def test_close_method(self):
        """Test explicit close method."""
        client = GatewayClient()

        # Ensure session exists
        await client._ensure_session()
        assert client._session is not None
        assert not client._closed

        # Close should set _closed flag
        await client.close()
        assert client._closed

    @pytest.mark.asyncio
    async def test_headers_with_api_key(self):
        """Test that API key is included in headers."""
        client = GatewayClient(api_key="test-key")
        headers = client._get_headers()
        assert headers["Authorization"] == "Bearer test-key"

    @pytest.mark.asyncio
    async def test_headers_without_api_key(self):
        """Test headers when no API key is provided."""
        client = GatewayClient()
        headers = client._get_headers()
        assert "Authorization" not in headers


class TestGatewayClientRequests:
    """Test gateway client HTTP request functionality."""

    @pytest.mark.asyncio
    async def test_request_method_exists(self):
        """Test that request methods are available."""
        client = GatewayClient()

        # Just test that the methods exist and can be called with patch
        with patch.object(client, "_get_json", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"status": "ok"}
            result = await client.health_check()
            assert result == {"status": "ok"}

    @pytest.mark.asyncio
    async def test_post_method_exists(self):
        """Test that POST methods are available."""
        client = GatewayClient()

        # Just test that the methods exist and can be called with patch
        with patch.object(client, "_post_json", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = {"content": []}
            result = await client.call_tool("template", "tool", {})
            assert result.content == []

    @pytest.mark.asyncio
    async def test_request_error_handling(self):
        """Test request error handling."""
        with patch.object(aiohttp, "ClientSession") as mock_session_class:
            mock_session = Mock()
            mock_session.get = AsyncMock(
                side_effect=aiohttp.ClientError("Connection failed")
            )
            mock_session_class.return_value = mock_session

            client = GatewayClient()
            await client.__aenter__()

            with pytest.raises(GatewayClientError, match="Request failed"):
                await client._get_json("/test")


class TestGatewayClientAPIEndpoints:
    """Test gateway client API endpoint methods."""

    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test health check endpoint."""
        client = GatewayClient()
        with patch.object(client, "_get_json", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"status": "healthy"}

            result = await client.health_check()

            assert result == {"status": "healthy"}
            mock_get.assert_called_once_with("/gateway/health")

    @pytest.mark.asyncio
    async def test_get_stats(self):
        """Test get stats endpoint."""
        client = GatewayClient()
        with patch.object(client, "_get_json", new_callable=AsyncMock) as mock_get:
            mock_stats = {
                "total_requests": 100,
                "active_connections": 5,
                "uptime": 3600,
                "templates": {},
                "load_balancer": {},
                "health_checker": {},
            }
            mock_get.return_value = mock_stats

            result = await client.get_stats()

            assert result.total_requests == 100
            mock_get.assert_called_once_with("/gateway/stats")

    @pytest.mark.asyncio
    async def test_get_registry(self):
        """Test get registry endpoint."""
        client = GatewayClient()
        with patch.object(client, "_get_json", new_callable=AsyncMock) as mock_get:
            mock_registry = {"templates": {"test": {}}}
            mock_get.return_value = mock_registry

            result = await client.get_registry()

            assert result == mock_registry
            mock_get.assert_called_once_with("/gateway/registry")

    @pytest.mark.asyncio
    async def test_list_templates(self):
        """Test list templates endpoint."""
        client = GatewayClient()
        with patch.object(client, "_get_json", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = {"templates": ["template1", "template2"]}

            result = await client.list_templates()

            assert result == ["template1", "template2"]
            mock_get.assert_called_once_with("/gateway/templates")

    @pytest.mark.asyncio
    async def test_get_template_health(self):
        """Test get template health endpoint."""
        client = GatewayClient()
        with patch.object(client, "_get_json", new_callable=AsyncMock) as mock_get:
            mock_health = {
                "status": "healthy",
                "healthy_instances": 3,
                "total_instances": 3,
                "instances": [],
            }
            mock_get.return_value = mock_health

            result = await client.get_template_health("test-template")

            assert result.status == "healthy"
            assert result.total_instances == 3
            mock_get.assert_called_once_with("/mcp/test-template/health")

    @pytest.mark.asyncio
    async def test_list_tools(self):
        """Test list tools endpoint."""
        client = GatewayClient()
        with patch.object(client, "_get_json", new_callable=AsyncMock) as mock_get:
            mock_tools = {"tools": [{"name": "tool1"}, {"name": "tool2"}]}
            mock_get.return_value = mock_tools

            result = await client.list_tools("test-template")

            assert result == [{"name": "tool1"}, {"name": "tool2"}]
            mock_get.assert_called_once_with("/mcp/test-template/tools/list")

    @pytest.mark.asyncio
    async def test_call_tool(self):
        """Test call tool endpoint."""
        client = GatewayClient()
        with patch.object(client, "_post_json", new_callable=AsyncMock) as mock_post:
            mock_response = {
                "result": {"output": "success"},
                "error": None,
                "content": [],
            }
            mock_post.return_value = mock_response

            result = await client.call_tool(
                "test-template", "test-tool", {"param": "value"}
            )

            assert result.content == []
            mock_post.assert_called_once_with(
                "/mcp/test-template/tools/call",
                {"name": "test-tool", "arguments": {"param": "value"}},
            )

    @pytest.mark.asyncio
    async def test_list_resources(self):
        """Test list resources endpoint."""
        client = GatewayClient()
        with patch.object(client, "_get_json", new_callable=AsyncMock) as mock_get:
            mock_resources = {"resources": [{"uri": "file://test.txt"}]}
            mock_get.return_value = mock_resources

            result = await client.list_resources("test-template")

            assert result == [{"uri": "file://test.txt"}]
            mock_get.assert_called_once_with("/mcp/test-template/resources/list")

    @pytest.mark.asyncio
    async def test_read_resource(self):
        """Test read resource endpoint."""
        client = GatewayClient()
        with patch.object(client, "_post_json", new_callable=AsyncMock) as mock_post:
            mock_content = {"contents": [{"text": "file content"}]}
            mock_post.return_value = mock_content

            result = await client.read_resource("test-template", "file://test.txt")

            assert result == mock_content
            mock_post.assert_called_once_with(
                "/mcp/test-template/resources/read", {"uri": "file://test.txt"}
            )

    @pytest.mark.asyncio
    async def test_list_prompts(self):
        """Test list prompts endpoint."""
        client = GatewayClient()
        with patch.object(client, "_get_json", new_callable=AsyncMock) as mock_get:
            mock_prompts = {"prompts": [{"name": "prompt1"}]}
            mock_get.return_value = mock_prompts

            result = await client.list_prompts("test-template")

            assert result == [{"name": "prompt1"}]
            mock_get.assert_called_once_with("/mcp/test-template/prompts/list")

    @pytest.mark.asyncio
    async def test_get_prompt(self):
        """Test get prompt endpoint."""
        client = GatewayClient()
        with patch.object(client, "_post_json", new_callable=AsyncMock) as mock_post:
            mock_prompt = {
                "description": "Test prompt",
                "messages": [
                    {"role": "user", "content": {"type": "text", "text": "Hello"}}
                ],
            }
            mock_post.return_value = mock_prompt

            result = await client.get_prompt(
                "test-template", "test-prompt", {"param": "value"}
            )

            assert result == mock_prompt
            mock_post.assert_called_once_with(
                "/mcp/test-template/prompts/get",
                {"name": "test-prompt", "arguments": {"param": "value"}},
            )


class TestGatewayClientBatchOperations:
    """Test gateway client batch operation functionality."""

    @pytest.mark.asyncio
    async def test_call_tools_batch_success(self):
        """Test successful batch tool calls."""
        client = GatewayClient()

        # Mock individual tool calls
        mock_results = [
            {"result": {"output": "result1"}, "error": None},
            {"result": {"output": "result2"}, "error": None},
        ]

        with patch.object(client, "call_tool", new_callable=AsyncMock) as mock_call:
            mock_call.side_effect = [
                type("Response", (), {"result": r["result"], "error": r["error"]})
                for r in mock_results
            ]

            requests = [
                {"template_name": "template1", "tool_name": "tool1", "arguments": {}},
                {"template_name": "template2", "tool_name": "tool2", "arguments": {}},
            ]

            results = await client.call_tools_batch(requests)

            assert len(results) == 2
            assert results[0].result == {"output": "result1"}
            assert results[1].result == {"output": "result2"}

    @pytest.mark.asyncio
    async def test_call_tools_batch_with_errors(self):
        """Test batch tool calls with some errors."""
        client = GatewayClient()

        with patch.object(client, "call_tool", new_callable=AsyncMock) as mock_call:
            mock_call.side_effect = [
                type(
                    "Response", (), {"content": [{"text": "success"}], "isError": False}
                ),
                type("Response", (), {"content": [], "isError": True}),
            ]

            requests = [
                {"template_name": "template1", "tool_name": "tool1", "arguments": {}},
                {"template_name": "template2", "tool_name": "tool2", "arguments": {}},
            ]

            results = await client.call_tools_batch(requests)

            assert len(results) == 2
            assert results[0].content == [{"text": "success"}]
            assert results[1].isError is True


class TestGatewayClientErrorHandling:
    """Test gateway client error handling scenarios."""

    @pytest.mark.asyncio
    async def test_http_error_handling(self):
        """Test HTTP error response handling."""
        mock_response = Mock()
        mock_response.raise_for_status = Mock(
            side_effect=aiohttp.ClientResponseError(
                request_info=Mock(), history=(), status=404
            )
        )

        with patch.object(aiohttp, "ClientSession") as mock_session_class:
            mock_session = Mock()
            mock_session.get = AsyncMock(return_value=mock_response)
            mock_session_class.return_value = mock_session

            client = GatewayClient()
            await client.__aenter__()

            with pytest.raises(GatewayClientError, match="Request failed"):
                await client._get_json("/test")

    @pytest.mark.asyncio
    async def test_timeout_error_handling(self):
        """Test timeout error handling."""
        with patch.object(aiohttp, "ClientSession") as mock_session_class:
            mock_session = Mock()
            mock_session.get = AsyncMock(side_effect=asyncio.TimeoutError())
            mock_session_class.return_value = mock_session

            client = GatewayClient()
            await client.__aenter__()

            with pytest.raises(GatewayClientError, match="Request failed"):
                await client._get_json("/test")
