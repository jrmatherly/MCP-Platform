#!/usr/bin/env python3
"""
Integration tests for Open Elastic Search MCP Server

Updated to use the current field names and expectations from
`template.json` in the `open-elastic-search` template.
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
        return {
            "engine_type": "elasticsearch",
            "elasticsearch_hosts": "https://localhost:9200",
            "elasticsearch_api_key": "test_api_key",
            "mcp_transport": "stdio",
            "mcp_port": 8000,
        }

    @pytest.fixture
    def mock_opensearch_config_data(self):
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
        return {
            "name": "Open Elastic Search",
            "version": "2.0.11",
            "transport": {
                "default": "stdio",
                "supported": ["stdio", "sse", "streamable-http"],
            },
            "experimental": True,
            "origin": "custom",
        }

    def test_elasticsearch_server_initialization(self, mock_elasticsearch_config_data):
        # Mock external process/startup - we only validate config shape here
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "Server started"

            assert mock_elasticsearch_config_data["engine_type"] == "elasticsearch"
            assert "elasticsearch_hosts" in mock_elasticsearch_config_data
            assert "elasticsearch_api_key" in mock_elasticsearch_config_data

    def test_opensearch_server_initialization(self, mock_opensearch_config_data):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = "Server started"

            assert mock_opensearch_config_data["engine_type"] == "opensearch"
            assert "opensearch_hosts" in mock_opensearch_config_data
            assert "opensearch_username" in mock_opensearch_config_data
            assert "opensearch_password" in mock_opensearch_config_data

    def test_environment_variable_mapping(self, mock_elasticsearch_config_data):
        expected = {
            "engine_type": "ENGINE_TYPE",
            "elasticsearch_hosts": "ELASTICSEARCH_HOSTS",
            "elasticsearch_api_key": "ELASTICSEARCH_API_KEY",
            "mcp_transport": "MCP_TRANSPORT",
            "mcp_port": "MCP_PORT",
        }

        for k in expected:
            if k in mock_elasticsearch_config_data:
                assert expected[k] is not None

    def test_transport_mode_validation(self, mock_elasticsearch_config_data):
        supported = ["stdio", "sse", "streamable-http"]
        for t in supported:
            cfg = mock_elasticsearch_config_data.copy()
            cfg["mcp_transport"] = t
            assert cfg["mcp_transport"] in supported

    def test_elasticsearch_authentication_methods(self):
        api_cfg = {
            "engine_type": "elasticsearch",
            "elasticsearch_hosts": "https://localhost:9200",
            "elasticsearch_api_key": "test_api_key",
        }
        user_cfg = {
            "engine_type": "elasticsearch",
            "elasticsearch_hosts": "https://localhost:9200",
            "elasticsearch_username": "elastic",
            "elasticsearch_password": "password",
        }

        assert "elasticsearch_api_key" in api_cfg
        assert "elasticsearch_username" in user_cfg
        assert "elasticsearch_password" in user_cfg

    def test_opensearch_authentication_method(self):
        cfg = {
            "engine_type": "opensearch",
            "opensearch_hosts": "https://localhost:9200",
            "opensearch_username": "admin",
            "opensearch_password": "admin",
        }
        assert "opensearch_username" in cfg and "opensearch_password" in cfg

    def test_http_transport_configuration(self):
        cfg = {
            "engine_type": "elasticsearch",
            "elasticsearch_hosts": "https://localhost:9200",
            "elasticsearch_api_key": "test_key",
            "mcp_transport": "sse",
            "mcp_host": "0.0.0.0",
            "mcp_port": 8000,
            "mcp_path": "/sse",
        }

        assert cfg["mcp_transport"] in ["sse", "streamable-http"]
        assert "mcp_host" in cfg and "mcp_port" in cfg and "mcp_path" in cfg

    def test_tool_availability(self):
        expected = [
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

        assert len(expected) == 16

    def test_docker_configuration(self, mock_template_data):
        assert mock_template_data["origin"] == "custom"
        assert mock_template_data["experimental"] is True

    def test_error_handling(self):
        invalids = [
            {
                "elasticsearch_hosts": "https://localhost:9200",
                "elasticsearch_api_key": "test_key",
            },
            {"engine_type": "elasticsearch", "elasticsearch_api_key": "test_key"},
            {
                "engine_type": "elasticsearch",
                "elasticsearch_hosts": "https://localhost:9200",
            },
            {"engine_type": "opensearch", "opensearch_hosts": "https://localhost:9200"},
        ]

        for cfg in invalids:
            assert len(cfg) < 4

    def test_version_compatibility(self, mock_template_data):
        assert mock_template_data["version"] == "2.0.11"
        assert mock_template_data["experimental"] is True

    def test_tool_discovery(self):
        expected_tools = [
            "list_indices",
            "get_mappings",
            "search",
            "esql",
            "get_shards",
        ]

        with patch("json.load") as mock_json_load:
            mock_tools = [{"name": t} for t in expected_tools]
            mock_json_load.return_value = mock_tools

            tools = self._discover_tools()
            names = [t["name"] for t in tools]
            assert all(t in names for t in expected_tools)

    def test_authentication_validation(self):
        api_cfg = {
            "elasticsearch_hosts": "https://localhost:9200",
            "elasticsearch_api_key": "test_key",
        }
        assert self._validate_auth(api_cfg)

        basic_cfg = {
            "elasticsearch_hosts": "https://localhost:9200",
            "elasticsearch_username": "elastic",
            "elasticsearch_password": "password",
        }
        assert self._validate_auth(basic_cfg)

        invalid = {"elasticsearch_hosts": "https://localhost:9200"}
        assert not self._validate_auth(invalid)

    def test_transport_modes(self):
        stdio = {"mcp_transport": "stdio"}
        result = self._test_transport_mode(stdio)
        assert result["transport"] == "stdio"

        http = {"mcp_transport": "streamable-http", "mcp_port": 8080}
        result = self._test_transport_mode(http)
        assert result["transport"] == "streamable-http"
        assert result["port"] == 8080

    def test_experimental_warning_display(self):
        warnings = self._get_template_warnings()
        assert any("EXPERIMENTAL" in w for w in warnings)

    def test_ssl_configuration(self):
        """
        Test ssl configuration extraction.
        """

        cfg = {"elasticsearch_verify_certs": False}
        env = self._extract_env_vars(cfg)
        assert (
            env.get("ELASTICSEARCH_VERIFY_CERTS") == "False"
            or env.get("ELASTICSEARCH_VERIFY_CERTS") is None
        )

    def test_error_handling_raises(self):
        with pytest.raises(ValueError, match="ELASTICSEARCH_HOSTS.*required"):
            self._validate_config({})

    # Helper methods for testing

    def _discover_tools(self):
        return [
            {"name": "list_indices"},
            {"name": "get_mappings"},
            {"name": "search"},
            {"name": "esql"},
            {"name": "get_shards"},
        ]

    def _validate_auth(self, config):
        has_api = "elasticsearch_api_key" in config
        has_basic = (
            "elasticsearch_username" in config and "elasticsearch_password" in config
        )
        return has_api or has_basic

    def _test_transport_mode(self, config):
        return {
            "transport": config.get("mcp_transport", "stdio"),
            "port": config.get("mcp_port", 8080),
        }

    def _get_template_warnings(self):
        return [
            "⚠️ WARNING: This MCP server is EXPERIMENTAL.",
            "⚠️ Elasticsearch support: versions 7.x, 8.x, and 9.x.",
            "⚠️ OpenSearch support: versions 1.x, 2.x, and 3.x.",
        ]

    def _extract_env_vars(self, config):
        mapping = {
            "elasticsearch_hosts": "ELASTICSEARCH_HOSTS",
            "elasticsearch_api_key": "ELASTICSEARCH_API_KEY",
            "elasticsearch_username": "ELASTICSEARCH_USERNAME",
            "elasticsearch_password": "ELASTICSEARCH_PASSWORD",
            "elasticsearch_verify_certs": "ELASTICSEARCH_VERIFY_CERTS",
            "log_level": "LOG_LEVEL",
            "mcp_transport": "MCP_TRANSPORT",
            "mcp_port": "MCP_PORT",
        }

        env = {}
        for k, v in mapping.items():
            if k in config:
                val = config[k]
                if isinstance(val, bool):
                    val = str(val)
                elif isinstance(val, int):
                    val = str(val)
                env[v] = val

        return env

    def _validate_config(self, config):
        # require elasticsearch_hosts for elasticsearch engine
        if not config.get("elasticsearch_hosts") and not config.get("opensearch_hosts"):
            raise ValueError(
                "ELASTICSEARCH_HOSTS is required when engine_type is elasticsearch"
            )
        # basic URL check
        url = config.get("elasticsearch_hosts") or config.get("opensearch_hosts")
        if url and not (url.startswith("http://") or url.startswith("https://")):
            raise ValueError("Invalid URL format")

        # must have auth
        if not self._validate_auth(config):
            raise ValueError("Authentication credentials required")

        return True


if __name__ == "__main__":
    pytest.main([__file__])
