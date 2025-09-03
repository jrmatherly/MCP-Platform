"""
Integration tests for Trino MCP server template structure and configuration.

Tests template structure, documentation completeness, and integration
with the MCP Platform template discovery system.
"""

import json
import os
from pathlib import Path

import pytest


class TestTrinoTemplate:
    """Test Trino MCP server template structure and configuration."""

    @pytest.fixture
    def template_dir(self) -> Path:
        """Get Trino template directory."""
        return Path(__file__).parent.parent

    def test_template_structure(self, template_dir):
        """Test Trino template has required files and structure."""
        # Required files
        required_files = ["template.json", "README.md", "USAGE.md", "docs/index.md"]

        for file_path in required_files:
            assert (
                template_dir / file_path
            ).exists(), f"Missing required file: {file_path}"

        # Required directories
        required_dirs = ["docs", "tests"]

        for dir_path in required_dirs:
            assert (
                template_dir / dir_path
            ).is_dir(), f"Missing required directory: {dir_path}"

    def test_template_json_validity(self, template_dir):
        """Test template.json is valid JSON with required fields."""
        template_file = template_dir / "template.json"

        with open(template_file, "r") as f:
            template_data = json.load(f)

        # Required fields
        required_fields = [
            "id",
            "name",
            "description",
            "version",
            "author",
            "category",
            "docker_image",
            "docker_tag",
            "transport",
            "config_schema",
            "capabilities",
            "tools",
        ]

        for field in required_fields:
            assert field in template_data, f"Missing required field: {field}"

        # Validate specific values
        assert template_data["id"] == "trino"
        assert template_data["category"] == "Database"
        assert template_data["docker_image"] == "ghcr.io/tuannvm/mcp-trino"
        assert template_data["origin"] == "external"

    def test_configuration_schema_structure(self, template_dir):
        """Test configuration schema has proper structure."""
        template_file = template_dir / "template.json"

        with open(template_file, "r") as f:
            template_data = json.load(f)

        config_schema = template_data["config_schema"]

        # Schema structure
        assert "type" in config_schema
        assert config_schema["type"] == "object"
        assert "properties" in config_schema
        assert "required" in config_schema
        assert "anyOf" in config_schema

        # Required properties
        required = config_schema["required"]
        assert "trino_host" in required
        assert "trino_user" in required

        # Properties should have proper structure
        properties = config_schema["properties"]
        for prop_name, prop_config in properties.items():
            assert "type" in prop_config
            assert "title" in prop_config
            assert "description" in prop_config
            assert "env_mapping" in prop_config

    def test_transport_configuration(self, template_dir):
        """Test transport configuration is properly defined."""
        template_file = template_dir / "template.json"

        with open(template_file, "r") as f:
            template_data = json.load(f)

        transport = template_data["transport"]

        # Trino MCP only supports stdio transport
        assert transport["default"] == "stdio"
        assert transport["supported"] == ["stdio"]

    def test_capabilities_examples(self, template_dir):
        """Test capabilities include proper examples."""
        template_file = template_dir / "template.json"

        with open(template_file, "r") as f:
            template_data = json.load(f)

        capabilities = template_data["capabilities"]

        # Should have at least 4 capabilities
        assert len(capabilities) >= 4

        for capability in capabilities:
            assert "name" in capability
            assert "description" in capability
            assert "example" in capability
            assert len(capability["description"]) > 0
            assert len(capability["example"]) > 0

    def test_documentation_completeness(self, template_dir):
        """Test documentation files are complete and well-formed."""
        # README.md
        readme = template_dir / "README.md"
        readme_content = readme.read_text()

        assert "Trino MCP Server" in readme_content
        assert "Configuration" in readme_content
        assert "Quick Start" in readme_content
        assert "Authentication" in readme_content
        assert "JWT" in readme_content
        assert "OAuth2" in readme_content

        # USAGE.md
        usage = template_dir / "USAGE.md"
        usage_content = usage.read_text()

        assert "Trino MCP Server Usage Guide" in usage_content
        assert "Available Tools" in usage_content
        assert "list_catalogs" in usage_content
        assert "execute_query" in usage_content
        assert "Setup Scenarios" in usage_content

        # docs/index.md
        docs = template_dir / "docs" / "index.md"
        docs_content = docs.read_text()

        assert "Complete Tool Reference" in docs_content
        assert "Tool Catalog" in docs_content
        assert "Authentication Configuration" in docs_content

    def test_feature_toggles_documented(self, template_dir):
        """Test feature toggles are properly documented."""
        readme = template_dir / "README.md"
        readme_content = readme.read_text()

        # Security features
        assert "read-only" in readme_content.lower()
        assert "⚠️" in readme_content  # Warning symbols for security

        # Access control features
        assert "allowed_catalogs" in readme_content
        assert "allowed_schemas" in readme_content
        assert "catalog_regex" in readme_content or "regex" in readme_content

    def test_environment_variable_mapping(self, template_dir):
        """Test all configuration properties have environment variable mappings."""
        template_file = template_dir / "template.json"

        with open(template_file, "r") as f:
            template_data = json.load(f)

        properties = template_data["config_schema"]["properties"]

        for prop_name, prop_config in properties.items():
            assert (
                "env_mapping" in prop_config
            ), f"Property {prop_name} missing env_mapping"
            env_var = prop_config["env_mapping"]

            # Environment variables should follow naming convention
            if prop_name.startswith("trino_"):
                assert env_var.startswith("TRINO_")
            elif prop_name.startswith("oauth2_"):
                assert env_var.startswith("TRINO_OAUTH2_")
            elif prop_name == "log_level":
                assert env_var == "MCP_LOG_LEVEL"

    def test_docker_configuration(self, template_dir):
        """Test Docker configuration is properly set up."""
        template_file = template_dir / "template.json"

        with open(template_file, "r") as f:
            template_data = json.load(f)

        # Docker image should be the upstream image
        assert template_data["docker_image"] == "ghcr.io/tuannvm/mcp-trino"
        assert template_data["docker_tag"] == "latest"
        assert template_data["has_image"] is True
        assert template_data["origin"] == "external"

        # Ports configuration
        assert "ports" in template_data
        ports = template_data["ports"]
        assert "8080" in ports
        assert ports["8080"] == 8080

    def test_tools_parameter_validation(self, template_dir):
        """Test tool parameters are properly validated."""
        template_file = template_dir / "template.json"

        with open(template_file, "r") as f:
            template_data = json.load(f)

        tools = template_data["tools"]

        # Find execute_query tool
        execute_query = next(t for t in tools if t["name"] == "execute_query")

        # Check required parameters
        query_param = next(
            p for p in execute_query["parameters"] if p["name"] == "query"
        )
        assert query_param["required"] is True
        assert query_param["type"] == "string"

        # Check optional parameters
        catalog_param = next(
            p for p in execute_query["parameters"] if p["name"] == "catalog"
        )
        assert catalog_param["required"] is False

        # Find describe_table tool
        describe_table = next(t for t in tools if t["name"] == "describe_table")

        # All describe_table parameters should be required
        for param in describe_table["parameters"]:
            if param["name"] in ["catalog", "schema", "table"]:
                assert param["required"] is True

    def test_examples_and_usage_patterns(self, template_dir):
        """Test examples are provided for different usage patterns."""
        template_file = template_dir / "template.json"

        with open(template_file, "r") as f:
            template_data = json.load(f)

        # Examples section should exist
        assert "examples" in template_data
        examples = template_data["examples"]

        # CLI usage examples
        assert "cli_usage" in examples
        cli_examples = examples["cli_usage"]
        assert len(cli_examples) >= 3

        # Should include examples for different auth methods
        cli_text = " ".join(cli_examples)
        assert "auth_method='jwt'" in cli_text
        assert "auth_method='oauth2'" in cli_text

        # Client integration examples
        assert "client_integration" in examples

    def test_security_defaults(self, template_dir):
        """Test security-focused default configurations."""
        template_file = template_dir / "template.json"

        with open(template_file, "r") as f:
            template_data = json.load(f)

        properties = template_data["config_schema"]["properties"]

        # Read-only should be default
        assert properties["read_only"]["default"] is True

        # Authentication should default to basic (simplest)
        assert properties["auth_method"]["default"] == "basic"

        # Reasonable timeout defaults
        assert properties["query_timeout"]["default"] == 300  # 5 minutes
        assert properties["max_results"]["default"] == 1000  # Reasonable limit

        # Open catalog/schema access by default (can be restricted)
        assert properties["allowed_catalogs"]["default"] == "*"
        assert properties["allowed_schemas"]["default"] == "*"

    def test_database_category_consistency(self, template_dir):
        """Test consistency with other database templates."""
        template_file = template_dir / "template.json"

        with open(template_file, "r") as f:
            template_data = json.load(f)

        # Should be categorized as Database
        assert template_data["category"] == "Database"

        # Should have database-related tags
        tags = template_data["tags"]
        database_related_tags = ["sql", "database", "analytics"]

        for tag in database_related_tags:
            assert tag in tags

        # Should have query execution capability
        capabilities = template_data["capabilities"]
        capability_names = [cap["name"] for cap in capabilities]
        assert "Query Execution" in capability_names

    def test_version_format(self, template_dir):
        """Test version follows semantic versioning."""
        template_file = template_dir / "template.json"

        with open(template_file, "r") as f:
            template_data = json.load(f)

        version = template_data["version"]

        # Should follow semantic versioning (X.Y.Z)
        import re

        semver_pattern = r"^\d+\.\d+\.\d+$"
        assert re.match(
            semver_pattern, version
        ), f"Version {version} doesn't follow semantic versioning"
