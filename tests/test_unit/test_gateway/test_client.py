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
        with patch.object(aiohttp, "ClientSession") as mock_session_class:
            mock_session = Mock()
            mock_session.close = AsyncMock()
            mock_session_class.return_value = mock_session

            async with GatewayClient() as client:
                assert client._session is not None
                assert client._session == mock_session

            mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_close_method(self):
        """Test explicit close method."""
        with patch.object(aiohttp, "ClientSession") as mock_session_class:
            mock_session = Mock()
            mock_session.close = AsyncMock()
            mock_session_class.return_value = mock_session

            client = GatewayClient()
            await client.__aenter__()
            await client.close()

            mock_session.close.assert_called_once()

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
    async def test_get_json_success(self):
        """Test successful GET request."""
        mock_response = Mock()
        mock_response.json = AsyncMock(return_value={"result": "success"})
        mock_response.raise_for_status = Mock()

        with patch.object(aiohttp, "ClientSession") as mock_session_class:
            mock_session = Mock()
            mock_session.get = AsyncMock(return_value=mock_response)
            mock_session_class.return_value = mock_session

            client = GatewayClient(api_key="test-key")
            await client.__aenter__()

            result = await client._get_json("/test")

            assert result == {"result": "success"}
            mock_session.get.assert_called_once_with(
                "http://localhost:8080/test",
                headers={"Authorization": "Bearer test-key"},
            )

    @pytest.mark.asyncio
    async def test_post_json_success(self):
        """Test successful POST request."""
        mock_response = Mock()
        mock_response.json = AsyncMock(return_value={"result": "created"})
        mock_response.raise_for_status = Mock()

        with patch.object(aiohttp, "ClientSession") as mock_session_class:
            mock_session = Mock()
            mock_session.post = AsyncMock(return_value=mock_response)
            mock_session_class.return_value = mock_session

            client = GatewayClient(api_key="test-key")
            await client.__aenter__()

            result = await client._post_json("/test", {"data": "value"})

            assert result == {"result": "created"}
            mock_session.post.assert_called_once_with(
                "http://localhost:8080/test",
                json={"data": "value"},
                headers={"Authorization": "Bearer test-key"},
            )

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
            mock_get.assert_called_once_with("/health")

    @pytest.mark.asyncio
    async def test_get_stats(self):
        """Test get stats endpoint."""
        client = GatewayClient()
        with patch.object(client, "_get_json", new_callable=AsyncMock) as mock_get:
            mock_stats = {
                "total_requests": 100,
                "active_connections": 5,
                "uptime": 3600,
            }
            mock_get.return_value = mock_stats

            result = await client.get_stats()

            assert result.total_requests == 100
            mock_get.assert_called_once_with("/stats")

    @pytest.mark.asyncio
    async def test_get_registry(self):
        """Test get registry endpoint."""
        client = GatewayClient()
        with patch.object(client, "_get_json", new_callable=AsyncMock) as mock_get:
            mock_registry = {"templates": {"test": {}}}
            mock_get.return_value = mock_registry

            result = await client.get_registry()

            assert result == mock_registry
            mock_get.assert_called_once_with("/registry")

    @pytest.mark.asyncio
    async def test_list_templates(self):
        """Test list templates endpoint."""
        client = GatewayClient()
        with patch.object(client, "_get_json", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = ["template1", "template2"]

            result = await client.list_templates()

            assert result == ["template1", "template2"]
            mock_get.assert_called_once_with("/templates")

    @pytest.mark.asyncio
    async def test_get_template_health(self):
        """Test get template health endpoint."""
        client = GatewayClient()
        with patch.object(client, "_get_json", new_callable=AsyncMock) as mock_get:
            mock_health = {
                "template_name": "test-template",
                "status": "healthy",
                "instance_count": 3,
            }
            mock_get.return_value = mock_health

            result = await client.get_template_health("test-template")

            assert result.template_name == "test-template"
            mock_get.assert_called_once_with("/templates/test-template/health")

    @pytest.mark.asyncio
    async def test_list_tools(self):
        """Test list tools endpoint."""
        client = GatewayClient()
        with patch.object(client, "_get_json", new_callable=AsyncMock) as mock_get:
            mock_tools = [{"name": "tool1"}, {"name": "tool2"}]
            mock_get.return_value = mock_tools

            result = await client.list_tools("test-template")

            assert result == mock_tools
            mock_get.assert_called_once_with("/templates/test-template/tools")

    @pytest.mark.asyncio
    async def test_call_tool(self):
        """Test call tool endpoint."""
        client = GatewayClient()
        with patch.object(client, "_post_json", new_callable=AsyncMock) as mock_post:
            mock_response = {"result": {"output": "success"}, "error": None}
            mock_post.return_value = mock_response

            result = await client.call_tool(
                "test-template", "test-tool", {"param": "value"}
            )

            assert result.result == {"output": "success"}
            mock_post.assert_called_once_with(
                "/templates/test-template/tools/test-tool",
                {"arguments": {"param": "value"}},
            )

    @pytest.mark.asyncio
    async def test_list_resources(self):
        """Test list resources endpoint."""
        client = GatewayClient()
        with patch.object(client, "_get_json", new_callable=AsyncMock) as mock_get:
            mock_resources = [{"uri": "file://test.txt"}]
            mock_get.return_value = mock_resources

            result = await client.list_resources("test-template")

            assert result == mock_resources
            mock_get.assert_called_once_with("/templates/test-template/resources")

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
                "/templates/test-template/resources/read", {"uri": "file://test.txt"}
            )

    @pytest.mark.asyncio
    async def test_list_prompts(self):
        """Test list prompts endpoint."""
        client = GatewayClient()
        with patch.object(client, "_get_json", new_callable=AsyncMock) as mock_get:
            mock_prompts = [{"name": "prompt1"}]
            mock_get.return_value = mock_prompts

            result = await client.list_prompts("test-template")

            assert result == mock_prompts
            mock_get.assert_called_once_with("/templates/test-template/prompts")

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
                "/templates/test-template/prompts/test-prompt",
                {"arguments": {"param": "value"}},
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
                type("Response", (), {"result": {"output": "success"}, "error": None}),
                GatewayClientError("Tool call failed"),
            ]

            requests = [
                {"template_name": "template1", "tool_name": "tool1", "arguments": {}},
                {"template_name": "template2", "tool_name": "tool2", "arguments": {}},
            ]

            results = await client.call_tools_batch(requests, fail_fast=False)

            assert len(results) == 2
            assert results[0].result == {"output": "success"}
            assert results[1].error is not None

    @pytest.mark.asyncio
    async def test_call_tools_batch_fail_fast(self):
        """Test batch tool calls with fail_fast=True."""
        client = GatewayClient()

        with patch.object(client, "call_tool", new_callable=AsyncMock) as mock_call:
            mock_call.side_effect = [
                type("Response", (), {"result": {"output": "success"}, "error": None}),
                GatewayClientError("Tool call failed"),
            ]

            requests = [
                {"template_name": "template1", "tool_name": "tool1", "arguments": {}},
                {"template_name": "template2", "tool_name": "tool2", "arguments": {}},
            ]

            with pytest.raises(GatewayClientError):
                await client.call_tools_batch(requests, fail_fast=True)


