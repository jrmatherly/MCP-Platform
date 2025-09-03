"""
Unit tests for Trino template configuration and validation.

Tests the Trino template's configuration schema and validation
without requiring complex template management infrastructure.
"""

import json
import os


class TestTrinoTemplateConfiguration:
    """Test Trino template configuration validation and processing."""

    def test_template_json_structure(self):
        """Test Trino template.json has required structure."""
        template_path = os.path.join(os.path.dirname(__file__), "..", "template.json")

        with open(template_path, "r") as f:
            template_config = json.load(f)

        # Verify required template fields
        assert template_config["name"] == "Trino MCP Server"
        assert template_config["description"]
        assert template_config["version"] == "1.0.0"
        assert template_config["docker_image"] == "ghcr.io/tuannvm/mcp-trino"
        assert template_config["docker_tag"] == "latest"
        assert template_config["has_image"] is True
        assert template_config["origin"] == "external"
        assert template_config["category"] == "Database"

        # Verify supported transports (Trino MCP uses stdio only)
        assert template_config["transport"]["default"] == "stdio"
        assert template_config["transport"]["supported"] == ["stdio"]

        # Verify configuration schema exists
        assert "config_schema" in template_config
        assert "properties" in template_config["config_schema"]

    def test_authentication_configuration_schema(self):
        """Test authentication configuration options."""
        template_path = os.path.join(os.path.dirname(__file__), "..", "template.json")

        with open(template_path, "r") as f:
            template_config = json.load(f)

        config_schema = template_config["config_schema"]
        properties = config_schema["properties"]

        # Required fields
        assert "trino_host" in properties
        assert "trino_user" in properties
        assert properties["trino_host"]["env_mapping"] == "TRINO_HOST"
        assert properties["trino_user"]["env_mapping"] == "TRINO_USER"

        # Authentication methods
        assert "auth_method" in properties
        auth_method = properties["auth_method"]
        assert auth_method["enum"] == ["basic", "jwt", "oauth2"]
        assert auth_method["default"] == "basic"
        assert auth_method["env_mapping"] == "TRINO_AUTH_METHOD"

        # JWT authentication
        assert "jwt_token" in properties
        assert properties["jwt_token"]["env_mapping"] == "TRINO_JWT_TOKEN"

        # OAuth2 authentication
        oauth2_fields = ["oauth2_client_id", "oauth2_client_secret", "oauth2_token_url"]
        for field in oauth2_fields:
            assert field in properties
            assert properties[field]["env_mapping"] == f"TRINO_{field.upper()}"

    def test_access_control_configuration(self):
        """Test access control configuration options."""
        template_path = os.path.join(os.path.dirname(__file__), "..", "template.json")

        with open(template_path, "r") as f:
            template_config = json.load(f)

        properties = template_config["config_schema"]["properties"]

        # Read-only mode
        assert "read_only" in properties
        assert properties["read_only"]["default"] is True
        assert properties["read_only"]["env_mapping"] == "TRINO_READ_ONLY"

        # Catalog filtering
        assert "allowed_catalogs" in properties
        assert properties["allowed_catalogs"]["default"] == "*"
        assert properties["allowed_catalogs"]["env_mapping"] == "TRINO_ALLOWED_CATALOGS"

        assert "catalog_regex" in properties
        assert properties["catalog_regex"]["env_mapping"] == "TRINO_CATALOG_REGEX"

        # Schema filtering
        assert "allowed_schemas" in properties
        assert properties["allowed_schemas"]["default"] == "*"
        assert properties["allowed_schemas"]["env_mapping"] == "TRINO_ALLOWED_SCHEMAS"

        assert "schema_regex" in properties
        assert properties["schema_regex"]["env_mapping"] == "TRINO_SCHEMA_REGEX"

    def test_performance_configuration(self):
        """Test performance-related configuration options."""
        template_path = os.path.join(os.path.dirname(__file__), "..", "template.json")

        with open(template_path, "r") as f:
            template_config = json.load(f)

        properties = template_config["config_schema"]["properties"]

        # Query timeout
        assert "query_timeout" in properties
        timeout_config = properties["query_timeout"]
        assert timeout_config["default"] == 300
        assert timeout_config["minimum"] == 10
        assert timeout_config["maximum"] == 3600
        assert timeout_config["env_mapping"] == "TRINO_QUERY_TIMEOUT"

        # Max results
        assert "max_results" in properties
        results_config = properties["max_results"]
        assert results_config["default"] == 1000
        assert results_config["minimum"] == 1
        assert results_config["maximum"] == 10000
        assert results_config["env_mapping"] == "TRINO_MAX_RESULTS"

        # Connection settings
        assert "trino_port" in properties
        port_config = properties["trino_port"]
        assert port_config["default"] == 8080
        assert port_config["minimum"] == 1
        assert port_config["maximum"] == 65535
        assert port_config["env_mapping"] == "TRINO_PORT"

    def test_conditional_authentication_requirements(self):
        """Test conditional requirements for different authentication methods."""
        template_path = os.path.join(os.path.dirname(__file__), "..", "template.json")

        with open(template_path, "r") as f:
            template_config = json.load(f)

        config_schema = template_config["config_schema"]

        # Check anyOf conditions for authentication
        assert "anyOf" in config_schema
        any_of_conditions = config_schema["anyOf"]

        # Should have conditions for basic, jwt, and oauth2
        assert len(any_of_conditions) == 3

        # Find JWT condition
        jwt_condition = next(
            c
            for c in any_of_conditions
            if c["properties"]["auth_method"]["const"] == "jwt"
        )
        assert "jwt_token" in jwt_condition["required"]

        # Find OAuth2 condition
        oauth2_condition = next(
            c
            for c in any_of_conditions
            if c["properties"]["auth_method"]["const"] == "oauth2"
        )
        oauth2_required = oauth2_condition["required"]
        assert "oauth2_client_id" in oauth2_required
        assert "oauth2_client_secret" in oauth2_required
        assert "oauth2_token_url" in oauth2_required

    def test_tools_and_capabilities(self):
        """Test that tools and capabilities are properly defined."""
        template_path = os.path.join(os.path.dirname(__file__), "..", "template.json")

        with open(template_path, "r") as f:
            template_config = json.load(f)

        # Check capabilities
        capabilities = template_config["capabilities"]
        assert len(capabilities) >= 4

        capability_names = [cap["name"] for cap in capabilities]
        expected_capabilities = [
            "Catalog Discovery",
            "Schema Inspection",
            "Query Execution",
            "Access Control",
            "Multi-Source Support",
        ]

        for expected in expected_capabilities:
            assert expected in capability_names

        # Check tools
        tools = template_config["tools"]
        assert len(tools) >= 7

        tool_names = [tool["name"] for tool in tools]
        expected_tools = [
            "list_catalogs",
            "list_schemas",
            "list_tables",
            "describe_table",
            "execute_query",
            "get_query_status",
            "cancel_query",
            "get_cluster_info",
        ]

        for expected in expected_tools:
            assert expected in tool_names

        # Verify specific tool parameters
        execute_query_tool = next(t for t in tools if t["name"] == "execute_query")
        query_param = next(
            p for p in execute_query_tool["parameters"] if p["name"] == "query"
        )
        assert query_param["required"] is True
        assert query_param["type"] == "string"
