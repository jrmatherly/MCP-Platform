#!/usr/bin/env python3
"""
Configuration tests for Open Elastic Search MCP Server

Tests for configuration parsing and validation.
"""

import json
import os
import sys

import pytest

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))


class TestOpenElasticSearchConfig:
    """Test configuration handling for Open Elastic Search MCP Server."""

    def test_template_json_structure(self):
        """Test that template.json has correct structure."""
        template_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "template.json"
        )

        with open(template_path, "r") as f:
            template_data = json.load(f)

        # Check required fields
        assert "name" in template_data
        assert "description" in template_data
        assert "version" in template_data
        assert "config_schema" in template_data

        # Check Open Elastic Search-specific fields
        assert template_data["name"] == "Open Elastic Search"
        assert template_data["experimental"] is True
        assert "elasticsearch" in template_data["tags"]
        assert "opensearch" in template_data["tags"]
        assert template_data["docker_image"] == "dataeverything/mcp-open-elastic-search"
        assert template_data["docker_tag"] == "latest"
        assert template_data["origin"] == "custom"

    def test_config_schema_validation(self):
        """Test configuration schema validation."""
        template_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "template.json"
        )

        with open(template_path, "r") as f:
            template_data = json.load(f)

        config_schema = template_data["config_schema"]

        # Check that required fields exist
        assert "properties" in config_schema
        properties = config_schema["properties"]

        # Check engine type configuration
        assert "engine_type" in properties
        assert properties["engine_type"]["type"] == "string"
        assert properties["engine_type"]["enum"] == ["elasticsearch", "opensearch"]

        # Check Elasticsearch configuration
        assert "elasticsearch_hosts" in properties
        assert "elasticsearch_api_key" in properties
        assert "elasticsearch_username" in properties
        assert "elasticsearch_password" in properties
        assert "elasticsearch_verify_certs" in properties

        # Check OpenSearch configuration
        assert "opensearch_hosts" in properties
        assert "opensearch_username" in properties
        assert "opensearch_password" in properties
        assert "opensearch_verify_certs" in properties

        # Check transport configuration
        assert "mcp_transport" in properties
        assert "mcp_host" in properties
        assert "mcp_port" in properties
        assert "mcp_path" in properties

    def test_transport_options(self):
        """Test transport configuration options."""
        template_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "template.json"
        )

        with open(template_path, "r") as f:
            template_data = json.load(f)

        # Check transport support
        transport_config = template_data["transport"]
        assert transport_config["default"] == "stdio"
        assert set(transport_config["supported"]) == {"stdio", "sse", "streamable-http"}

        # Check MCP transport enum
        mcp_transport = template_data["config_schema"]["properties"]["mcp_transport"]
        assert set(mcp_transport["enum"]) == {"stdio", "sse", "streamable-http"}

    def test_authentication_schema(self):
        """Test authentication schema validation."""
        template_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "template.json"
        )

        with open(template_path, "r") as f:
            template_data = json.load(f)

        config_schema = template_data["config_schema"]

        # Check anyOf constraint for different engine types
        assert "anyOf" in config_schema
        any_of_constraints = config_schema["anyOf"]

        # Should have constraints for both elasticsearch and opensearch
        assert len(any_of_constraints) == 2

        # Find elasticsearch constraint
        es_constraint = None
        os_constraint = None
        for constraint in any_of_constraints:
            if constraint["properties"]["engine_type"]["const"] == "elasticsearch":
                es_constraint = constraint
            elif constraint["properties"]["engine_type"]["const"] == "opensearch":
                os_constraint = constraint

        assert es_constraint is not None
        assert os_constraint is not None

        # Check Elasticsearch authentication options
        assert "oneOf" in es_constraint
        es_auth_options = es_constraint["oneOf"]
        assert len(es_auth_options) == 2  # API key or username/password

        # Check OpenSearch authentication requirements
        assert "opensearch_hosts" in os_constraint["required"]
        assert "opensearch_username" in os_constraint["required"]
        assert "opensearch_password" in os_constraint["required"]

    def test_sensitive_fields(self):
        """Test that sensitive fields are properly marked."""
        template_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "template.json"
        )

        with open(template_path, "r") as f:
            template_data = json.load(f)

        properties = template_data["config_schema"]["properties"]

        # Check that password and API key fields are marked as sensitive
        sensitive_fields = [
            "elasticsearch_api_key",
            "elasticsearch_password",
            "opensearch_password"
        ]

        for field in sensitive_fields:
            assert properties[field].get("sensitive") is True

    def test_environment_mappings(self):
        """Test that environment variable mappings are correct."""
        template_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "template.json"
        )

        with open(template_path, "r") as f:
            template_data = json.load(f)

        properties = template_data["config_schema"]["properties"]

        # Check environment mappings
        expected_mappings = {
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
            "mcp_path": "MCP_PATH"
        }

        for field, expected_env in expected_mappings.items():
            assert properties[field]["env_mapping"] == expected_env

    def test_warnings_present(self):
        """Test that appropriate warnings are present."""
        template_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "template.json"
        )

        with open(template_path, "r") as f:
            template_data = json.load(f)

        warnings = template_data["warnings"]
        assert len(warnings) == 4

        # Check for experimental warning
        experimental_warning = next(
            (w for w in warnings if "EXPERIMENTAL" in w), None
        )
        assert experimental_warning is not None

        # Check for version support warnings
        es_warning = next(
            (w for w in warnings if "Elasticsearch" in w and "7.x, 8.x" in w), None
        )
        assert es_warning is not None

        os_warning = next(
            (w for w in warnings if "OpenSearch" in w and "1.x, 2.x" in w), None
        )
        assert os_warning is not None

        schema = template_data["config_schema"]
        properties = schema["properties"]

        # Check required environment variable mappings
        assert properties["es_url"]["env_mapping"] == "ES_URL"
        assert properties["es_api_key"]["env_mapping"] == "ES_API_KEY"
        assert properties["es_username"]["env_mapping"] == "ES_USERNAME"
        assert properties["es_password"]["env_mapping"] == "ES_PASSWORD"
        assert properties["es_ssl_skip_verify"]["env_mapping"] == "ES_SSL_SKIP_VERIFY"

        # Check sensitive fields are marked
        assert properties["es_api_key"]["sensitive"] is True
        assert properties["es_password"]["sensitive"] is True

        # Check required fields
        assert "es_url" in schema["required"]

    def test_authentication_requirements(self):
        """Test authentication requirement validation."""
        template_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "template.json"
        )

        with open(template_path, "r") as f:
            template_data = json.load(f)

        schema = template_data["config_schema"]

        # Check oneOf requirement for authentication
        assert "oneOf" in schema
        one_of = schema["oneOf"]

        # Should require either API key or username/password
        api_key_option = next(
            (opt for opt in one_of if "es_api_key" in opt["required"]), None
        )
        basic_auth_option = next(
            (opt for opt in one_of if "es_username" in opt["required"]), None
        )

        assert api_key_option is not None
        assert basic_auth_option is not None
        assert "es_password" in basic_auth_option["required"]

    def test_default_values(self):
        """Test default configuration values."""
        template_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "template.json"
        )

        with open(template_path, "r") as f:
            template_data = json.load(f)

        properties = template_data["config_schema"]["properties"]

        # Check default values
        assert properties["es_ssl_skip_verify"]["default"] is False
        assert properties["log_level"]["default"] == "INFO"
        assert properties["mcp_transport"]["default"] == "stdio"
        assert properties["mcp_port"]["default"] == 8080

    def test_transport_configuration(self):
        """Test transport configuration."""
        template_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "template.json"
        )

        with open(template_path, "r") as f:
            template_data = json.load(f)

        transport = template_data["transport"]

        assert transport["default"] == "stdio"
        assert "stdio" in transport["supported"]
        assert "http" in transport["supported"]

    def test_warning_messages(self):
        """Test that warning messages are present."""
        template_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "template.json"
        )

        with open(template_path, "r") as f:
            template_data = json.load(f)

        warnings = template_data.get("warnings", [])

        # Check for experimental warning
        experimental_warning = any("EXPERIMENTAL" in warning for warning in warnings)
        assert experimental_warning

        # Check for version warning
        version_warning = any("8.x and 9.x" in warning for warning in warnings)
        assert version_warning

    def test_tools_json_structure(self):
        """Test that tools.json has correct structure."""
        tools_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "tools.json"
        )

        with open(tools_path, "r") as f:
            tools_data = json.load(f)

        # Should be a list of tools
        assert isinstance(tools_data, list)
        assert len(tools_data) == 5  # Expected 5 tools

        expected_tools = [
            "list_indices",
            "get_mappings",
            "search",
            "esql",
            "get_shards",
        ]
        tool_names = [tool["name"] for tool in tools_data]

        for expected_tool in expected_tools:
            assert expected_tool in tool_names

    def test_tool_schemas(self):
        """Test tool input schemas."""
        tools_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "tools.json"
        )

        with open(tools_path, "r") as f:
            tools_data = json.load(f)

        for tool in tools_data:
            assert "name" in tool
            assert "description" in tool
            assert "inputSchema" in tool

            # Check input schema structure
            schema = tool["inputSchema"]
            assert "type" in schema
            assert schema["type"] == "object"
            assert "properties" in schema
            assert "required" in schema

    def test_docker_configuration(self):
        """Test Docker-specific configuration."""
        template_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), "template.json"
        )

        with open(template_path, "r") as f:
            template_data = json.load(f)

        assert template_data["has_image"] is True
        assert template_data["origin"] == "external"
        assert template_data["docker_image"] == "dataeverything/mcp-elasticsearch"
        assert template_data["docker_tag"] == "latest"


if __name__ == "__main__":
    pytest.main([__file__])
