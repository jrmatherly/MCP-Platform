"""
Pytest configuration for Filesystem template tests.

This module provides Filesystem template-specific fixtures and configuration
for testing the Filesystem MCP server template functionality.
"""

import sys
from pathlib import Path

import pytest

# Add template directory to Python path for local imports
template_dir = Path(__file__).parent.parent
sys.path.insert(0, str(template_dir))

# =============================================================================
# Filesystem Template-Specific Fixtures
# =============================================================================


@pytest.fixture(scope="session")
def template_config():
    """
    Load Filesystem template configuration for tests.

    Scope: session - Template config is static, shared across all tests.
    Automatically discovers and loads the template.json configuration
    for the Filesystem template, providing access to schema and metadata.

    Returns:
        dict: Complete template configuration from template.json.

    Features:
        - Auto-discovery of template.json in parent directory
        - JSON parsing with UTF-8 encoding support
        - Session-scoped for performance (config doesn't change)
    """
    import json

    config_file = template_dir / "template.json"
    with open(config_file, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture
def mock_env_vars(monkeypatch):
    """
    Mock environment variables for Filesystem template testing.

    Scope: function - Fresh environment setup per test for isolation.
    Sets up common environment variables expected by Filesystem template tests.

    Args:
        monkeypatch: Pytest monkeypatch fixture for environment modification.

    Environment Variables Set:
        - LOG_LEVEL: Set to INFO for consistent logging during tests

    Usage:
        Test functions can depend on this fixture to get a clean
        environment with Filesystem template-specific variables configured.
    """
    monkeypatch.setenv("LOG_LEVEL", "INFO")
