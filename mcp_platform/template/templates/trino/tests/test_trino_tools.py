"""
Unit tests for Trino template tool validation and categorization.

Tests tool definitions, parameter validation, and access control
for the Trino MCP server template.
"""

import json
import os


class TestTrinoTemplateTools:
    """Test Trino template tool validation and categorization."""

    def test_tool_categorization_and_naming(self):
        """Test tool categorization follows Trino conventions."""
        template_path = os.path.join(os.path.dirname(__file__), "..", "template.json")

        with open(template_path, "r") as f:
            template_config = json.load(f)

        tools = template_config["tools"]

        # Discovery tools
        discovery_tools = [
            "list_catalogs",
            "list_schemas",
            "list_tables",
            "get_cluster_info",
        ]

        # Inspection tools
        inspection_tools = ["describe_table"]

        # Query tools
        query_tools = ["execute_query", "get_query_status", "cancel_query"]

        all_expected_tools = discovery_tools + inspection_tools + query_tools

        tool_names = [tool["name"] for tool in tools]

        for expected_tool in all_expected_tools:
            assert (
                expected_tool in tool_names
            ), f"Missing expected tool: {expected_tool}"

        # Verify tool naming follows Trino patterns
        for tool_name in tool_names:
            # Should use snake_case
            assert "_" in tool_name or tool_name in ["catalogs", "schemas", "tables"]
            # Should be descriptive and action-oriented
            assert len(tool_name) > 3

    def test_discovery_tools_structure(self):
        """Test discovery tools have proper parameter structure."""
        template_path = os.path.join(os.path.dirname(__file__), "..", "template.json")

        with open(template_path, "r") as f:
            template_config = json.load(f)

        tools = {tool["name"]: tool for tool in template_config["tools"]}

        # list_catalogs should have no parameters
        list_catalogs = tools["list_catalogs"]
        assert list_catalogs["parameters"] == []
        assert "List all accessible Trino catalogs" in list_catalogs["description"]

        # list_schemas should require catalog parameter
        list_schemas = tools["list_schemas"]
        schema_params = {p["name"]: p for p in list_schemas["parameters"]}
        assert "catalog" in schema_params
        assert schema_params["catalog"]["required"] is True
        assert schema_params["catalog"]["type"] == "string"

        # list_tables should require catalog and schema
        list_tables = tools["list_tables"]
        table_params = {p["name"]: p for p in list_tables["parameters"]}
        assert "catalog" in table_params
        assert "schema" in table_params
        assert table_params["catalog"]["required"] is True
        assert table_params["schema"]["required"] is True

    def test_query_execution_tool_parameters(self):
        """Test query execution tool has proper parameters."""
        template_path = os.path.join(os.path.dirname(__file__), "..", "template.json")

        with open(template_path, "r") as f:
            template_config = json.load(f)

        tools = {tool["name"]: tool for tool in template_config["tools"]}
        execute_query = tools["execute_query"]

        params = {p["name"]: p for p in execute_query["parameters"]}

        # Required query parameter
        assert "query" in params
        assert params["query"]["required"] is True
        assert params["query"]["type"] == "string"
        assert "SQL query" in params["query"]["description"]

        # Optional context parameters
        assert "catalog" in params
        assert params["catalog"]["required"] is False
        assert params["catalog"]["type"] == "string"

        assert "schema" in params
        assert params["schema"]["required"] is False
        assert params["schema"]["type"] == "string"

        # Should mention read-only restrictions
        assert "read-only" in execute_query["description"].lower()

    def test_table_inspection_tools(self):
        """Test table inspection tools have proper structure."""
        template_path = os.path.join(os.path.dirname(__file__), "..", "template.json")

        with open(template_path, "r") as f:
            template_config = json.load(f)

        tools = {tool["name"]: tool for tool in template_config["tools"]}
        describe_table = tools["describe_table"]

        params = {p["name"]: p for p in describe_table["parameters"]}

        # Should require catalog, schema, and table
        required_params = ["catalog", "schema", "table"]
        for param_name in required_params:
            assert param_name in params
            assert params[param_name]["required"] is True
            assert params[param_name]["type"] == "string"

    def test_query_management_tools(self):
        """Test query management tools are properly defined."""
        template_path = os.path.join(os.path.dirname(__file__), "..", "template.json")

        with open(template_path, "r") as f:
            template_config = json.load(f)

        tools = {tool["name"]: tool for tool in template_config["tools"]}

        # get_query_status tool
        get_status = tools["get_query_status"]
        status_params = {p["name"]: p for p in get_status["parameters"]}
        assert "query_id" in status_params
        assert status_params["query_id"]["required"] is True
        assert "query ID" in status_params["query_id"]["description"]

        # cancel_query tool
        cancel_query = tools["cancel_query"]
        cancel_params = {p["name"]: p for p in cancel_query["parameters"]}
        assert "query_id" in cancel_params
        assert cancel_params["query_id"]["required"] is True

    def test_access_control_integration(self):
        """Test tools integrate with access control configuration."""
        template_path = os.path.join(os.path.dirname(__file__), "..", "template.json")

        with open(template_path, "r") as f:
            template_config = json.load(f)

        # Access control should be mentioned in capabilities
        capabilities = template_config["capabilities"]
        access_control_cap = next(
            cap for cap in capabilities if "Access Control" in cap["name"]
        )

        assert "catalog" in access_control_cap["description"].lower()
        assert "schema" in access_control_cap["description"].lower()
        assert "filter" in access_control_cap["description"].lower()

        # Configuration should support filtering
        properties = template_config["config_schema"]["properties"]

        filtering_configs = [
            "allowed_catalogs",
            "catalog_regex",
            "allowed_schemas",
            "schema_regex",
        ]

        for config_name in filtering_configs:
            assert config_name in properties

    def test_read_only_mode_restrictions(self):
        """Test read-only mode restrictions are documented."""
        template_path = os.path.join(os.path.dirname(__file__), "..", "template.json")

        with open(template_path, "r") as f:
            template_config = json.load(f)

        # Read-only should be default
        properties = template_config["config_schema"]["properties"]
        assert properties["read_only"]["default"] is True

        # execute_query should mention restrictions
        tools = {tool["name"]: tool for tool in template_config["tools"]}
        execute_query = tools["execute_query"]
        assert "read-only" in execute_query["description"].lower()

        # Should have capability explaining read-only
        capabilities = template_config["capabilities"]
        query_capability = next(
            cap for cap in capabilities if "Query Execution" in cap["name"]
        )
        assert "read-only" in query_capability["example"].lower()

    def test_environment_variable_consistency(self):
        """Test environment variables are consistent with upstream."""
        template_path = os.path.join(os.path.dirname(__file__), "..", "template.json")

        with open(template_path, "r") as f:
            template_config = json.load(f)

        properties = template_config["config_schema"]["properties"]

        # Core Trino connection variables
        trino_vars = {
            "trino_host": "TRINO_HOST",
            "trino_port": "TRINO_PORT",
            "trino_user": "TRINO_USER",
        }

        for prop_name, expected_env in trino_vars.items():
            assert properties[prop_name]["env_mapping"] == expected_env

        # Authentication variables
        auth_vars = {
            "auth_method": "TRINO_AUTH_METHOD",
            "jwt_token": "TRINO_JWT_TOKEN",
            "oauth2_client_id": "TRINO_OAUTH2_CLIENT_ID",
            "oauth2_client_secret": "TRINO_OAUTH2_CLIENT_SECRET",
            "oauth2_token_url": "TRINO_OAUTH2_TOKEN_URL",
        }

        for prop_name, expected_env in auth_vars.items():
            assert properties[prop_name]["env_mapping"] == expected_env

        # Access control variables
        access_vars = {
            "read_only": "TRINO_READ_ONLY",
            "allowed_catalogs": "TRINO_ALLOWED_CATALOGS",
            "catalog_regex": "TRINO_CATALOG_REGEX",
            "allowed_schemas": "TRINO_ALLOWED_SCHEMAS",
            "schema_regex": "TRINO_SCHEMA_REGEX",
            "query_timeout": "TRINO_QUERY_TIMEOUT",
            "max_results": "TRINO_MAX_RESULTS",
        }

        for prop_name, expected_env in access_vars.items():
            assert properties[prop_name]["env_mapping"] == expected_env

    def test_tool_parameter_descriptions(self):
        """Test all tool parameters have clear descriptions."""
        template_path = os.path.join(os.path.dirname(__file__), "..", "template.json")

        with open(template_path, "r") as f:
            template_config = json.load(f)

        tools = template_config["tools"]

        for tool in tools:
            assert "description" in tool
            assert len(tool["description"]) > 10  # Meaningful description

            for param in tool["parameters"]:
                assert "name" in param
                assert "description" in param
                assert "type" in param
                assert "required" in param

                # Description should be helpful
                assert len(param["description"]) > 5

                # Type should be valid
                assert param["type"] in [
                    "string",
                    "integer",
                    "boolean",
                    "array",
                    "object",
                ]
