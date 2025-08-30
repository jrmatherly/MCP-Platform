"""
Tests for Slack MCP server configuration and validation.

These tests verify configuration schema validation and environment variable handling.
"""

import json
import pytest
from pathlib import Path


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
            assert "description" in prop_config, f"Property {prop_name} missing description"

    def test_authentication_config_options(self, template_config):
        """Test authentication configuration options."""
        properties = template_config["config_schema"]["properties"]
        
        # OAuth authentication options
        oauth_props = ["slack_token", "slack_user_token", "slack_app_token"]
        for prop in oauth_props:
            assert prop in properties, f"Missing OAuth property: {prop}"
            prop_config = properties[prop]
            assert prop_config["type"] == "string"
            assert prop_config.get("sensitive", False), f"OAuth property {prop} should be sensitive"
            assert "env_mapping" in prop_config

        # Stealth mode authentication options
        stealth_props = ["slack_cookie", "slack_workspace", "stealth_mode"]
        for prop in stealth_props:
            assert prop in properties, f"Missing stealth mode property: {prop}"

    def test_environment_variable_mappings(self, template_config):
        """Test environment variable mappings are consistent."""
        properties = template_config["config_schema"]["properties"]
        
        expected_mappings = {
            "slack_token": "SLACK_TOKEN",
            "slack_user_token": "SLACK_USER_TOKEN", 
            "slack_app_token": "SLACK_APP_TOKEN",
            "slack_cookie": "SLACK_COOKIE",
            "slack_workspace": "SLACK_WORKSPACE",
            "stealth_mode": "STEALTH_MODE",
            "enable_message_posting": "ENABLE_MESSAGE_POSTING",
            "allowed_channels": "ALLOWED_CHANNELS",
            "cache_enabled": "CACHE_ENABLED",
            "cache_ttl": "CACHE_TTL",
            "read_only_mode": "READ_ONLY_MODE",
            "log_level": "LOG_LEVEL",
            "mcp_transport": "MCP_TRANSPORT",
            "mcp_port": "MCP_PORT"
        }
        
        for prop_name, expected_env in expected_mappings.items():
            if prop_name in properties:
                prop_config = properties[prop_name]
                assert "env_mapping" in prop_config, f"Missing env_mapping for {prop_name}"
                assert prop_config["env_mapping"] == expected_env, \
                    f"Incorrect env_mapping for {prop_name}: expected {expected_env}, got {prop_config['env_mapping']}"

    def test_safety_configuration_defaults(self, template_config):
        """Test that safety-related configurations have secure defaults."""
        properties = template_config["config_schema"]["properties"]
        
        # Message posting should be disabled by default
        posting_config = properties["enable_message_posting"]
        assert posting_config["default"] == False, "Message posting should be disabled by default"
        
        # Read-only mode should be available with safe default
        readonly_config = properties["read_only_mode"]
        assert readonly_config["default"] == False, "Read-only mode default should be explicit"
        
        # Stealth mode should be disabled by default
        stealth_config = properties["stealth_mode"]
        assert stealth_config["default"] == False, "Stealth mode should be disabled by default"

    def test_performance_configuration_defaults(self, template_config):
        """Test performance-related configuration defaults."""
        properties = template_config["config_schema"]["properties"]
        
        # Caching should be enabled by default
        cache_config = properties["cache_enabled"]
        assert cache_config["default"] == True, "Caching should be enabled by default"
        
        # Cache TTL should have reasonable default
        ttl_config = properties["cache_ttl"]
        assert ttl_config["default"] == 3600, "Cache TTL should have 1 hour default"
        
        # History limit should have reasonable default
        history_config = properties["max_history_limit"]
        assert history_config["default"] == "30d", "History limit should default to 30 days"

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
        
        # MCP port config should match
        properties = template_config["config_schema"]["properties"]
        mcp_port_config = properties["mcp_port"]
        assert mcp_port_config["default"] == 3003

    def test_sensitive_data_marking(self, template_config):
        """Test that sensitive configuration is properly marked."""
        properties = template_config["config_schema"]["properties"]
        
        sensitive_props = [
            "slack_token",
            "slack_user_token", 
            "slack_app_token",
            "slack_cookie"
        ]
        
        for prop in sensitive_props:
            prop_config = properties[prop]
            assert prop_config.get("sensitive", False), f"Property {prop} should be marked as sensitive"

    def test_enum_configurations(self, template_config):
        """Test enumerated configuration options."""
        properties = template_config["config_schema"]["properties"]
        
        # Log level should have enum values
        log_level_config = properties["log_level"]
        assert "enum" in log_level_config
        expected_levels = ["DEBUG", "INFO", "WARNING", "ERROR"]
        for level in expected_levels:
            assert level in log_level_config["enum"]
        
        # MCP transport should have enum values
        transport_config = properties["mcp_transport"]
        assert "enum" in transport_config
        expected_transports = ["stdio", "sse"]
        for transport in expected_transports:
            assert transport in transport_config["enum"]

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
        
        proxy_props = ["http_proxy", "https_proxy"]
        for prop in proxy_props:
            assert prop in properties, f"Missing proxy property: {prop}"
            prop_config = properties[prop]
            assert prop_config["type"] == "string"
            assert "env_mapping" in prop_config

    def test_boolean_type_configurations(self, template_config):
        """Test boolean configuration properties."""
        properties = template_config["config_schema"]["properties"]
        
        boolean_props = {
            "stealth_mode": False,
            "enable_message_posting": False,
            "cache_enabled": True,
            "read_only_mode": False,
            "embed_user_info": True
        }
        
        for prop, expected_default in boolean_props.items():
            prop_config = properties[prop]
            assert prop_config["type"] == "boolean", f"Property {prop} should be boolean type"
            assert prop_config["default"] == expected_default, \
                f"Property {prop} has wrong default: expected {expected_default}, got {prop_config['default']}"

    def test_integer_type_configurations(self, template_config):
        """Test integer configuration properties."""
        properties = template_config["config_schema"]["properties"]
        
        integer_props = ["mcp_port", "cache_ttl"]
        for prop in integer_props:
            prop_config = properties[prop]
            assert prop_config["type"] == "integer", f"Property {prop} should be integer type"
            assert isinstance(prop_config["default"], int), f"Property {prop} should have integer default"

    def test_string_type_configurations(self, template_config):
        """Test string configuration properties."""
        properties = template_config["config_schema"]["properties"]
        
        string_props = [
            "slack_token", "slack_user_token", "slack_app_token",
            "slack_cookie", "slack_workspace", "allowed_channels",
            "max_history_limit", "http_proxy", "https_proxy",
            "log_level", "mcp_transport"
        ]
        
        for prop in string_props:
            prop_config = properties[prop]
            assert prop_config["type"] == "string", f"Property {prop} should be string type"

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
            "log_level", "mcp_transport", "mcp_port",
            "slack_token", "slack_user_token", "slack_app_token"
        ]
        
        for prop in titled_props:
            if prop in properties:
                prop_config = properties[prop]
                assert "title" in prop_config, f"Property {prop} should have a title"
                assert len(prop_config["title"]) > 0, f"Property {prop} title should not be empty"
        
        # All properties should have descriptions
        for prop_name, prop_config in properties.items():
            assert "description" in prop_config, f"Property {prop_name} missing description"
            assert len(prop_config["description"]) > 10, f"Property {prop_name} description too short"

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
        
        # Docker image should be correct
        assert template_config["docker_image"] == "dataeverything/mcp-slack"
        
        # Origin should be external (extends external project)
        assert template_config.get("origin") == "external"
        
        # Tool discovery should be dynamic
        assert template_config.get("tool_discovery") == "dynamic"