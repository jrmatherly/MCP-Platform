"""
MCP Client integration for the Gateway.

Provides a Python SDK for programmatic access to the gateway with connection pooling,
session management, and native MCP protocol support.
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any

import aiohttp
from aiohttp import ClientSession, ClientTimeout

from ..core.mcp_connection import MCPConnection
from .models import GatewayStatsResponse, HealthCheckResponse, ToolCallResponse

logger = logging.getLogger(__name__)


class GatewayClientError(Exception):
    """Gateway client related errors."""


class GatewayClient:
    """Async client for MCP Gateway with connection pooling and session management."""

    def __init__(
        self,
        base_url: str = "http://localhost:8080",
        api_key: str | None = None,
        timeout: int = 60,
        max_connections: int = 100,
        max_connections_per_host: int = 30,
    ):
        """
        Initialize gateway client.

        Args:
            base_url: Gateway base URL
            api_key: API key for authentication
            timeout: Request timeout in seconds
            max_connections: Maximum total connections
            max_connections_per_host: Maximum connections per host
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = ClientTimeout(total=timeout)
        self.max_connections = max_connections
        self.max_connections_per_host = max_connections_per_host

        # Session will be created lazily
        self._session: ClientSession | None = None
        self._closed = False

    def _get_headers(self) -> dict[str, str]:
        """Get request headers."""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    async def _ensure_session(self):
        """Ensure session is created."""
        if self._session is None and not self._closed:
            # Connection pooling configuration
            connector = aiohttp.TCPConnector(
                limit=self.max_connections,
                limit_per_host=self.max_connections_per_host,
                enable_cleanup_closed=True,
            )

            self._session = ClientSession(
                connector=connector,
                timeout=self.timeout,
                headers=self._get_headers(),
            )

    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_session()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    async def close(self):
        """Close the client session."""
        if not self._closed and self._session is not None:
            await self._session.close()
        self._closed = True

    def _check_closed(self):
        """Check if client is closed."""
        if self._closed:
            raise GatewayClientError("Client is closed")

    async def _request(self, method: str, path: str, **kwargs) -> aiohttp.ClientResponse:
        """Make HTTP request to gateway."""
        self._check_closed()
        await self._ensure_session()

        url = f"{self.base_url}{path}"
        try:
            response = await self._session.request(method, url, **kwargs)
            return response
        except aiohttp.ClientError as e:
            raise GatewayClientError(f"Request failed: {e}")

    async def _get_json(self, path: str, **kwargs) -> dict[str, Any]:
        """Make GET request and return JSON."""
        async with await self._request("GET", path, **kwargs) as response:
            if response.status >= 400:
                text = await response.text()
                raise GatewayClientError(
                    f"Request failed with status {response.status}: {text}"
                )
            return await response.json()

    async def _post_json(
        self, path: str, data: dict[str, Any], **kwargs
    ) -> dict[str, Any]:
        """Make POST request with JSON and return JSON."""
        async with await self._request("POST", path, json=data, **kwargs) as response:
            if response.status >= 400:
                text = await response.text()
                raise GatewayClientError(
                    f"Request failed with status {response.status}: {text}"
                )
            return await response.json()

    # Gateway Management

    async def health_check(self) -> dict[str, Any]:
        """Check gateway health."""
        return await self._get_json("/gateway/health")

    async def get_stats(self) -> GatewayStatsResponse:
        """Get gateway statistics."""
        data = await self._get_json("/gateway/stats")
        return GatewayStatsResponse(**data)

    async def get_registry(self) -> dict[str, Any]:
        """Get server registry information."""
        return await self._get_json("/gateway/registry")

    # Template Management

    async def list_templates(self) -> list[str]:
        """List available templates."""
        data = await self._get_json("/gateway/templates")
        return data.get("templates", [])

    async def get_template_health(self, template_name: str) -> HealthCheckResponse:
        """Get health status for a specific template."""
        data = await self._get_json(f"/mcp/{template_name}/health")
        return HealthCheckResponse(**data)

    # Tool Operations

    async def list_tools(self, template_name: str) -> list[dict[str, Any]]:
        """List tools for a template."""
        data = await self._get_json(f"/mcp/{template_name}/tools/list")
        return data.get("tools", [])

    async def call_tool(
        self,
        template_name: str,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
    ) -> ToolCallResponse:
        """Call a tool through the gateway."""
        payload = {
            "name": tool_name,
            "arguments": arguments or {},
        }
        data = await self._post_json(f"/mcp/{template_name}/tools/call", payload)
        return ToolCallResponse(**data)

    # Resource Operations

    async def list_resources(self, template_name: str) -> list[dict[str, Any]]:
        """List resources for a template."""
        data = await self._get_json(f"/mcp/{template_name}/resources/list")
        return data.get("resources", [])

    async def read_resource(
        self,
        template_name: str,
        resource_uri: str,
    ) -> dict[str, Any]:
        """Read a resource through the gateway."""
        payload = {"uri": resource_uri}
        return await self._post_json(f"/mcp/{template_name}/resources/read", payload)

    # Prompt Operations

    async def list_prompts(self, template_name: str) -> list[dict[str, Any]]:
        """List prompts for a template."""
        data = await self._get_json(f"/mcp/{template_name}/prompts/list")
        return data.get("prompts", [])

    async def get_prompt(
        self,
        template_name: str,
        prompt_name: str,
        arguments: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Get a prompt through the gateway."""
        payload = {
            "name": prompt_name,
            "arguments": arguments or {},
        }
        return await self._post_json(f"/mcp/{template_name}/prompts/get", payload)

    # Batch Operations

    async def call_tools_batch(
        self,
        calls: list[dict[str, Any]],
    ) -> list[ToolCallResponse]:
        """Call multiple tools in batch."""
        tasks = []
        for call in calls:
            task = self.call_tool(
                call["template_name"],
                call["tool_name"],
                call.get("arguments"),
            )
            tasks.append(task)

        results = await asyncio.gather(*tasks, return_exceptions=True)

        responses = []
        for result in results:
            if isinstance(result, Exception):
                # Convert exception to error response
                responses.append(
                    ToolCallResponse(
                        content=[{"type": "text", "text": f"Error: {result}"}],
                        isError=True,
                    )
                )
            else:
                responses.append(result)

        return responses


class MCPGatewayConnection:
    """Direct MCP protocol connection through the gateway.

    This provides a more advanced interface that uses the native MCP protocol
    while benefiting from gateway load balancing and health checking.
    """

    def __init__(
        self,
        template_name: str,
        gateway_url: str = "http://localhost:8080",
        api_key: str | None = None,
    ):
        """
        Initialize MCP gateway connection.

        Args:
            template_name: Template to connect to
            gateway_url: Gateway base URL
            api_key: API key for authentication
        """
        self.template_name = template_name
        self.gateway_url = gateway_url.rstrip("/")
        self.api_key = api_key
        self._connection: MCPConnection | None = None

    async def connect(self) -> bool:
        """Connect to MCP server through gateway."""
        if self._connection is not None:
            return True

        # Use HTTP connection through gateway
        endpoint = f"{self.gateway_url}/mcp/{self.template_name}"

        self._connection = MCPConnection()

        # Add authentication header if API key provided
        headers = {}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"

        # connect_http_smart does not accept headers as a keyword argument
        # If authentication is needed, pass headers as part of the endpoint or update MCPConnection accordingly
        success = await self._connection.connect_http_smart(endpoint)

        if not success:
            self._connection = None
            return False

        return True

    async def disconnect(self):
        """Disconnect from MCP server."""
        if self._connection:
            await self._connection.disconnect()
            self._connection = None

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()

    def _check_connected(self):
        """Check if connected."""
        if self._connection is None:
            raise GatewayClientError("Not connected. Call connect() first.")

    async def list_tools(self) -> list[dict[str, Any]]:
        """List available tools."""
        self._check_connected()
        result = await self._connection.list_tools()
        return result.get("tools", [])

    async def call_tool(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Call a tool."""
        self._check_connected()
        return await self._connection.call_tool(name, arguments or {})

    async def list_resources(self) -> list[dict[str, Any]]:
        """List available resources."""
        self._check_connected()
        raise NotImplementedError("list_resources is not implemented in MCPConnection")

    async def read_resource(self, uri: str) -> dict[str, Any]:
        """Read a resource."""
        self._check_connected()
        raise NotImplementedError("read_resource is not implemented in MCPConnection")

    async def list_prompts(self) -> list[dict[str, Any]]:
        """List available prompts."""
        self._check_connected()
        raise NotImplementedError("list_prompts is not implemented in MCPConnection")

    async def get_prompt(
        self,
        name: str,
        arguments: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Get a prompt."""
        self._check_connected()
        raise NotImplementedError("get_prompt is not implemented in MCPConnection")


# Connection pool for efficient resource management
class GatewayConnectionPool:
    """Connection pool for MCP gateway connections."""

    def __init__(
        self,
        gateway_url: str = "http://localhost:8080",
        api_key: str | None = None,
        max_connections: int = 10,
    ):
        """
        Initialize connection pool.

        Args:
            gateway_url: Gateway base URL
            api_key: API key for authentication
            max_connections: Maximum connections per template
        """
        self.gateway_url = gateway_url
        self.api_key = api_key
        self.max_connections = max_connections
        self._pools: dict[str, list[MCPGatewayConnection]] = {}
        self._semaphores: dict[str, asyncio.Semaphore] = {}

    def _get_semaphore(self, template_name: str) -> asyncio.Semaphore:
        """Get semaphore for template."""
        if template_name not in self._semaphores:
            self._semaphores[template_name] = asyncio.Semaphore(self.max_connections)
        return self._semaphores[template_name]

    @asynccontextmanager
    async def get_connection(self, template_name: str):
        """Get connection from pool."""
        semaphore = self._get_semaphore(template_name)

        async with semaphore:
            # Try to get existing connection from pool
            if template_name in self._pools and self._pools[template_name]:
                connection = self._pools[template_name].pop()
            else:
                # Create new connection
                connection = MCPGatewayConnection(
                    template_name, self.gateway_url, self.api_key
                )
                await connection.connect()

            try:
                yield connection
            finally:
                # Return connection to pool
                if template_name not in self._pools:
                    self._pools[template_name] = []
                self._pools[template_name].append(connection)

    async def close_all(self):
        """Close all connections in pool."""
        for pool in self._pools.values():
            for connection in pool:
                await connection.disconnect()
        self._pools.clear()
        self._semaphores.clear()


# Convenience functions


async def create_gateway_client(
    base_url: str = "http://localhost:8080", api_key: str | None = None, **kwargs
) -> GatewayClient:
    """Create and return a gateway client."""
    return GatewayClient(base_url, api_key, **kwargs)


async def call_tool_simple(
    template_name: str,
    tool_name: str,
    arguments: dict[str, Any] | None = None,
    gateway_url: str = "http://localhost:8080",
    api_key: str | None = None,
) -> ToolCallResponse:
    """Simple tool call function."""
    async with GatewayClient(gateway_url, api_key) as client:
        return await client.call_tool(template_name, tool_name, arguments)
