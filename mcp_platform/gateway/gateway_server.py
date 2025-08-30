"""
MCP Gateway Server - Main HTTP server for unified MCP access.

Provides a single HTTP endpoint for accessing all deployed MCP servers
with intelligent routing, load balancing, and protocol translation.
"""

import logging
import time
from typing import Any, Dict, Optional
from urllib.parse import urlparse

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from mcp_platform.core.mcp_connection import MCPConnection
from mcp_platform.core.multi_backend_manager import MultiBackendManager

from .health_checker import HealthChecker
from .load_balancer import LoadBalancer, LoadBalancingStrategy
from .registry import ServerInstance, ServerRegistry

logger = logging.getLogger(__name__)


class MCPGatewayServer:
    """
    Main MCP Gateway server providing unified access to MCP servers.

    Features:
    - Single HTTP endpoint for all MCP servers
    - Automatic routing based on template name
    - Load balancing across multiple instances
    - Health checking and failover
    - Protocol translation (HTTP and stdio)
    """

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8080,
        registry_file: Optional[str] = None,
        health_check_interval: int = 30,
        request_timeout: int = 60,
        max_retries: int = 3,
    ):
        """
        Initialize MCP Gateway server.

        Args:
            host: Host to bind the server to
            port: Port to bind the server to
            registry_file: Path to registry persistence file
            health_check_interval: Health check interval in seconds
            request_timeout: Request timeout in seconds
            max_retries: Maximum retries for failed requests
        """
        self.host = host
        self.port = port
        self.request_timeout = request_timeout
        self.max_retries = max_retries

        # Initialize core components
        self.registry = ServerRegistry(registry_file)
        self.load_balancer = LoadBalancer()
        self.health_checker = HealthChecker(self.registry, health_check_interval)
        self.backend_manager = MultiBackendManager()

        # FastAPI app
        self.app = FastAPI(
            title="MCP Gateway",
            description="Unified HTTP gateway for Model Context Protocol servers",
            version="1.0.0",
        )

        # Add CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Setup routes
        self._setup_routes()

        # Runtime state
        self._running = False
        self._request_count = 0
        self._start_time: Optional[float] = None

    def _setup_routes(self):
        """Setup FastAPI routes."""

        # MCP server routes
        @self.app.get("/mcp/{template_name}/tools/list")
        async def list_tools(template_name: str):
            """List tools for a specific template."""
            return await self._handle_mcp_request(template_name, "tools/list", {})

        @self.app.post("/mcp/{template_name}/tools/call")
        async def call_tool(template_name: str, request: Request):
            """Call a tool on a specific template."""
            body = await request.json()
            return await self._handle_mcp_request(template_name, "tools/call", body)

        @self.app.get("/mcp/{template_name}/resources/list")
        async def list_resources(template_name: str):
            """List resources for a specific template."""
            return await self._handle_mcp_request(template_name, "resources/list", {})

        @self.app.post("/mcp/{template_name}/resources/read")
        async def read_resource(template_name: str, request: Request):
            """Read a resource on a specific template."""
            body = await request.json()
            return await self._handle_mcp_request(template_name, "resources/read", body)

        @self.app.get("/mcp/{template_name}/health")
        async def check_template_health(template_name: str):
            """Check health of all instances for a template."""
            return await self._handle_health_check(template_name)

        # Gateway management routes
        @self.app.get("/gateway/registry")
        async def get_registry():
            """Get current server registry."""
            return {
                "templates": {
                    name: template.to_dict()
                    for name, template in self.registry.templates.items()
                },
                "stats": self.registry.get_registry_stats(),
            }

        @self.app.get("/gateway/health")
        async def gateway_health():
            """Gateway health check."""
            return {
                "status": "healthy" if self._running else "unhealthy",
                "uptime_seconds": (
                    time.time() - self._start_time if self._start_time else 0
                ),
                "total_requests": self._request_count,
                "registry_stats": self.registry.get_registry_stats(),
                "health_checker_stats": self.health_checker.get_health_stats(),
                "load_balancer_stats": self.load_balancer.get_load_balancer_stats(),
            }

        @self.app.post("/gateway/register")
        async def register_server(request: Request):
            """Register a new server instance."""
            data = await request.json()
            return await self._handle_server_registration(data)

        @self.app.delete("/gateway/deregister/{template_name}/{instance_id}")
        async def deregister_server(template_name: str, instance_id: str):
            """Deregister a server instance."""
            success = self.registry.deregister_server(template_name, instance_id)
            if success:
                return {
                    "message": f"Deregistered instance {instance_id} from template {template_name}"
                }
            else:
                raise HTTPException(status_code=404, detail="Instance not found")

        @self.app.get("/gateway/stats")
        async def get_stats():
            """Get comprehensive gateway statistics."""
            return {
                "gateway": {
                    "uptime_seconds": (
                        time.time() - self._start_time if self._start_time else 0
                    ),
                    "total_requests": self._request_count,
                    "request_timeout": self.request_timeout,
                    "max_retries": self.max_retries,
                },
                "registry": self.registry.get_registry_stats(),
                "health_checker": self.health_checker.get_health_stats(),
                "load_balancer": self.load_balancer.get_load_balancer_stats(),
            }

    async def _handle_mcp_request(
        self, template_name: str, method: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle MCP request routing and load balancing.

        Args:
            template_name: Name of the target template
            method: MCP method to call
            params: Method parameters

        Returns:
            MCP response
        """
        self._request_count += 1

        # Get healthy instances for template
        instances = self.registry.get_healthy_instances(template_name)

        # If no instances available, try stdio fallback
        if not instances:
            return await self._try_stdio_fallback(template_name, method, params)

        # Get template for load balancer configuration
        template = self.registry.get_template(template_name)
        strategy = (
            LoadBalancingStrategy(template.load_balancer.strategy) if template else None
        )

        # Try request with retries
        last_error = None
        for attempt in range(self.max_retries):
            try:
                # Select instance using load balancer
                instance = self.load_balancer.select_instance(instances, strategy)
                if not instance:
                    # If load balancer fails, try stdio fallback
                    return await self._try_stdio_fallback(template_name, method, params)

                # Record request start
                self.load_balancer.record_request_start(instance, strategy)

                # Route request based on transport type
                if instance.transport == "http":
                    response = await self._route_http_request(instance, method, params)
                elif instance.transport == "stdio":
                    response = await self._route_stdio_request(instance, method, params)
                else:
                    raise HTTPException(
                        status_code=500,
                        detail=f"Unsupported transport type: {instance.transport}",
                    )

                # Record successful completion
                self.load_balancer.record_request_completion(instance, True, strategy)

                return response

            except Exception as e:
                last_error = e
                logger.warning(
                    f"Request attempt {attempt + 1} failed for template {template_name}: {e}"
                )

                # Record failed completion
                if "instance" in locals():
                    self.load_balancer.record_request_completion(
                        instance, False, strategy
                    )

                # Remove failed instance from this attempt
                if "instance" in locals() and instance in instances:
                    instances.remove(instance)

                # If no more instances, try stdio fallback
                if not instances:
                    return await self._try_stdio_fallback(template_name, method, params)
                if not instances:
                    break

        # All retries failed
        raise HTTPException(
            status_code=502,
            detail=f"All attempts failed for template '{template_name}': {str(last_error)}",
        )

    async def _route_http_request(
        self, instance: ServerInstance, method: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Route request to HTTP MCP server."""
        if not instance.endpoint:
            raise HTTPException(
                status_code=500, detail="No endpoint configured for HTTP instance"
            )

        try:
            parsed = urlparse(instance.endpoint)
            base_url = f"{parsed.scheme}://{parsed.netloc}"

            connection = MCPConnection(timeout=self.request_timeout)

            # Connect to server
            success = await connection.connect_http_smart(base_url)
            if not success:
                raise HTTPException(
                    status_code=502, detail="Failed to connect to MCP server"
                )

            # Make MCP request
            if method == "tools/list":
                result = await connection.list_tools()
            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                if not tool_name:
                    raise HTTPException(status_code=400, detail="Missing tool name")
                result = await connection.call_tool(tool_name, arguments)
            elif method == "resources/list":
                result = await connection.list_resources()
            elif method == "resources/read":
                uri = params.get("uri")
                if not uri:
                    raise HTTPException(status_code=400, detail="Missing resource URI")
                result = await connection.read_resource(uri)
            else:
                raise HTTPException(
                    status_code=400, detail=f"Unsupported method: {method}"
                )

            await connection.disconnect()
            return result or {"result": "success"}

        except Exception as e:
            logger.error(f"HTTP routing failed for instance {instance.id}: {e}")
            raise HTTPException(
                status_code=502, detail=f"HTTP request failed: {str(e)}"
            )

    async def _route_stdio_request(
        self, instance: ServerInstance, method: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Route request to stdio MCP server."""
        if not instance.command:
            raise HTTPException(
                status_code=500, detail="No command configured for stdio instance"
            )

        try:
            connection = MCPConnection(timeout=self.request_timeout)

            # Connect to stdio server
            success = await connection.connect_stdio(
                command=instance.command,
                working_dir=instance.working_dir,
                env_vars=instance.env_vars,
            )
            if not success:
                raise HTTPException(
                    status_code=502, detail="Failed to connect to stdio MCP server"
                )

            # Make MCP request
            if method == "tools/list":
                result = await connection.list_tools()
            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                if not tool_name:
                    raise HTTPException(status_code=400, detail="Missing tool name")
                result = await connection.call_tool(tool_name, arguments)
            elif method == "resources/list":
                result = await connection.list_resources()
            elif method == "resources/read":
                uri = params.get("uri")
                if not uri:
                    raise HTTPException(status_code=400, detail="Missing resource URI")
                result = await connection.read_resource(uri)
            else:
                raise HTTPException(
                    status_code=400, detail=f"Unsupported method: {method}"
                )

            await connection.disconnect()
            return result or {"result": "success"}

        except Exception as e:
            logger.error(f"stdio routing failed for instance {instance.id}: {e}")
            raise HTTPException(
                status_code=502, detail=f"stdio request failed: {str(e)}"
            )

    async def _try_stdio_fallback(
        self, template_name: str, method: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Try stdio fallback when no registered instances are available.

        This implements the same logic as MultiBackendManager.call_tool to automatically
        fall back to stdio transport when no HTTP deployments exist.
        """
        try:
            # Use backend manager to attempt stdio call based on method
            if method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                if not tool_name:
                    raise HTTPException(status_code=400, detail="Missing tool name")

                result = self.backend_manager.call_tool(
                    template_name=template_name,
                    tool_name=tool_name,
                    arguments=arguments,
                    force_stdio=True,
                )
            elif method == "tools/list":
                # For tools/list, we need to use call_tool with a special approach
                # since there's no dedicated list_tools method in MultiBackendManager
                result = self.backend_manager.get_all_tools(
                    template_name=template_name,
                    include_static=False,  # Only dynamic tools from stdio
                    include_dynamic=True,
                )
                # Transform the result to match MCP list_tools format
                if isinstance(result, dict) and "dynamic_tools" in result:
                    # Extract tools for the specific template
                    template_tools = result["dynamic_tools"].get(template_name, {})
                    if template_tools:
                        # Return in MCP format
                        return {"tools": list(template_tools.values())}
                    else:
                        # Try stdio call using MultiBackendManager for this template
                        return await self._try_direct_stdio_call(
                            template_name, method, params
                        )
                else:
                    return await self._try_direct_stdio_call(
                        template_name, method, params
                    )
            else:
                # For other methods, try direct stdio call
                return await self._try_direct_stdio_call(template_name, method, params)

            # Check if the call was successful
            if isinstance(result, dict):
                if result.get(
                    "success", True
                ):  # Default to True for backward compatibility
                    # Add metadata about the fallback
                    if "backend_type" in result:
                        result["_gateway_info"] = {
                            "used_stdio_fallback": True,
                            "backend_type": result["backend_type"],
                            "message": f"No registered instances found for '{template_name}', used stdio fallback",
                        }
                    return result
                else:
                    # Backend returned explicit failure
                    error_msg = result.get("error", "Unknown error")
                    if error_msg and "not found" in str(error_msg).lower():
                        raise HTTPException(
                            status_code=404,
                            detail=f"Template '{template_name}' not found",
                        )
                    elif (
                        error_msg and "does not support stdio" in str(error_msg).lower()
                    ):
                        raise HTTPException(
                            status_code=400,
                            detail=f"Template '{template_name}' does not support stdio transport. Deploy it first: mcpp deploy {template_name}",
                        )
                    else:
                        raise HTTPException(status_code=502, detail=str(error_msg))
            else:
                return result

        except HTTPException:
            # Re-raise HTTP exceptions as-is
            raise
        except Exception as e:
            logger.warning(f"stdio fallback failed for template {template_name}: {e}")
            raise HTTPException(
                status_code=503,
                detail=f"No instances available for template '{template_name}' and stdio fallback failed: {str(e)}",
            )

    async def _try_direct_stdio_call(
        self, template_name: str, method: str, params: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Try direct stdio call using the first available backend's tool manager.
        """
        if not self.backend_manager.tool_managers:
            raise HTTPException(
                status_code=503,
                detail="No backend tool managers available for stdio fallback",
            )

        # Try first available backend
        backend_type, tool_manager = next(
            iter(self.backend_manager.tool_managers.items())
        )

        try:
            if method == "tools/list":
                # Use the tool manager's discovery method
                result = tool_manager.list_tools(
                    template_name,
                    static=False,  # Only dynamic tools for stdio
                    dynamic=True,
                    config_values={},  # Empty config for stdio calls
                    timeout=30,
                )
            elif method == "tools/call":
                tool_name = params.get("name")
                arguments = params.get("arguments", {})
                if not tool_name:
                    raise HTTPException(status_code=400, detail="Missing tool name")

                result = tool_manager.call_tool(
                    template_name,
                    tool_name,
                    arguments,
                    config_values={},  # Empty config for stdio calls
                    force_stdio=True,
                    pull_image=False,  # Don't pull images for gateway calls
                )
            else:
                raise HTTPException(
                    status_code=501,
                    detail=f"Method '{method}' not supported for stdio fallback",
                )

            # Add backend info to result
            if isinstance(result, dict):
                result["_gateway_info"] = {
                    "used_stdio_fallback": True,
                    "backend_type": backend_type,
                    "message": f"No registered instances found for '{template_name}', used stdio fallback",
                }

            return result

        except Exception as e:
            logger.warning(f"Direct stdio call failed on {backend_type}: {e}")
            raise HTTPException(
                status_code=502, detail=f"stdio fallback failed: {str(e)}"
            )

    async def _handle_health_check(self, template_name: str) -> Dict[str, Any]:
        """Handle template health check."""
        template = self.registry.get_template(template_name)
        if not template:
            raise HTTPException(
                status_code=404, detail=f"Template '{template_name}' not found"
            )

        # Get current health status
        healthy_instances = template.get_healthy_instances()
        total_instances = len(template.instances)

        # Trigger immediate health checks
        health_results = {}
        for instance in template.instances:
            health_result = await self.health_checker.check_instance_now(
                template_name, instance.id
            )
            health_results[instance.id] = {
                "healthy": health_result,
                "endpoint": instance.endpoint,
                "transport": instance.transport,
                "status": instance.status,
                "consecutive_failures": instance.consecutive_failures,
                "last_health_check": instance.last_health_check,
            }

        return {
            "template_name": template_name,
            "total_instances": total_instances,
            "healthy_instances": len(healthy_instances),
            "health_percentage": (
                (len(healthy_instances) / total_instances * 100)
                if total_instances > 0
                else 0
            ),
            "instances": health_results,
        }

    async def _handle_server_registration(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle server registration request."""
        try:
            # Extract required fields
            template_name = data.get("template_name")
            instance_data = data.get("instance")

            if not template_name or not instance_data:
                raise HTTPException(
                    status_code=400,
                    detail="Missing required fields: template_name, instance",
                )

            # Create server instance
            instance = ServerInstance.from_dict(instance_data)

            # Register with registry
            self.registry.register_server(template_name, instance)

            return {
                "message": f"Registered instance {instance.id} for template {template_name}",
                "instance_id": instance.id,
                "template_name": template_name,
            }

        except Exception as e:
            logger.error(f"Server registration failed: {e}")
            raise HTTPException(
                status_code=400, detail=f"Registration failed: {str(e)}"
            )

    async def start(self):
        """Start the gateway server."""
        if self._running:
            logger.warning("Gateway server is already running")
            return

        self._running = True
        self._start_time = time.time()

        # Start health checker
        await self.health_checker.start()

        logger.info(f"Starting MCP Gateway server on {self.host}:{self.port}")

    async def stop(self):
        """Stop the gateway server."""
        if not self._running:
            return

        self._running = False

        # Stop health checker
        await self.health_checker.stop()

        logger.info("MCP Gateway server stopped")

    def run(self, **kwargs):
        """Run the gateway server using uvicorn."""
        # Merge provided kwargs with defaults
        config = {"host": self.host, "port": self.port, "log_level": "info", **kwargs}

        uvicorn.run(self.app, **config)
