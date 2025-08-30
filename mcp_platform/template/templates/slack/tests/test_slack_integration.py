"""
Integration tests for Slack MCP server template.

These tests verify the Slack template structure and basic functionality
without requiring full deployment infrastructure.
"""

import json
from pathlib import Path

import pytest


class TestSlackTemplate:
    """Test Slack MCP server template structure and configuration."""

    @pytest.fixture
    def template_dir(self) -> Path:
        """Get Slack template directory."""
        return Path(__file__).parent.parent

    def test_template_structure(self, template_dir):
        """Test Slack template has required files and structure."""
        # Required files
        required_files = [
            "template.json",
            "README.md",
            "USAGE.md",
            "Dockerfile",
            "script.sh",
        ]

        for file_path in required_files:
            assert (
                template_dir / file_path
            ).exists(), f"Missing required file: {file_path}"

        # Required directories
        required_dirs = ["tests"]

        for dir_path in required_dirs:
            assert (
                template_dir / dir_path
            ).is_dir(), f"Missing required directory: {dir_path}"

    def test_template_json_validity(self, template_dir):
        """Test template.json is valid JSON with required fields."""
        template_json = template_dir / "template.json"

        with open(template_json, "r") as f:
            config = json.load(f)

        # Required top-level fields
        required_fields = [
            "name",
            "description",
            "version",
            "author",
            "category",
            "tags",
            "docker_image",
            "docker_tag",
            "transport",
            "capabilities",
            "config_schema",
        ]

        for field in required_fields:
            assert field in config, f"Missing required field: {field}"

        # Verify basic field types
        assert isinstance(config["name"], str)
        assert isinstance(config["description"], str)
        assert isinstance(config["version"], str)
        assert isinstance(config["tags"], list)
        assert isinstance(config["capabilities"], list)
        assert isinstance(config["config_schema"], dict)

    def test_configuration_schema_structure(self, template_dir):
        """Test configuration schema has proper structure."""
        template_json = template_dir / "template.json"

        with open(template_json, "r") as f:
            config = json.load(f)

        schema = config["config_schema"]

        # Required schema structure
        assert "type" in schema
        assert schema["type"] == "object"
        assert "properties" in schema

        properties = schema["properties"]

        # Test key Slack-specific configuration properties
        slack_core_props = [
            "slack_mcp_xoxc_token",
            "slack_mcp_xoxd_token",
            "slack_mcp_xoxp_token",
            "slack_mcp_port",
            "slack_mcp_host",
            "slack_mcp_log_level",
            "slack_mcp_add_message_tool",
            "slack_mcp_users_cache",
            "slack_mcp_channels_cache",
        ]

        for prop in slack_core_props:
            assert prop in properties, f"Missing configuration property: {prop}"

        # Test environment variable mappings
        for prop_name, prop_config in properties.items():
            if "env_mapping" in prop_config:
                assert isinstance(prop_config["env_mapping"], str)
                assert len(prop_config["env_mapping"]) > 0

    def test_transport_configuration(self, template_dir):
        """Test transport configuration is properly defined."""
        template_json = template_dir / "template.json"

        with open(template_json, "r") as f:
            config = json.load(f)

        transport = config["transport"]

        assert "default" in transport
        assert "supported" in transport
        assert transport["default"] == "stdio"

        # Slack supports stdio and SSE transports
        supported = transport["supported"]
        assert "stdio" in supported
        assert "sse" in supported

    def test_capabilities_examples(self, template_dir):
        """Test capabilities include proper examples."""
        template_json = template_dir / "template.json"

        with open(template_json, "r") as f:
            config = json.load(f)

        capabilities = config["capabilities"]
        assert len(capabilities) >= 5

        # Each capability should have required fields
        for cap in capabilities:
            assert "name" in cap
            assert "description" in cap
            assert "example" in cap
            assert "example_args" in cap
            assert "example_response" in cap

        # Verify Slack-specific capabilities
        cap_names = [cap["name"] for cap in capabilities]
        expected_caps = [
            "conversations_history",
            "conversations_replies",
            "conversations_add_message",
            "search_messages",
            "channel_management",
            "user_management",
        ]

        for expected in expected_caps:
            assert expected in cap_names

    def test_documentation_completeness(self, template_dir):
        """Test documentation files are complete and well-formed."""
        readme_file = template_dir / "README.md"
        usage_file = template_dir / "USAGE.md"

        # Check README content
        with open(readme_file, "r") as f:
            readme_content = f.read()

        readme_sections = [
            "# Slack MCP Server",
            "## Features",
            "## Quick Start",
            "## Configuration",
            "## Available Tools",
            "## Authentication Modes",
            "## Safety Features",
            "## Transport Modes",
            "## Troubleshooting",
        ]

        for section in readme_sections:
            assert section in readme_content, f"Missing README section: {section}"

        # Check USAGE content
        with open(usage_file, "r") as f:
            usage_content = f.read()

        usage_sections = [
            "# Slack MCP Server Usage Guide",
            "## Authentication Methods",
            "## Configuration Examples",
            "## Tool Usage Examples",
            "## Docker Usage",
            "## Integration Examples",
            "## Troubleshooting Guide",
        ]

        for section in usage_sections:
            assert section in usage_content, f"Missing USAGE section: {section}"

    def test_slack_specific_features(self, template_dir):
        """Test Slack-specific features are properly documented."""
        template_json = template_dir / "template.json"

        with open(template_json, "r") as f:
            config = json.load(f)

        # Test examples section
        assert "examples" in config
        examples = config["examples"]

        # Should have examples for different authentication modes using korotovsky naming
        example_sections = [
            "cookie_authentication",
            "oauth_authentication",
            "message_posting",
        ]
        for section in example_sections:
            assert section in examples, f"Missing example section: {section}"

        # Test category and tags
        assert config["category"] == "Communication"

        slack_tags = ["slack", "messaging", "collaboration", "workspace"]
        for tag in slack_tags:
            assert tag in config["tags"], f"Missing tag: {tag}"

    def test_environment_variable_mapping(self, template_dir):
        """Test environment variable mappings are consistent."""
        template_json = template_dir / "template.json"

        with open(template_json, "r") as f:
            config = json.load(f)

        properties = config["config_schema"]["properties"]

        # Test sensitive configuration is marked properly using korotovsky naming
        sensitive_props = [
            "slack_mcp_xoxc_token",
            "slack_mcp_xoxd_token",
            "slack_mcp_xoxp_token",
            "slack_mcp_sse_api_key",
        ]
        for prop in sensitive_props:
            if prop in properties:
                prop_config = properties[prop]
                assert prop_config.get(
                    "sensitive", False
                ), f"Property {prop} should be marked as sensitive"

        # Test boolean defaults using actual properties
        boolean_props = {
            "slack_mcp_custom_tls": False,
            "slack_mcp_server_ca_toolkit": False,
            "slack_mcp_server_ca_insecure": False,
            "slack_mcp_add_message_mark": False,
        }

        for prop, expected_default in boolean_props.items():
            if prop in properties:
                prop_config = properties[prop]
                assert (
                    prop_config.get("default") == expected_default
                ), f"Property {prop} has incorrect default"

    def test_docker_configuration(self, template_dir):
        """Test Docker configuration is present and valid."""
        dockerfile = template_dir / "Dockerfile"
        script_file = template_dir / "script.sh"

        # Check Dockerfile exists and has basic structure
        assert dockerfile.exists()

        with open(dockerfile, "r") as f:
            dockerfile_content = f.read()

        dockerfile_requirements = [
            "FROM ghcr.io/korotovsky/slack-mcp-server",
            "WORKDIR /app",
            "EXPOSE 3003",
            "CMD",
        ]

        for requirement in dockerfile_requirements:
            assert (
                requirement in dockerfile_content
            ), f"Missing Dockerfile requirement: {requirement}"

        # Check script.sh exists and is executable
        assert script_file.exists()

        # Check script has proper shebang and basic structure
        with open(script_file, "r") as f:
            script_content = f.read()

        script_requirements = ["#!/bin/bash", "set -e", "MCP_TRANSPORT"]

        for requirement in script_requirements:
            assert (
                requirement in script_content
            ), f"Missing script requirement: {requirement}"

    def test_template_origin_and_metadata(self, template_dir):
        """Test template metadata and origin information."""
        template_json = template_dir / "template.json"

        with open(template_json, "r") as f:
            config = json.load(f)

        # Test origin is marked as external since it extends korotovsky/slack-mcp-server
        assert config.get("origin") == "external"

        # Test author attribution
        assert "korotovsky/slack-mcp-server" in config["author"]

        # Test docker image naming
        assert config["docker_image"] == "dataeverything/mcp-slack"

        # Test tool discovery is dynamic
        assert config.get("tool_discovery") == "dynamic"

    def test_safety_and_security_features(self, template_dir):
        """Test that safety and security features are properly configured."""
        template_json = template_dir / "template.json"

        with open(template_json, "r") as f:
            config = json.load(f)

        properties = config["config_schema"]["properties"]

        # Message posting should be disabled by default
        assert "slack_mcp_add_message_tool" in properties
        posting_config = properties["slack_mcp_add_message_tool"]
        assert (
            "default" not in posting_config
        ), "Message posting should be disabled by default (no default)"

        # Security features should be available
        security_fields = ["slack_mcp_custom_tls", "slack_mcp_server_ca_insecure"]
        for field in security_fields:
            if field in properties:
                assert (
                    properties[field]["default"] is False
                ), f"{field} should default to False for security"

        # Sensitive tokens should be marked
        sensitive_fields = [
            "slack_mcp_xoxc_token",
            "slack_mcp_xoxd_token",
            "slack_mcp_xoxp_token",
            "slack_mcp_sse_api_key",
        ]
        for field in sensitive_fields:
            if field in properties:
                assert properties[field].get("sensitive", False) is True
