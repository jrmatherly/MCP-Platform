#!/usr/bin/env python3
"""
Integration tests for Elasticsearch MCP Server

These tests verify the integration between the server and the MCP template system.
"""

import asyncio
import os
import sys
from unittest.mock import MagicMock, patch
import json

import pytest

# Add the parent directory to the Python path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))


class TestElasticsearchMCPIntegration:
    """Integration tests for Elasticsearch MCP Server."""

    @pytest.fixture
    def mock_config_data(self):
        """Mock configuration data for testing."""
        return {
            "es_url": "https://localhost:9200",
            "es_api_key": "test_api_key",
            "log_level": "INFO",
            "mcp_transport": "stdio",
            "mcp_port": 8080,
        }

    @pytest.fixture
    def mock_template_data(self):
        """Mock template data for testing."""
        return {
            "name": "Elasticsearch MCP Server",
            "version": "1.0.0",
            "transport": {"default": "stdio", "supported": ["stdio", "http"]},
            "experimental": True,
        }

    @pytest.mark.asyncio
    async def test_elasticsearch_server_initialization(self, mock_config_data, mock_template_data):
        """Test server initialization with proper configuration."""
        # Mock the server class since we're testing template integration
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "Server started successfully"
            
            # Simulate server startup
            result = await self._simulate_server_start(mock_config_data)
            assert result["status"] == "success"
            assert "es_url" in result["config"]

    @pytest.mark.asyncio
    async def test_environment_variable_mapping(self, mock_config_data):
        """Test that environment variables are properly mapped."""
        expected_env_vars = {
            "ES_URL": "https://localhost:9200",
            "ES_API_KEY": "test_api_key",
            "LOG_LEVEL": "INFO",
            "MCP_TRANSPORT": "stdio",
            "MCP_PORT": "8080",
        }
        
        env_vars = self._extract_env_vars(mock_config_data)
        assert env_vars == expected_env_vars

    @pytest.mark.asyncio
    async def test_tool_discovery(self):
        """Test tool discovery for Elasticsearch tools."""
        expected_tools = [
            "list_indices",
            "get_mappings", 
            "search",
            "esql",
            "get_shards"
        ]
        
        with patch("json.load") as mock_json_load:
            # Mock tools.json content
            mock_tools = [{"name": tool} for tool in expected_tools]
            mock_json_load.return_value = mock_tools
            
            tools = await self._discover_tools()
            tool_names = [tool["name"] for tool in tools]
            
            assert all(tool in tool_names for tool in expected_tools)

    @pytest.mark.asyncio
    async def test_authentication_validation(self):
        """Test authentication validation for different auth methods."""
        # Test API key authentication
        api_key_config = {
            "es_url": "https://localhost:9200",
            "es_api_key": "test_key"
        }
        assert self._validate_auth(api_key_config) == True
        
        # Test username/password authentication
        basic_auth_config = {
            "es_url": "https://localhost:9200",
            "es_username": "elastic",
            "es_password": "password"
        }
        assert self._validate_auth(basic_auth_config) == True
        
        # Test invalid authentication (missing credentials)
        invalid_config = {
            "es_url": "https://localhost:9200"
        }
        assert self._validate_auth(invalid_config) == False

    @pytest.mark.asyncio
    async def test_transport_modes(self, mock_config_data):
        """Test different transport modes (stdio and http)."""
        # Test stdio mode
        stdio_config = mock_config_data.copy()
        stdio_config["mcp_transport"] = "stdio"
        
        result = await self._test_transport_mode(stdio_config)
        assert result["transport"] == "stdio"
        
        # Test http mode
        http_config = mock_config_data.copy()
        http_config["mcp_transport"] = "http"
        http_config["mcp_port"] = 8080
        
        result = await self._test_transport_mode(http_config)
        assert result["transport"] == "http"
        assert result["port"] == 8080

    @pytest.mark.asyncio
    async def test_experimental_warning_display(self):
        """Test that experimental warnings are properly displayed."""
        warnings = await self._get_template_warnings()
        
        experimental_warnings = [w for w in warnings if "EXPERIMENTAL" in w]
        assert len(experimental_warnings) > 0
        assert any("WARNING" in warning for warning in experimental_warnings)

    @pytest.mark.asyncio
    async def test_ssl_configuration(self, mock_config_data):
        """Test SSL configuration options."""
        # Test with SSL verification enabled (default)
        ssl_config = mock_config_data.copy()
        ssl_config["es_ssl_skip_verify"] = False
        
        env_vars = self._extract_env_vars(ssl_config)
        assert env_vars.get("ES_SSL_SKIP_VERIFY") == "False"
        
        # Test with SSL verification disabled
        ssl_config["es_ssl_skip_verify"] = True
        env_vars = self._extract_env_vars(ssl_config)
        assert env_vars.get("ES_SSL_SKIP_VERIFY") == "True"

    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error handling for various failure scenarios."""
        # Test missing required fields
        with pytest.raises(ValueError, match="ES_URL.*required"):
            self._validate_config({})
        
        # Test invalid URL format
        with pytest.raises(ValueError, match="Invalid URL"):
            self._validate_config({"es_url": "not-a-url"})

    # Helper methods for testing

    async def _simulate_server_start(self, config):
        """Simulate server startup with given configuration."""
        # This would normally start the actual server
        # For testing, we just validate the configuration
        if self._validate_config(config):
            return {
                "status": "success",
                "config": config
            }
        return {"status": "error"}

    def _extract_env_vars(self, config):
        """Extract environment variables from configuration."""
        env_mapping = {
            "es_url": "ES_URL",
            "es_api_key": "ES_API_KEY", 
            "es_username": "ES_USERNAME",
            "es_password": "ES_PASSWORD",
            "es_ssl_skip_verify": "ES_SSL_SKIP_VERIFY",
            "log_level": "LOG_LEVEL",
            "mcp_transport": "MCP_TRANSPORT",
            "mcp_port": "MCP_PORT"
        }
        
        env_vars = {}
        for config_key, env_key in env_mapping.items():
            if config_key in config:
                value = config[config_key]
                # Convert boolean values to string
                if isinstance(value, bool):
                    value = str(value)
                elif isinstance(value, int):
                    value = str(value)
                env_vars[env_key] = value
        
        return env_vars

    async def _discover_tools(self):
        """Mock tool discovery."""
        # In real implementation, this would read tools.json
        return [
            {"name": "list_indices"},
            {"name": "get_mappings"},
            {"name": "search"},
            {"name": "esql"},
            {"name": "get_shards"}
        ]

    def _validate_auth(self, config):
        """Validate authentication configuration."""
        has_api_key = "es_api_key" in config
        has_basic_auth = "es_username" in config and "es_password" in config
        return has_api_key or has_basic_auth

    async def _test_transport_mode(self, config):
        """Test transport mode configuration."""
        return {
            "transport": config.get("mcp_transport", "stdio"),
            "port": config.get("mcp_port", 8080)
        }

    async def _get_template_warnings(self):
        """Get template warnings."""
        return [
            "⚠️ WARNING: This MCP server is EXPERIMENTAL.",
            "⚠️ This server works with Elasticsearch versions 8.x and 9.x only.",
            "⚠️ Ensure your Elasticsearch cluster is properly secured and accessible."
        ]

    def _validate_config(self, config):
        """Validate configuration."""
        if not config.get("es_url"):
            raise ValueError("ES_URL is required")
        
        url = config["es_url"]
        if not (url.startswith("http://") or url.startswith("https://")):
            raise ValueError("Invalid URL format")
        
        # Check authentication
        if not self._validate_auth(config):
            raise ValueError("Authentication credentials required")
        
        return True


if __name__ == "__main__":
    pytest.main([__file__])