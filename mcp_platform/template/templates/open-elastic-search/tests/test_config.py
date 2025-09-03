#!/usr/bin/env python3
"""
Configuration tests for Open Elastic Search MCP Server.

These tests are aligned with the current `template.json` for the
`open-elastic-search` template and validate the schema names, transport,
tools and authentication conditional rules.
"""

import json
import os
import sys

import pytest

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))


class TestOpenElasticSearchConfig:
    """Test configuration handling for Open Elastic Search MCP Server."""

    def _load_template(self):
        template_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "template.json"
        )
        with open(template_path, "r") as f:
            return json.load(f)

    def _load_tools(self):
        tools_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "tools.json"
        )
        with open(tools_path, "r") as f:
            return json.load(f)

    def test_template_json_structure(self):
        template_data = self._load_template()

        # Basic fields
        assert template_data["name"] == "Open Elastic Search"
        assert template_data.get("experimental") is True
        assert "elasticsearch" in template_data.get("tags", [])
        assert "opensearch" in template_data.get("tags", [])
        assert template_data["docker_image"] == "dataeverything/mcp-open-elastic-search"
        assert template_data["docker_tag"] == "latest"
        assert template_data["origin"] == "custom"

    def test_config_schema_properties(self):
        template_data = self._load_template()
        config_schema = template_data["config_schema"]
        assert config_schema["type"] == "object"
        properties = config_schema["properties"]

        # engine_type and its enum
        assert "engine_type" in properties
        assert properties["engine_type"]["enum"] == ["elasticsearch", "opensearch"]

        # Elasticsearch properties
        for name in (
            "elasticsearch_hosts",
            "elasticsearch_api_key",
            "elasticsearch_username",
            "elasticsearch_password",
            "elasticsearch_verify_certs",
        ):
            assert name in properties

        # OpenSearch properties
        for name in ("opensearch_hosts", "opensearch_username", "opensearch_password"):
            assert name in properties

        # MCP transport properties
        for name in ("mcp_transport", "mcp_host", "mcp_port", "mcp_path"):
            assert name in properties

    def test_transport_options(self):
        template_data = self._load_template()
        transport_config = template_data["transport"]

        assert transport_config["default"] == "stdio"
        assert set(transport_config["supported"]) == {"stdio", "sse", "streamable-http"}

        # mcp_transport enum in schema
        mcp_transport = template_data["config_schema"]["properties"]["mcp_transport"]
        assert set(mcp_transport["enum"]) == {"stdio", "sse", "streamable-http"}

    def test_authentication_schema_anyof(self):
        template_data = self._load_template()
        config_schema = template_data["config_schema"]

        assert "anyOf" in config_schema
        any_of = config_schema["anyOf"]
        assert len(any_of) == 2

        # Find the elasticsearch and opensearch constraints
        es = next(
            c
            for c in any_of
            if c["properties"]["engine_type"]["const"] == "elasticsearch"
        )
        os = next(
            c for c in any_of if c["properties"]["engine_type"]["const"] == "opensearch"
        )

        # Elasticsearch must require hosts and oneOf auth options
        assert "elasticsearch_hosts" in es.get("required", [])
        assert "oneOf" in es
        assert len(es["oneOf"]) == 2

        # OpenSearch must require hosts + username/password
        for req in ("opensearch_hosts", "opensearch_username", "opensearch_password"):
            assert req in os.get("required", [])

    def test_sensitive_and_env_mappings(self):
        template_data = self._load_template()
        props = template_data["config_schema"]["properties"]

        # sensitive fields
        assert props["elasticsearch_api_key"].get("sensitive") is True
        assert props["elasticsearch_password"].get("sensitive") is True
        assert props["opensearch_password"].get("sensitive") is True

        # env mappings
        expected_env = {
            "engine_type": "ENGINE_TYPE",
            "elasticsearch_hosts": "ELASTICSEARCH_HOSTS",
            "elasticsearch_api_key": "ELASTICSEARCH_API_KEY",
            "elasticsearch_username": "ELASTICSEARCH_USERNAME",
            "elasticsearch_password": "ELASTICSEARCH_PASSWORD",
            "elasticsearch_verify_certs": "ELASTICSEARCH_VERIFY_CERTS",
            "opensearch_hosts": "OPENSEARCH_HOSTS",
            "opensearch_username": "OPENSEARCH_USERNAME",
            "opensearch_password": "OPENSEARCH_PASSWORD",
            "opensearch_verify_certs": "OPENSEARCH_VERIFY_CERTS",
            "mcp_transport": "MCP_TRANSPORT",
            "mcp_host": "MCP_HOST",
            "mcp_port": "MCP_PORT",
            "mcp_path": "MCP_PATH",
        }

        for k, v in expected_env.items():
            assert props[k]["env_mapping"] == v

    def test_warnings_and_defaults(self):
        template_data = self._load_template()
        warnings = template_data.get("warnings", [])
        assert len(warnings) == 4
        assert any("EXPERIMENTAL" in w for w in warnings)
        assert any("Elasticsearch" in w for w in warnings)
        assert any("OpenSearch" in w for w in warnings)

        props = template_data["config_schema"]["properties"]
        assert props["elasticsearch_verify_certs"].get("default") is False
        assert props["mcp_transport"].get("default") == "stdio"
        assert props["mcp_port"].get("default") == 8000
        assert props["mcp_path"].get("default") == "/mcp"

    def test_tools_json_structure(self):
        tools = self._load_tools()
        assert isinstance(tools, list)
        # The template provides a comprehensive list of tools (16 entries)
        assert len(tools) == 16

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

        tool_names = [t["name"] for t in tools]
        for expected in expected_tools:
            assert expected in tool_names


if __name__ == "__main__":
    pytest.main([__file__])
