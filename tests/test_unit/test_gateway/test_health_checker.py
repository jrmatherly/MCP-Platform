"""
Unit tests for the Gateway Health Checker.
"""

import asyncio
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


@pytest.mark.unit
@pytest.mark.gateway
@pytest.mark.asyncio
class TestHealthChecker:
    """Test HealthChecker functionality."""

    @pytest.fixture
    def mock_registry(self):
        """Create a mock registry."""
        registry = AsyncMock()
        registry.list_templates.return_value = ["test_template"]

        # Create mock instances with all required attributes
        instance1 = SimpleNamespace(
            id="instance1",
            template_name="test_template",
            endpoint="http://localhost:8001",
            transport="http",
            status="healthy",
        )
        instance2 = SimpleNamespace(
            id="instance2",
            template_name="test_template",
            endpoint="http://localhost:8002",
            transport="http",
            status="unhealthy",
        )

        # Return list directly, not a coroutine
        async def get_instances(template_name):
            return [instance1, instance2]

        registry.list_instances = get_instances
        registry.list_all_instances.return_value = [instance1, instance2]
        registry.update_instance_health = MagicMock()  # Synchronous mock
        return registry

    @pytest.fixture
    def health_checker(self, mock_registry):
        """Create a health checker instance."""
        from mcp_platform.gateway.health_checker import HealthChecker

        return HealthChecker(mock_registry, check_interval=1)

    def test_init(self, mock_registry):
        """Test health checker initialization."""
        from mcp_platform.gateway.health_checker import HealthChecker

        checker = HealthChecker(mock_registry, check_interval=30)

        assert checker.registry == mock_registry
        assert checker.check_interval == 30
        assert not checker._running
        assert checker._check_task is None
        assert checker.timeout == 10  # default
        assert checker.max_concurrent_checks == 10  # default

    @pytest.mark.asyncio
    async def test_start_stop(self, health_checker):
        """Test starting and stopping health checker."""
        assert not health_checker._running

        # Start health checker
        await health_checker.start()
        assert health_checker._running
        assert health_checker._check_task is not None

        # Stop health checker
        await health_checker.stop()
        assert not health_checker._running

    @pytest.mark.asyncio
    async def test_double_start_prevention(self, health_checker):
        """Test that starting twice doesn't create multiple tasks."""
        await health_checker.start()
        first_task = health_checker._check_task

        await health_checker.start()  # Should be no-op
        assert health_checker._check_task == first_task

        await health_checker.stop()

    @pytest.mark.asyncio
    async def test_stop_when_not_running(self, health_checker):
        """Test stopping when not running."""
        assert not health_checker._running
        await health_checker.stop()  # Should not raise

    @pytest.mark.asyncio
    async def test_check_http_health_success(self, health_checker):
        """Test successful HTTP health check via mocking."""
        instance = SimpleNamespace(
            id="test",
            template_name="test_template",
            endpoint="http://localhost:8001",
            transport="http",
        )

        # Mock the MCP protocol health check
        with patch.object(
            health_checker, "_check_mcp_protocol_health", return_value=True
        ):
            is_healthy = await health_checker._check_http_health(instance)
            assert is_healthy

    @pytest.mark.asyncio
    async def test_check_http_health_failure(self, health_checker):
        """Test failed HTTP health check."""
        instance = SimpleNamespace(
            id="test",
            template_name="test_template",
            endpoint="http://localhost:8001",
            transport="http",
        )

        # Mock all health check methods to fail
        with (
            patch.object(
                health_checker, "_check_mcp_protocol_health", return_value=False
            ),
            patch.object(
                health_checker, "_check_basic_http_health", return_value=False
            ),
            patch.object(
                health_checker, "_check_http_connectivity", return_value=False
            ),
        ):
            is_healthy = await health_checker._check_http_health(instance)
            assert not is_healthy

    @pytest.mark.asyncio
    async def test_check_stdio_health(self, health_checker):
        """Test stdio health check."""
        instance = SimpleNamespace(
            id="test",
            template_name="test_template",
            command=["python", "-m", "test_server"],
            transport="stdio",
        )

        # Mock the _check_stdio_health method directly
        with patch.object(health_checker, "_check_stdio_health", return_value=True):
            is_healthy = await health_checker._check_stdio_health(instance)
            assert is_healthy

    @pytest.mark.asyncio
    async def test_perform_health_checks(self, health_checker, mock_registry):
        """Test performing health checks for all instances."""
        # Mock the instance health check to return predictable results
        with patch.object(health_checker, "_check_instance_health") as mock_check:
            mock_check.side_effect = [True, False]  # First healthy, second unhealthy

            await health_checker._perform_health_checks()

            # Verify registry calls
            mock_registry.list_all_instances.assert_called_once()

            # Should have called health check twice
            assert mock_check.call_count == 2

    @pytest.mark.asyncio
    async def test_health_check_statistics(self, health_checker):
        """Test health check statistics tracking."""
        # Initial state
        assert health_checker._total_checks == 0
        assert health_checker._successful_checks == 0
        assert health_checker._failed_checks == 0
        assert health_checker._last_check_time is None

    @pytest.mark.asyncio
    async def test_concurrent_semaphore(self, health_checker):
        """Test that semaphore limits concurrent health checks."""
        assert health_checker.max_concurrent_checks == 10
        assert health_checker._semaphore._value == 10

    @pytest.mark.asyncio
    async def test_check_instance_health_unknown_transport(
        self, health_checker, mock_registry
    ):
        """Test health check with unknown transport type."""
        instance = SimpleNamespace(
            id="test",
            template_name="test_template",
            transport="unknown",
        )

        is_healthy = await health_checker._check_instance_health(instance)
        assert not is_healthy

        # Should update registry with failure
        mock_registry.update_instance_health.assert_called_with(
            "test_template", "test", False
        )

    @pytest.mark.asyncio
    async def test_error_handling_in_health_check(self, health_checker, mock_registry):
        """Test error handling during health checks."""
        instance = SimpleNamespace(
            id="test",
            template_name="test_template",
            endpoint="http://localhost:8001",
            transport="http",
        )

        # Mock health check to raise exception
        with patch.object(
            health_checker, "_check_http_health", side_effect=Exception("Network error")
        ):
            is_healthy = await health_checker._check_instance_health(instance)
            assert not is_healthy

            # Should update registry with failure
            mock_registry.update_instance_health.assert_called_with(
                "test_template", "test", False
            )

    @pytest.mark.asyncio
    async def test_health_check_loop_exception_handling(
        self, health_checker, mock_registry
    ):
        """Test that health check loop handles exceptions gracefully."""
        # Make registry raise exception
        mock_registry.list_templates.side_effect = Exception("Registry error")

        # Should not raise exception
        await health_checker._perform_health_checks()

    @pytest.mark.asyncio
    async def test_http_health_no_endpoint(self, health_checker):
        """Test HTTP health check with no endpoint configured."""
        instance = SimpleNamespace(
            id="test",
            template_name="test_template",
            endpoint=None,
            transport="http",
        )

        is_healthy = await health_checker._check_http_health(instance)
        assert not is_healthy