class TestGatewayClientMCPSession:
    """Test gateway client MCP session functionality."""

    @pytest.mark.asyncio
    async def test_create_mcp_session(self):
        """Test MCP session creation."""
        client = GatewayClient()

        with patch("mcp_platform.gateway.client.MCPConnection") as mock_mcp_class:
            mock_mcp = Mock()
            mock_mcp.connect = AsyncMock(return_value=True)
            mock_mcp_class.return_value = mock_mcp

            session = await client.create_mcp_session("test-template")

            assert session is not None
            mock_mcp_class.assert_called_once()
            mock_mcp.connect.assert_called_once()

    @pytest.mark.asyncio
    async def test_mcp_session_context_manager(self):
        """Test MCP session as context manager."""
        client = GatewayClient()

        with patch("mcp_platform.gateway.client.MCPConnection") as mock_mcp_class:
            mock_mcp = Mock()
            mock_mcp.connect = AsyncMock(return_value=True)
            mock_mcp.disconnect = AsyncMock()
            mock_mcp_class.return_value = mock_mcp

            session = await client.create_mcp_session("test-template")

            async with session:
                pass  # Session should be connected

            mock_mcp.disconnect.assert_called_once()


class TestGatewayClientErrorHandling:
    """Test gateway client error handling scenarios."""

    @pytest.mark.asyncio
    async def test_session_not_initialized_error(self):
        """Test error when session is not initialized."""
        client = GatewayClient()

        with pytest.raises(GatewayClientError, match="Client session not initialized"):
            await client._get_json("/test")

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
