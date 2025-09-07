"""
Health Checker for MCP Gateway.

Monitors health of registered MCP server instances and updates their status
in the registry. Supports both HTTP and stdio health checking.
"""

import asyncio
import logging
import time

import aiohttp

from mcp_platform.core.mcp_connection import MCPConnection

from .registry import ServerInstance, ServerRegistry

logger = logging.getLogger(__name__)


class HealthChecker:
    """
    Health checker for monitoring MCP server instances.

    Performs periodic health checks on registered servers and updates
    their status in the registry. Supports different check methods
    based on server transport type.
    """

    def __init__(
        self,
        registry: ServerRegistry,
        check_interval: int = 30,
        timeout: int = 10,
        max_concurrent_checks: int = 10,
    ):
        """
        Initialize health checker.

        Args:
            registry: Server registry to update
            check_interval: Interval between health checks in seconds
            timeout: Timeout for individual health checks in seconds
            max_concurrent_checks: Maximum concurrent health check operations
        """
        self.registry = registry
        self.check_interval = check_interval
        self.timeout = timeout
        self.max_concurrent_checks = max_concurrent_checks

        self._running = False
        self._check_task: asyncio.Task | None = None
        self._semaphore = asyncio.Semaphore(max_concurrent_checks)

        # Health check statistics
        self._total_checks = 0
        self._successful_checks = 0
        self._failed_checks = 0
        self._last_check_time: float | None = None

    async def start(self):
        """Start the health checking service."""
        if self._running:
            logger.warning("Health checker is already running")
            return

        self._running = True
        self._check_task = asyncio.create_task(self._health_check_loop())
        logger.info(f"Health checker started with {self.check_interval}s interval")

    async def stop(self):
        """Stop the health checking service."""
        if not self._running:
            return

        self._running = False
        if self._check_task:
            self._check_task.cancel()
            try:
                await self._check_task
            except asyncio.CancelledError:
                pass

        logger.info("Health checker stopped")

    async def _health_check_loop(self):
        """Main health checking loop."""
        while self._running:
            try:
                await self._perform_health_checks()
                self._last_check_time = time.time()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in health check loop: {e}")
                await asyncio.sleep(
                    min(self.check_interval, 10)
                )  # Shorter retry interval on error

    async def _perform_health_checks(self):
        """Perform health checks on all registered instances."""
        instances = await self.registry.list_all_instances()
        if not instances:
            logger.debug("No instances to health check")
            return

        logger.debug(f"Performing health checks on {len(instances)} instances")

        # Create tasks for all health checks
        tasks = []
        for instance in instances:
            task = asyncio.create_task(self._check_instance_health(instance))
            tasks.append(task)

        # Wait for all checks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        successful_checks = 0
        failed_checks = 0

        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Health check error for {instances[i].id}: {result}")
                failed_checks += 1
            elif result:
                successful_checks += 1
            else:
                failed_checks += 1

        # Update statistics
        self._total_checks += len(instances)
        self._successful_checks += successful_checks
        self._failed_checks += failed_checks

        logger.debug(
            f"Health check completed: {successful_checks} successful, "
            f"{failed_checks} failed out of {len(instances)} instances"
        )

    async def _check_instance_health(self, instance: ServerInstance) -> bool:
        """
        Check health of a single server instance.

        Args:
            instance: Server instance to check

        Returns:
            True if instance is healthy, False otherwise
        """
        async with self._semaphore:
            try:
                if instance.transport == "http":
                    is_healthy = await self._check_http_health(instance)
                elif instance.transport == "stdio":
                    is_healthy = await self._check_stdio_health(instance)
                else:
                    logger.warning(
                        f"Unknown transport type for instance {instance.id}: {instance.transport}"
                    )
                    is_healthy = False

                # Update instance health in registry
                self.registry.update_instance_health(
                    instance.template_name, instance.id, is_healthy
                )

                return is_healthy

            except Exception as e:
                logger.error(f"Health check failed for instance {instance.id}: {e}")
                self.registry.update_instance_health(
                    instance.template_name, instance.id, False
                )
                return False

    async def _check_http_health(self, instance: ServerInstance) -> bool:
        """
        Check health of HTTP MCP server.

        Args:
            instance: HTTP server instance to check

        Returns:
            True if server is healthy, False otherwise
        """
        if not instance.endpoint:
            logger.warning(f"No endpoint configured for HTTP instance {instance.id}")
            return False

        try:
            # Try multiple health check approaches

            # 1. Try MCP tools/list via MCPConnection (most reliable)
            mcp_healthy = await self._check_mcp_protocol_health(instance.endpoint)
            if mcp_healthy:
                return True

            # 2. Try basic HTTP health endpoint
            http_healthy = await self._check_basic_http_health(instance.endpoint)
            if http_healthy:
                return True

            # 3. Try simple connectivity check
            connectivity_healthy = await self._check_http_connectivity(instance.endpoint)
            return connectivity_healthy

        except Exception as e:
            logger.debug(f"HTTP health check failed for {instance.id}: {e}")
            return False

    async def _check_mcp_protocol_health(self, endpoint: str) -> bool:
        """Check health using MCP protocol (tools/list)."""
        try:
            from urllib.parse import urlparse

            parsed = urlparse(endpoint)
            base_url = f"{parsed.scheme}://{parsed.netloc}"

            connection = MCPConnection(timeout=self.timeout)

            # Try to connect and list tools
            success = await connection.connect_http_smart(base_url)
            if success:
                tools = await connection.list_tools()
                await connection.disconnect()
                return tools is not None  # Any response (even empty) indicates health

            return False

        except Exception as e:
            logger.debug(f"MCP protocol health check failed: {e}")
            return False

    async def _check_basic_http_health(self, endpoint: str) -> bool:
        """Check health using basic HTTP health endpoints."""
        health_paths = ["/health", "/ping", "/status", "/"]

        try:
            from urllib.parse import urljoin, urlparse

            parsed = urlparse(endpoint)
            base_url = f"{parsed.scheme}://{parsed.netloc}"

            timeout = aiohttp.ClientTimeout(total=self.timeout)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                for path in health_paths:
                    try:
                        health_url = urljoin(base_url, path)
                        async with session.get(health_url) as response:
                            if (
                                response.status < 500
                            ):  # Accept any non-server-error response
                                return True
                    except Exception:
                        continue  # Try next path

            return False

        except Exception as e:
            logger.debug(f"Basic HTTP health check failed: {e}")
            return False

    async def _check_http_connectivity(self, endpoint: str) -> bool:
        """Check basic HTTP connectivity."""
        try:
            from urllib.parse import urlparse

            parsed = urlparse(endpoint)
            base_url = f"{parsed.scheme}://{parsed.netloc}"

            timeout = aiohttp.ClientTimeout(total=self.timeout)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(base_url):
                    # Any response indicates the server is up
                    return True

        except Exception as e:
            logger.debug(f"HTTP connectivity check failed: {e}")
            return False

    async def _check_stdio_health(self, instance: ServerInstance) -> bool:
        """
        Check health of stdio MCP server.

        Args:
            instance: stdio server instance to check

        Returns:
            True if server is healthy, False otherwise
        """
        if not instance.command:
            logger.warning(f"No command configured for stdio instance {instance.id}")
            return False

        try:
            # For stdio servers, check if the process can be started and responds to MCP
            connection = MCPConnection(timeout=self.timeout)

            success = await connection.connect_stdio(
                command=instance.command,
                working_dir=instance.working_dir,
                env_vars=instance.env_vars,
            )

            if success:
                # Try to list tools to verify MCP protocol works
                tools = await connection.list_tools()
                await connection.disconnect()
                return tools is not None

            return False

        except Exception as e:
            logger.debug(f"stdio health check failed for {instance.id}: {e}")
            return False

    async def check_instance_now(
        self, template_name: str, instance_id: str
    ) -> bool | None:
        """
        Perform immediate health check on a specific instance.

        Args:
            template_name: Name of the template
            instance_id: ID of the instance to check

        Returns:
            True if healthy, False if unhealthy, None if instance not found
        """
        instance = self.registry.get_instance(template_name, instance_id)
        if not instance:
            return None

        return await self._check_instance_health(instance)

    def get_health_stats(self) -> dict[str, any]:
        """Get health checker statistics."""
        uptime = (
            time.time() - (self._last_check_time or time.time())
            if self._last_check_time
            else 0
        )
        success_rate = (
            (self._successful_checks / self._total_checks * 100)
            if self._total_checks > 0
            else 0
        )

        return {
            "running": self._running,
            "check_interval": self.check_interval,
            "timeout": self.timeout,
            "max_concurrent_checks": self.max_concurrent_checks,
            "total_checks": self._total_checks,
            "successful_checks": self._successful_checks,
            "failed_checks": self._failed_checks,
            "success_rate_percent": round(success_rate, 2),
            "last_check_time": self._last_check_time,
            "uptime_seconds": round(uptime, 2) if self._last_check_time else None,
        }

    def reset_stats(self):
        """Reset health check statistics."""
        self._total_checks = 0
        self._successful_checks = 0
        self._failed_checks = 0
        self._last_check_time = None
        logger.info("Health checker statistics reset")
