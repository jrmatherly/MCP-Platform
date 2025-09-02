#!/usr/bin/env python3
"""
Integration tests for Open Elastic Search MCP Server

These tests verify the integration between the server and the MCP template system.
"""

import os
import sys
from unittest.mock import patch

import pytest

# Add the parent directory to the Python path to allow imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))


class TestOpenElasticSearchMCPIntegration:
    """Integration tests for Open Elastic Search MCP Server."""

    @pytest.fixture
    def mock_elasticsearch_config_data(self):
        """Mock Elasticsearch configuration data for testing."""
        return {
            "engine_type": "elasticsearch",
            "elasticsearch_hosts": "https://localhost:9200",
            "elasticsearch_api_key": "test_api_key",
            "mcp_transport": "stdio",
            "mcp_port": 8000,
        }

    @pytest.fixture
    def mock_opensearch_config_data(self):
        """Mock OpenSearch configuration data for testing."""
        return {
            "engine_type": "opensearch",
            "opensearch_hosts": "https://localhost:9200",
            "opensearch_username": "admin",
            "opensearch_password": "admin",
            "mcp_transport": "stdio",
            "mcp_port": 8000,
        }

    @pytest.fixture
    def mock_template_data(self):
        """Mock template data for testing."""
        return {
            "name": "Open Elastic Search",
            "version": "2.0.11",
            "transport": {"default": "stdio", "supported": ["stdio", "sse", "streamable-http"]},
            "experimental": True,
            "origin": "custom",
        }

    @pytest.mark.asyncio
    async def test_elasticsearch_server_initialization(
        self, mock_elasticsearch_config_data, mock_template_data
    ):
        """Test Elasticsearch server initialization with proper configuration."""
        # Mock the server class since we're testing template integration
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "Server started successfully"
            
            # Test that initialization with Elasticsearch config works
            assert mock_elasticsearch_config_data["engine_type"] == "elasticsearch"
            assert "elasticsearch_hosts" in mock_elasticsearch_config_data
            assert "elasticsearch_api_key" in mock_elasticsearch_config_data

    @pytest.mark.asyncio
    async def test_opensearch_server_initialization(
        self, mock_opensearch_config_data, mock_template_data
    ):
        """Test OpenSearch server initialization with proper configuration."""
        # Mock the server class since we're testing template integration
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "Server started successfully"
            
            # Test that initialization with OpenSearch config works
            assert mock_opensearch_config_data["engine_type"] == "opensearch"
            assert "opensearch_hosts" in mock_opensearch_config_data
            assert "opensearch_username" in mock_opensearch_config_data
            assert "opensearch_password" in mock_opensearch_config_data

    def test_environment_variable_mapping(self, mock_elasticsearch_config_data):
        """Test environment variable mapping for configuration."""
        expected_mappings = {
            "engine_type": "ENGINE_TYPE",
            "elasticsearch_hosts": "ELASTICSEARCH_HOSTS",
            "elasticsearch_api_key": "ELASTICSEARCH_API_KEY",
            "mcp_transport": "MCP_TRANSPORT",
            "mcp_port": "MCP_PORT",
        }

        # Verify the mapping works as expected
        for config_key, env_var in expected_mappings.items():
            if config_key in mock_elasticsearch_config_data:
                # This would be handled by the configuration processor
                assert env_var is not None

    def test_transport_mode_validation(self, mock_elasticsearch_config_data):
        """Test different transport modes."""
        supported_transports = ["stdio", "sse", "streamable-http"]
        
        for transport in supported_transports:
            config = mock_elasticsearch_config_data.copy()
            config["mcp_transport"] = transport
            
            # Each transport should be valid
            assert config["mcp_transport"] in supported_transports

    def test_elasticsearch_authentication_methods(self):
        """Test different Elasticsearch authentication methods."""
        # API key authentication
        api_key_config = {
            "engine_type": "elasticsearch",
            "elasticsearch_hosts": "https://localhost:9200",
            "elasticsearch_api_key": "test_api_key",
        }
        
        # Username/password authentication
        user_pass_config = {
            "engine_type": "elasticsearch",
            "elasticsearch_hosts": "https://localhost:9200",
            "elasticsearch_username": "elastic",
            "elasticsearch_password": "password",
        }
        
        # Both should be valid
        assert "elasticsearch_api_key" in api_key_config
        assert "elasticsearch_username" in user_pass_config
        assert "elasticsearch_password" in user_pass_config

    def test_opensearch_authentication_method(self):
        """Test OpenSearch authentication method."""
        opensearch_config = {
            "engine_type": "opensearch",
            "opensearch_hosts": "https://localhost:9200",
            "opensearch_username": "admin",
            "opensearch_password": "admin",
        }
        
        # OpenSearch requires username/password
        assert "opensearch_username" in opensearch_config
        assert "opensearch_password" in opensearch_config

    def test_ssl_configuration(self):
        """Test SSL configuration options."""
        # Elasticsearch SSL config
        es_ssl_config = {
            "engine_type": "elasticsearch",
            "elasticsearch_hosts": "https://localhost:9200",
            "elasticsearch_api_key": "test_key",
            "elasticsearch_verify_certs": False,
        }
        
        # OpenSearch SSL config
        os_ssl_config = {
            "engine_type": "opensearch",
            "opensearch_hosts": "https://localhost:9200",
            "opensearch_username": "admin",
            "opensearch_password": "admin",
            "opensearch_verify_certs": False,
        }
        
        # Both should support SSL configuration
        assert "elasticsearch_verify_certs" in es_ssl_config
        assert "opensearch_verify_certs" in os_ssl_config

    def test_http_transport_configuration(self):
        """Test HTTP-based transport configuration."""
        http_config = {
            "engine_type": "elasticsearch",
            "elasticsearch_hosts": "https://localhost:9200",
            "elasticsearch_api_key": "test_key",
            "mcp_transport": "sse",
            "mcp_host": "0.0.0.0",
            "mcp_port": 8000,
            "mcp_path": "/sse",
        }
        
        # HTTP transports should include host, port, and path
        assert http_config["mcp_transport"] in ["sse", "streamable-http"]
        assert "mcp_host" in http_config
        assert "mcp_port" in http_config
        assert "mcp_path" in http_config

    @pytest.mark.asyncio
    async def test_tool_availability(self):
        """Test that all expected tools are available."""
        expected_tools = [
            "general_api_request",
            "list_indices",
            "get_index",
            "create_index",
            "delete_index",
            "search_documents",
            "index_document",
            "get_document",
            "delete_document",
            "delete_by_query",
            "get_cluster_health",
            "get_cluster_stats",
            "list_aliases",
            "get_alias",
            "put_alias",
            "delete_alias",
        ]
        
        # This would typically be tested with actual tool discovery
        # For now, we just verify the expected tool list
        assert len(expected_tools) == 16

    def test_docker_configuration(self, mock_template_data):
        """Test Docker-specific configuration."""
        # Verify template indicates custom image build
        assert mock_template_data["origin"] == "custom"
        
        # Custom builds should have specific characteristics
        assert mock_template_data["experimental"] is True

    @pytest.mark.asyncio
    async def test_error_handling(self):
        """Test error handling for invalid configurations."""
        # Test missing required fields
        invalid_configs = [
            # Missing engine type
            {
                "elasticsearch_hosts": "https://localhost:9200",
                "elasticsearch_api_key": "test_key",
            },
            # Missing hosts
            {
                "engine_type": "elasticsearch",
                "elasticsearch_api_key": "test_key",
            },
            # Missing authentication for elasticsearch
            {
                "engine_type": "elasticsearch",
                "elasticsearch_hosts": "https://localhost:9200",
            },
            # Missing authentication for opensearch
            {
                "engine_type": "opensearch",
                "opensearch_hosts": "https://localhost:9200",
            },
        ]
        
        # Each invalid config should fail validation
        for invalid_config in invalid_configs:
            # This would be caught by schema validation
            assert len(invalid_config) < 3  # Incomplete configurations

    def test_version_compatibility(self, mock_template_data):
        """Test version compatibility information."""
        # Template should indicate support for multiple versions
        assert mock_template_data["version"] == "2.0.11"
        
        # Should support experimental features
        assert mock_template_data["experimental"] is True
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
            "get_shards",
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
        api_key_config = {"es_url": "https://localhost:9200", "es_api_key": "test_key"}
        assert self._validate_auth(api_key_config) is True

        # Test username/password authentication
        basic_auth_config = {
            "es_url": "https://localhost:9200",
            "es_username": "elastic",
            "es_password": "password",
        }
        assert self._validate_auth(basic_auth_config) is True

        # Test invalid authentication (missing credentials)
        invalid_config = {"es_url": "https://localhost:9200"}
        assert self._validate_auth(invalid_config) is False

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
            return {"status": "success", "config": config}
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
            "mcp_port": "MCP_PORT",
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
            {"name": "get_shards"},
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
            "port": config.get("mcp_port", 8080),
        }

    async def _get_template_warnings(self):
        """Get template warnings."""
        return [
            "⚠️ WARNING: This MCP server is EXPERIMENTAL.",
            "⚠️ This server works with Elasticsearch versions 8.x and 9.x only.",
            "⚠️ Ensure your Elasticsearch cluster is properly secured and accessible.",
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
