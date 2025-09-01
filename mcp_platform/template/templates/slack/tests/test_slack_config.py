"""
Tests for Slack MCP server configuration and validation.

These tests verify configuration schema validation and environment variable handling.
"""

import json
from pathlib import Path

import pytest


class TestSlackConfig:
    """Test Slack MCP server configuration and validation."""

    @pytest.fixture
    def template_config(self) -> dict:
        """Load template configuration."""
        template_dir = Path(__file__).parent.parent
        template_json = template_dir / "template.json"

        with open(template_json, "r") as f:
            return json.load(f)

    def test_config_schema_validity(self, template_config):
        """Test configuration schema is valid JSON Schema."""
        config_schema = template_config["config_schema"]

        # Basic schema structure
        assert config_schema["type"] == "object"
        assert "properties" in config_schema

        properties = config_schema["properties"]

        # Test that all properties have required fields
        for prop_name, prop_config in properties.items():
            assert "type" in prop_config, f"Property {prop_name} missing type"
            assert (
                "description" in prop_config
            ), f"Property {prop_name} missing description"

    def test_authentication_config_options(self, template_config):
        """Test authentication configuration options."""
        properties = template_config["config_schema"]["properties"]

        # OAuth authentication options using korotovsky naming
        oauth_props = [
            "slack_mcp_xoxc_token",
            "slack_mcp_xoxd_token",
            "slack_mcp_xoxp_token",
        ]
        for prop in oauth_props:
            assert prop in properties, f"Missing OAuth property: {prop}"
            prop_config = properties[prop]
            assert prop_config["type"] == "string"
            assert prop_config.get(
                "sensitive", False
            ), f"OAuth property {prop} should be sensitive"
            assert "env_mapping" in prop_config

        # SSE authentication option
        if "slack_mcp_sse_api_key" in properties:
            sse_config = properties["slack_mcp_sse_api_key"]
            assert sse_config["type"] == "string"
            assert sse_config.get("sensitive", False), "SSE API key should be sensitive"

    def test_environment_variable_mappings(self, template_config):
        """Test environment variable mappings are consistent."""
        properties = template_config["config_schema"]["properties"]

        # Authentication tokens should be in the expected env mapping
        expected_mappings = {
            "slack_mcp_xoxc_token": "SLACK_MCP_XOXC_TOKEN",
            "slack_mcp_xoxd_token": "SLACK_MCP_XOXD_TOKEN",
            "slack_mcp_xoxp_token": "SLACK_MCP_XOXP_TOKEN",
            "slack_mcp_sse_api_key": "SLACK_MCP_SSE_API_KEY",
            "slack_mcp_proxy": "SLACK_MCP_PROXY",
            "slack_mcp_user_agent": "SLACK_MCP_USER_AGENT",
            "slack_mcp_add_message_tool": "SLACK_MCP_ADD_MESSAGE_TOOL",
            "slack_mcp_port": "SLACK_MCP_PORT",
            "slack_mcp_host": "SLACK_MCP_HOST",
            "slack_mcp_log_level": "SLACK_MCP_LOG_LEVEL",
            "slack_mcp_users_cache": "SLACK_MCP_USERS_CACHE",
            "slack_mcp_channels_cache": "SLACK_MCP_CHANNELS_CACHE",
        }

        for prop_name, expected_env in expected_mappings.items():
            if prop_name in properties:
                prop_config = properties[prop_name]
                assert (
                    "env_mapping" in prop_config
                ), f"Missing env_mapping for {prop_name}"
                assert (
                    prop_config["env_mapping"] == expected_env
                ), f"Incorrect env_mapping for {prop_name}: expected {expected_env}, got {prop_config['env_mapping']}"

    def test_safety_configuration_defaults(self, template_config):
        """Test that safety-related configurations have secure defaults."""
        properties = template_config["config_schema"]["properties"]

        # Message posting tool should not have a default (disabled by default)
        if "slack_mcp_add_message_tool" in properties:
            posting_config = properties["slack_mcp_add_message_tool"]
            assert (
                "default" not in posting_config
            ), "Message posting should be disabled by default (no default value)"

        # Custom TLS should be disabled by default
        if "slack_mcp_custom_tls" in properties:
            tls_config = properties["slack_mcp_custom_tls"]
            assert (
                tls_config["default"] is False
            ), "Custom TLS should be disabled by default"

        # Insecure CA should be disabled by default
        if "slack_mcp_server_ca_insecure" in properties:
            insecure_config = properties["slack_mcp_server_ca_insecure"]
            assert (
                insecure_config["default"] is False
            ), "Insecure CA should be disabled by default"

    def test_performance_configuration_defaults(self, template_config):
        """Test performance-related configuration defaults."""
        properties = template_config["config_schema"]["properties"]

        # Cache files should have reasonable defaults
        if "slack_mcp_users_cache" in properties:
            users_cache_config = properties["slack_mcp_users_cache"]
            assert (
                users_cache_config["default"] == ".users_cache.json"
            ), "Users cache should have default filename"

        if "slack_mcp_channels_cache" in properties:
            channels_cache_config = properties["slack_mcp_channels_cache"]
            assert (
                channels_cache_config["default"] == ".channels_cache_v2.json"
            ), "Channels cache should have default filename"

        # Port should have reasonable default
        if "slack_mcp_port" in properties:
            port_config = properties["slack_mcp_port"]
            assert port_config["default"] == 13080, "Port should default to 13080"

    def test_transport_configuration(self, template_config):
        """Test transport configuration is properly set up."""
        transport = template_config["transport"]

        # Default transport should be stdio
        assert transport["default"] == "stdio"

        # Should support stdio and sse
        supported = transport["supported"]
        assert "stdio" in supported
        assert "sse" in supported

        # Should have port configuration
        assert "port" in transport
        assert transport["port"] == 3003

        # Slack MCP port config should exist
        properties = template_config["config_schema"]["properties"]
        if "slack_mcp_port" in properties:
            slack_port_config = properties["slack_mcp_port"]
            assert slack_port_config["default"] == 13080

    def test_sensitive_data_marking(self, template_config):
        """Test that sensitive configuration is properly marked."""
        properties = template_config["config_schema"]["properties"]

        sensitive_props = [
            "slack_mcp_xoxc_token",
            "slack_mcp_xoxd_token",
            "slack_mcp_xoxp_token",
            "slack_mcp_sse_api_key",
        ]

        for prop in sensitive_props:
            prop_config = properties[prop]
            assert prop_config.get(
                "sensitive", False
            ), f"Property {prop} should be marked as sensitive"

    def test_enum_configurations(self, template_config):
        """Test enumerated configuration options."""
        properties = template_config["config_schema"]["properties"]

        # Log level should have enum values using korotovsky naming
        log_level_config = properties["slack_mcp_log_level"]
        assert "enum" in log_level_config
        expected_levels = ["debug", "info", "warn", "error", "panic", "fatal"]
        for level in expected_levels:
            assert level in log_level_config["enum"]

    def test_array_configurations(self, template_config):
        """Test array-type configurations with separators."""
        properties = template_config["config_schema"]["properties"]

        # Allowed channels should be string with comma separator
        if "allowed_channels" in properties:
            channels_config = properties["allowed_channels"]
            assert channels_config["type"] == "string"
            assert "env_separator" in channels_config
            assert channels_config["env_separator"] == ","

    def test_proxy_configuration(self, template_config):
        """Test proxy configuration options."""
        properties = template_config["config_schema"]["properties"]

        # Korotovsky uses single proxy setting
        if "slack_mcp_proxy" in properties:
            proxy_config = properties["slack_mcp_proxy"]
            assert proxy_config["type"] == "string"
            assert "env_mapping" in proxy_config

    def test_boolean_type_configurations(self, template_config):
        """Test boolean configuration properties."""
        properties = template_config["config_schema"]["properties"]

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
                    prop_config["type"] == "boolean"
                ), f"Property {prop} should be boolean type"
                assert (
                    prop_config["default"] == expected_default
                ), f"Property {prop} has wrong default: expected {expected_default}, got {prop_config['default']}"

    def test_integer_type_configurations(self, template_config):
        """Test integer configuration properties."""
        properties = template_config["config_schema"]["properties"]

        integer_props = ["slack_mcp_port"]
        for prop in integer_props:
            if prop in properties:
                prop_config = properties[prop]
                assert (
                    prop_config["type"] == "integer"
                ), f"Property {prop} should be integer type"
                assert isinstance(
                    prop_config["default"], int
                ), f"Property {prop} should have integer default"

    def test_string_type_configurations(self, template_config):
        """Test string configuration properties."""
        properties = template_config["config_schema"]["properties"]

        string_props = [
            "slack_mcp_xoxc_token",
            "slack_mcp_xoxd_token",
            "slack_mcp_xoxp_token",
            "slack_mcp_sse_api_key",
            "slack_mcp_proxy",
            "slack_mcp_user_agent",
            "slack_mcp_server_ca",
            "slack_mcp_add_message_tool",
            "slack_mcp_add_message_unfurling",
            "slack_mcp_users_cache",
            "slack_mcp_channels_cache",
            "slack_mcp_host",
            "slack_mcp_log_level",
        ]

        for prop in string_props:
            if prop in properties:
                prop_config = properties[prop]
                assert (
                    prop_config["type"] == "string"
                ), f"Property {prop} should be string type"

    def test_required_fields_configuration(self, template_config):
        """Test required fields configuration."""
        config_schema = template_config["config_schema"]

        # Should have required field (even if empty)
        assert "required" in config_schema

        # For Slack, no fields should be strictly required since we support multiple auth modes
        required_fields = config_schema["required"]
        assert isinstance(required_fields, list)
        # Should be empty or minimal since auth is flexible
        assert len(required_fields) == 0

    def test_title_and_description_completeness(self, template_config):
        """Test that all properties have proper titles and descriptions."""
        properties = template_config["config_schema"]["properties"]

        # Properties that should have titles
        titled_props = [
            "slack_mcp_log_level",
            "slack_mcp_port",
            "slack_mcp_host",
            "slack_mcp_xoxc_token",
            "slack_mcp_xoxd_token",
            "slack_mcp_xoxp_token",
        ]

        for prop in titled_props:
            if prop in properties:
                prop_config = properties[prop]
                assert "title" in prop_config, f"Property {prop} should have a title"
                assert (
                    len(prop_config["title"]) > 0
                ), f"Property {prop} title should not be empty"

        # All properties should have descriptions
        for prop_name, prop_config in properties.items():
            assert (
                "description" in prop_config
            ), f"Property {prop_name} missing description"
            assert (
                len(prop_config["description"]) > 10
            ), f"Property {prop_name} description too short"

    def test_docker_port_configuration(self, template_config):
        """Test Docker port configuration."""
        ports = template_config.get("ports", {})

        # Should expose port 3003
        assert "3003" in ports
        assert ports["3003"] == 3003

        # Should match transport port
        transport_port = template_config["transport"]["port"]
        assert transport_port == 3003

    def test_template_metadata_consistency(self, template_config):
        """Test template metadata is consistent."""
        # Category should be Communication
        assert template_config["category"] == "Communication"

        # Should have Slack-related tags
        tags = template_config["tags"]
        slack_tags = ["slack", "messaging", "communication"]
        for tag in slack_tags:
            assert tag in tags, f"Missing tag: {tag}"

        # Docker image should be for the template wrapper
        assert template_config["docker_image"] == "dataeverything/mcp-slack"

        # Origin should be external (extends external project)
        assert template_config.get("origin") == "external"

        # Tool discovery should be dynamic
        assert template_config.get("tool_discovery") == "dynamic"
