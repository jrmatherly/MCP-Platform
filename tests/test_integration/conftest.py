"""
Integration test specific fixtures.

These fixtures support integration testing with real components
and end-to-end scenarios.
"""

import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest

# =============================================================================
# Integration Test Environment Fixtures
# =============================================================================


@pytest.fixture(scope="session")
def integration_test_workspace():
    """
    Create a dedicated workspace for integration tests.

    Scope: session - Expensive filesystem operations shared across all tests.
    Creates temporary directory structure with cleanup after all tests complete.
    Session scope ensures single workspace creation for performance optimization.

    Returns:
        Path: Temporary workspace directory with predefined structure.

    Directory Structure:
        - templates/: Template storage for integration testing
        - deployments/: Deployment artifacts and logs
        - logs/: Test execution logging

    Features:
        - Automatic cleanup after session completion
        - Isolated test environment per session
        - Predictable directory structure for integration scenarios
    """
    with tempfile.TemporaryDirectory(prefix="mcp_integration_test_") as temp_dir:
        workspace = Path(temp_dir)

        # Create directory structure
        (workspace / "templates").mkdir()
        (workspace / "deployments").mkdir()
        (workspace / "logs").mkdir()

        yield workspace


@pytest.fixture
def integration_templates_dir(integration_test_workspace):
    """
    Create a templates directory with real template examples.

    Scope: function - Fresh template directory per test for isolation.
    Creates demo and filesystem templates with complete configuration for
    realistic integration testing scenarios.

    Args:
        integration_test_workspace: Session workspace fixture dependency.

    Returns:
        Path: Templates directory with demo and filesystem template examples.

    Templates Created:
        - demo/: Demo MCP server with Docker configuration
        - filesystem/: Filesystem MCP server with volume mount support

    Features:
        - Complete template.json configurations
        - Dockerfile examples for containerization
        - Realistic config schemas for testing
    """
    templates_dir = integration_test_workspace / "templates"

    # Create demo template
    demo_dir = templates_dir / "demo"
    demo_dir.mkdir()

    demo_template = demo_dir / "template.json"
    demo_template.write_text(
        """{
        "name": "Demo MCP Server",
        "description": "A demo MCP server for testing",
        "version": "1.0.0",
        "docker_image": "demo/mcp-server:latest",
        "tool_discovery": "dynamic",
        "tool_endpoint": "/tools",
        "has_image": true,
        "origin": "internal",
        "config_schema": {
            "type": "object",
            "properties": {
                "log_level": {
                    "type": "string",
                    "description": "Logging level",
                    "default": "INFO",
                    "env_mapping": "LOG_LEVEL"
                },
                "port": {
                    "type": "integer",
                    "description": "Server port",
                    "default": 8080,
                    "env_mapping": "SERVER_PORT"
                }
            }
        }
    }"""
    )

    demo_dockerfile = demo_dir / "Dockerfile"
    demo_dockerfile.write_text(
        """FROM python:3.9-slim
WORKDIR /app
COPY pyproject.toml uv.lock ./
COPY . .
RUN pip install uv && uv sync --frozen --no-dev
EXPOSE 8080
CMD ["python", "server.py"]
"""
    )

    # Create filesystem template
    fs_dir = templates_dir / "filesystem"
    fs_dir.mkdir()

    fs_template = fs_dir / "template.json"
    fs_template.write_text(
        """{
        "name": "Filesystem MCP Server",
        "description": "A filesystem MCP server for testing",
        "version": "1.0.0",
        "docker_image": "filesystem/mcp-server:latest",
        "tool_discovery": "static",
        "has_image": true,
        "origin": "external",
        "config_schema": {
            "type": "object",
            "properties": {
                "allowed_dirs": {
                    "type": "string",
                    "description": "Allowed directories",
                    "env_mapping": "ALLOWED_DIRS",
                    "volume_mount": true,
                    "command_arg": true
                },
                "read_only": {
                    "type": "boolean",
                    "description": "Read-only mode",
                    "default": false,
                    "env_mapping": "READ_ONLY"
                }
            },
            "required": ["allowed_dirs"]
        }
    }"""
    )

    return templates_dir


@pytest.fixture
def full_deployment_config():
    """Complete deployment configuration for integration tests."""
    return {
        "template": "demo",
        "backend": "docker",
        "config": {"log_level": "DEBUG", "port": 9090},
        "environment": {"NODE_ENV": "test", "DEBUG": "true"},
        "volumes": ["/host/data:/app/data:ro"],
    }


@pytest.fixture
def multi_backend_config():
    """Configuration for testing multiple backends."""
    return {
        "backends": {
            "docker": {"enabled": True, "socket_path": "/var/run/docker.sock"},
            "kubernetes": {
                "enabled": True,
                "kubeconfig_path": "~/.kube/config",
                "namespace": "mcp-test",
            },
            "mock": {"enabled": True},
        }
    }


# =============================================================================
# Real Component Integration Fixtures
# =============================================================================


@pytest.fixture
def real_deployment_manager():
    """
    Create a real DeploymentManager for integration tests.

    Scope: function - Fresh manager per test for isolation and safety.
    Uses mock backend for integration testing to ensure safety while
    maintaining realistic deployment manager behavior and API.

    Returns:
        DeploymentManager: Real deployment manager with mock backend.

    Safety Features:
        - Mock backend prevents actual Docker/K8s resource creation
        - Real manager API for authentic integration testing
        - Isolated per test to prevent cross-test contamination

    Usage:
        Ideal for testing deployment workflows, configuration processing,
        and manager coordination without external infrastructure dependencies.
    """
    from mcp_platform.core.deployment_manager import DeploymentManager

    return DeploymentManager("mock")  # Use mock backend for safety in tests


@pytest.fixture
def real_config_processor():
    """Create a real ConfigProcessor for integration tests."""
    from mcp_platform.core.config_processor import ConfigProcessor

    return ConfigProcessor()


@pytest.fixture
def integration_test_deployment():
    """Create a test deployment for integration scenarios."""
    return {
        "id": "integration-test-deployment-001",
        "template": "demo",
        "status": "running",
        "backend_type": "mock",
        "created_at": "2024-01-15T10:00:00Z",
        "config": {"log_level": "INFO", "port": 8080},
        "environment": {"NODE_ENV": "test"},
        "ports": ["8080:8080"],
        "volumes": [],
    }


# =============================================================================
# End-to-End Scenario Fixtures
# =============================================================================


@pytest.fixture
def e2e_scenario_data():
    """Data for end-to-end testing scenarios."""
    return {
        "templates": ["demo", "filesystem"],
        "backends": ["mock", "docker"],
        "deployments": [
            {"template": "demo", "backend": "mock", "config": {"log_level": "INFO"}},
            {
                "template": "filesystem",
                "backend": "mock",
                "config": {"allowed_dirs": "/tmp", "read_only": True},
            },
        ],
    }


@pytest.fixture
def mock_external_services():
    """Mock external services for integration tests."""
    return {
        "docker_registry": Mock(),
        "kubernetes_api": Mock(),
        "monitoring_service": Mock(),
    }
