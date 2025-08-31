"""
Unit tests for gateway health checker.

Tests health checking functionality, status monitoring, and failure handling.
"""

import asyncio
import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock, patch

import pytest

from mcp_platform.gateway.health_checker import HealthChecker
from mcp_platform.gateway.models import ServerStatus, TransportType
from mcp_platform.gateway.registry import ServerInstance, ServerRegistry


class TestHealthChecker:
    """Test HealthChecker class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_registry = Mock(spec=ServerRegistry)
        self.health_checker = HealthChecker(
            registry=self.mock_registry,
            check_interval=5,
            timeout=10,
            max_concurrent_checks=5,
        )

    def test_health_checker_initialization(self):
        """Test HealthChecker initialization."""
        assert self.health_checker.registry == self.mock_registry
        assert self.health_checker.check_interval == 5
        assert self.health_checker.timeout == 10
        assert self.health_checker.max_concurrent_checks == 5
        assert not self.health_checker._running
        assert self.health_checker._task is None

    def test_health_checker_defaults(self):
        """Test HealthChecker with default values."""
        hc = HealthChecker(self.mock_registry)

        assert hc.check_interval == 30
        assert hc.timeout == 10
        assert hc.max_concurrent_checks == 10

    def test_is_running(self):
        """Test health checker running status."""
        assert not self.health_checker.is_running()

        self.health_checker._running = True
        assert self.health_checker.is_running()

    @pytest.mark.asyncio
    async def test_start_health_checker(self):
        """Test starting the health checker."""
        with patch.object(self.health_checker, "_run_health_checks") as mock_run:
            mock_run.return_value = asyncio.sleep(0.1)  # Mock coroutine

            await self.health_checker.start()

            assert self.health_checker._running is True
            assert self.health_checker._task is not None

    @pytest.mark.asyncio
    async def test_stop_health_checker(self):
        """Test stopping the health checker."""
        # Start it first
        with patch.object(self.health_checker, "_run_health_checks") as mock_run:
            mock_run.return_value = asyncio.sleep(0.1)
            await self.health_checker.start()

            # Now stop it
            await self.health_checker.stop()

            assert self.health_checker._running is False
            assert (
                self.health_checker._task is None
                or self.health_checker._task.cancelled()
            )

    @pytest.mark.asyncio
    async def test_check_instance_http_healthy(self):
        """Test checking a healthy HTTP instance."""
        instance = ServerInstance(
            id=1,
            name="http-server",
            host="localhost",
            port=8080,
            transport=TransportType.HTTP,
            status=ServerStatus.RUNNING,
        )

        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)
            mock_get.return_value = mock_response

            result = await self.health_checker.check_instance(instance)

            assert result is True
            mock_get.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_instance_http_unhealthy(self):
        """Test checking an unhealthy HTTP instance."""
        instance = ServerInstance(
            id=1,
            name="http-server",
            host="localhost",
            port=8080,
            transport=TransportType.HTTP,
            status=ServerStatus.RUNNING,
        )

        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_get.side_effect = Exception("Connection refused")

            result = await self.health_checker.check_instance(instance)

            assert result is False

    @pytest.mark.asyncio
    async def test_check_instance_http_timeout(self):
        """Test checking an HTTP instance that times out."""
        instance = ServerInstance(
            id=1,
            name="http-server",
            host="localhost",
            port=8080,
            transport=TransportType.HTTP,
            status=ServerStatus.RUNNING,
        )

        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_get.side_effect = asyncio.TimeoutError()

            result = await self.health_checker.check_instance(instance)

            assert result is False

    @pytest.mark.asyncio
    async def test_check_instance_stdio_healthy(self):
        """Test checking a healthy stdio instance."""
        instance = ServerInstance(
            id=1,
            name="stdio-server",
            transport=TransportType.STDIO,
            status=ServerStatus.RUNNING,
        )

        with patch("mcp_platform.gateway.health_checker.MCPConnection") as mock_mcp:
            mock_connection = AsyncMock()
            mock_connection.ping.return_value = True
            mock_mcp.return_value.__aenter__ = AsyncMock(return_value=mock_connection)
            mock_mcp.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await self.health_checker.check_instance(instance)

            assert result is True
            mock_connection.ping.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_instance_stdio_unhealthy(self):
        """Test checking an unhealthy stdio instance."""
        instance = ServerInstance(
            id=1,
            name="stdio-server",
            transport=TransportType.STDIO,
            status=ServerStatus.RUNNING,
        )

        with patch("mcp_platform.gateway.health_checker.MCPConnection") as mock_mcp:
            mock_connection = AsyncMock()
            mock_connection.ping.side_effect = Exception("Connection failed")
            mock_mcp.return_value.__aenter__ = AsyncMock(return_value=mock_connection)
            mock_mcp.return_value.__aexit__ = AsyncMock(return_value=None)

            result = await self.health_checker.check_instance(instance)

            assert result is False

    @pytest.mark.asyncio
    async def test_update_instance_health_healthy_to_unhealthy(self):
        """Test updating instance health from healthy to unhealthy."""
        instance = ServerInstance(
            id=1,
            name="test-server",
            status=ServerStatus.RUNNING,
            health_score=0.9,
            consecutive_failures=0,
        )

        # Simulate health check failure
        with patch.object(self.health_checker, "check_instance", return_value=False):
            await self.health_checker.update_instance_health(instance)

        # Should update registry with unhealthy status
        self.mock_registry.update_instance_health.assert_called_once()
        call_args = self.mock_registry.update_instance_health.call_args[0]
        updated_instance = call_args[0]

        assert updated_instance.consecutive_failures == 1
        assert updated_instance.health_score < 0.9

    @pytest.mark.asyncio
    async def test_update_instance_health_unhealthy_to_healthy(self):
        """Test updating instance health from unhealthy to healthy."""
        instance = ServerInstance(
            id=1,
            name="test-server",
            status=ServerStatus.RUNNING,
            health_score=0.1,
            consecutive_failures=3,
        )

        # Simulate health check success
        with patch.object(self.health_checker, "check_instance", return_value=True):
            await self.health_checker.update_instance_health(instance)

        # Should update registry with healthy status
        self.mock_registry.update_instance_health.assert_called_once()
        call_args = self.mock_registry.update_instance_health.call_args[0]
        updated_instance = call_args[0]

        assert updated_instance.consecutive_failures == 0
        assert updated_instance.health_score > 0.1

    @pytest.mark.asyncio
    async def test_update_instance_health_mark_unhealthy_after_failures(self):
        """Test marking instance as unhealthy after consecutive failures."""
        instance = ServerInstance(
            id=1,
            name="test-server",
            status=ServerStatus.RUNNING,
            consecutive_failures=4,  # Close to failure threshold
        )

        # Simulate health check failure
        with patch.object(self.health_checker, "check_instance", return_value=False):
            await self.health_checker.update_instance_health(instance)

        # Should mark as unhealthy after reaching threshold
        self.mock_registry.update_instance_health.assert_called_once()
        call_args = self.mock_registry.update_instance_health.call_args[0]
        updated_instance = call_args[0]

        assert updated_instance.consecutive_failures == 5
        # Should be marked as unhealthy if threshold is reached
        if (
            updated_instance.consecutive_failures
            >= self.health_checker.failure_threshold
        ):
            assert updated_instance.status == ServerStatus.UNHEALTHY

    @pytest.mark.asyncio
    async def test_check_all_instances(self):
        """Test checking all instances in registry."""
        instances = [
            ServerInstance(id=1, name="server1", status=ServerStatus.RUNNING),
            ServerInstance(id=2, name="server2", status=ServerStatus.RUNNING),
            ServerInstance(id=3, name="server3", status=ServerStatus.RUNNING),
        ]

        self.mock_registry.get_all_instances.return_value = instances

        with patch.object(self.health_checker, "update_instance_health") as mock_update:
            mock_update.return_value = None  # Mock async function

            await self.health_checker.check_all_instances()

            # Should check all instances
            assert mock_update.call_count == 3
            self.mock_registry.get_all_instances.assert_called_once()

    @pytest.mark.asyncio
    async def test_check_all_instances_concurrent_limit(self):
        """Test that concurrent checks are limited."""
        # Create more instances than the concurrent limit
        instances = [
            ServerInstance(id=i, name=f"server{i}", status=ServerStatus.RUNNING)
            for i in range(15)  # More than max_concurrent_checks (5)
        ]

        self.mock_registry.get_all_instances.return_value = instances

        check_times = []

        async def mock_update_health(instance):
            check_times.append(time.time())
            await asyncio.sleep(0.1)  # Simulate some work

        with patch.object(
            self.health_checker,
            "update_instance_health",
            side_effect=mock_update_health,
        ):
            start_time = time.time()
            await self.health_checker.check_all_instances()
            total_time = time.time() - start_time

        # With concurrent limit of 5, checking 15 instances should take more time
        # than if all were checked concurrently
        assert total_time > 0.2  # Should take at least 2 batches * 0.1s
        assert len(check_times) == 15

    @pytest.mark.asyncio
    async def test_health_check_statistics(self):
        """Test health check statistics collection."""
        instance1 = ServerInstance(id=1, name="server1", status=ServerStatus.RUNNING)
        instance2 = ServerInstance(id=2, name="server2", status=ServerStatus.UNHEALTHY)

        self.mock_registry.get_all_instances.return_value = [instance1, instance2]

        # Perform health checks
        with patch.object(self.health_checker, "check_instance") as mock_check:
            mock_check.side_effect = [True, False]  # server1 healthy, server2 unhealthy

            await self.health_checker.check_all_instances()

        stats = self.health_checker.get_statistics()

        assert "total_checks" in stats
        assert "healthy_instances" in stats
        assert "unhealthy_instances" in stats
        assert "last_check_time" in stats

    def test_get_health_score_calculation(self):
        """Test health score calculation logic."""
        # Test healthy instance
        healthy_score = self.health_checker._calculate_health_score(
            consecutive_failures=0, success_rate=1.0
        )
        assert healthy_score > 0.8

        # Test unhealthy instance
        unhealthy_score = self.health_checker._calculate_health_score(
            consecutive_failures=5, success_rate=0.1
        )
        assert unhealthy_score < 0.3

        # Test partially healthy instance
        partial_score = self.health_checker._calculate_health_score(
            consecutive_failures=2, success_rate=0.7
        )
        assert 0.3 < partial_score < 0.8


class TestHealthCheckerIntegration:
    """Test HealthChecker integration scenarios."""

    @pytest.mark.asyncio
    async def test_health_checker_lifecycle(self):
        """Test complete health checker lifecycle."""
        mock_registry = Mock(spec=ServerRegistry)
        hc = HealthChecker(mock_registry, check_interval=1, timeout=5)

        # Should start not running
        assert not hc.is_running()

        # Start health checker
        with patch.object(hc, "_run_health_checks") as mock_run:
            # Make _run_health_checks run briefly then stop
            async def mock_health_loop():
                hc._running = True
                await asyncio.sleep(0.1)
                hc._running = False

            mock_run.return_value = mock_health_loop()

            await hc.start()

            # Should be running
            assert hc.is_running()

            # Wait a bit for the loop to complete
            await asyncio.sleep(0.2)

            # Stop health checker
            await hc.stop()

            # Should be stopped
            assert not hc.is_running()

    @pytest.mark.asyncio
    async def test_health_checker_error_handling(self):
        """Test health checker error handling."""
        mock_registry = Mock(spec=ServerRegistry)
        mock_registry.get_all_instances.side_effect = Exception("Registry error")

        hc = HealthChecker(mock_registry)

        # Should handle registry errors gracefully
        try:
            await hc.check_all_instances()
        except Exception:
            pytest.fail("Health checker should handle registry errors gracefully")

    @pytest.mark.asyncio
    async def test_health_checker_with_mixed_transports(self):
        """Test health checker with different transport types."""
        mock_registry = Mock(spec=ServerRegistry)

        instances = [
            ServerInstance(
                id=1,
                name="http-server",
                transport=TransportType.HTTP,
                host="localhost",
                port=8080,
                status=ServerStatus.RUNNING,
            ),
            ServerInstance(
                id=2,
                name="stdio-server",
                transport=TransportType.STDIO,
                status=ServerStatus.RUNNING,
            ),
        ]

        mock_registry.get_all_instances.return_value = instances

        hc = HealthChecker(mock_registry)

        # Mock both HTTP and stdio health checks
        with (
            patch("aiohttp.ClientSession.get") as mock_http,
            patch("mcp_platform.gateway.health_checker.MCPConnection") as mock_mcp,
        ):

            # Mock HTTP response
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.__aenter__ = AsyncMock(return_value=mock_response)
            mock_response.__aexit__ = AsyncMock(return_value=None)
            mock_http.return_value = mock_response

            # Mock MCP connection
            mock_connection = AsyncMock()
            mock_connection.ping.return_value = True
            mock_mcp.return_value.__aenter__ = AsyncMock(return_value=mock_connection)
            mock_mcp.return_value.__aexit__ = AsyncMock(return_value=None)

            await hc.check_all_instances()

            # Should call appropriate health check for each transport
            mock_http.assert_called_once()
            mock_connection.ping.assert_called_once()
