#!/usr/bin/env python3
"""
Configuration tests for Elasticsearch MCP Server

Tests for configuration parsing and validation.
"""

import pytest
import json
import os
import sys

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(__file__)))


class TestElasticsearchConfig:
    """Test configuration handling for Elasticsearch MCP Server."""

    def test_template_json_structure(self):
        """Test that template.json has correct structure."""
        template_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 
            "template.json"
        )
        
        with open(template_path, 'r') as f:
            template_data = json.load(f)
        
        # Check required fields
        assert "name" in template_data
        assert "description" in template_data
        assert "version" in template_data
        assert "config_schema" in template_data
        
        # Check Elasticsearch-specific fields
        assert template_data["name"] == "Elasticsearch"
        assert template_data["experimental"] == True
        assert "elasticsearch" in template_data["tags"]
        assert template_data["docker_image"] == "docker.elastic.co/mcp/elasticsearch"
        assert template_data["docker_tag"] == "0.4.5"

    def test_config_schema_validation(self):
        """Test configuration schema validation."""
        template_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 
            "template.json"
        )
        
        with open(template_path, 'r') as f:
            template_data = json.load(f)
        
        schema = template_data["config_schema"]
        properties = schema["properties"]
        
        # Check required environment variable mappings
        assert properties["es_url"]["env_mapping"] == "ES_URL"
        assert properties["es_api_key"]["env_mapping"] == "ES_API_KEY"
        assert properties["es_username"]["env_mapping"] == "ES_USERNAME"
        assert properties["es_password"]["env_mapping"] == "ES_PASSWORD"
        assert properties["es_ssl_skip_verify"]["env_mapping"] == "ES_SSL_SKIP_VERIFY"
        
        # Check sensitive fields are marked
        assert properties["es_api_key"]["sensitive"] == True
        assert properties["es_password"]["sensitive"] == True
        
        # Check required fields
        assert "es_url" in schema["required"]

    def test_authentication_requirements(self):
        """Test authentication requirement validation."""
        template_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 
            "template.json"
        )
        
        with open(template_path, 'r') as f:
            template_data = json.load(f)
        
        schema = template_data["config_schema"]
        
        # Check oneOf requirement for authentication
        assert "oneOf" in schema
        one_of = schema["oneOf"]
        
        # Should require either API key or username/password
        api_key_option = next((opt for opt in one_of if "es_api_key" in opt["required"]), None)
        basic_auth_option = next((opt for opt in one_of if "es_username" in opt["required"]), None)
        
        assert api_key_option is not None
        assert basic_auth_option is not None
        assert "es_password" in basic_auth_option["required"]

    def test_default_values(self):
        """Test default configuration values."""
        template_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 
            "template.json"
        )
        
        with open(template_path, 'r') as f:
            template_data = json.load(f)
        
        properties = template_data["config_schema"]["properties"]
        
        # Check default values
        assert properties["es_ssl_skip_verify"]["default"] == False
        assert properties["log_level"]["default"] == "INFO"
        assert properties["mcp_transport"]["default"] == "stdio"
        assert properties["mcp_port"]["default"] == 8080

    def test_transport_configuration(self):
        """Test transport configuration."""
        template_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 
            "template.json"
        )
        
        with open(template_path, 'r') as f:
            template_data = json.load(f)
        
        transport = template_data["transport"]
        
        assert transport["default"] == "stdio"
        assert "stdio" in transport["supported"]
        assert "http" in transport["supported"]

    def test_warning_messages(self):
        """Test that warning messages are present."""
        template_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 
            "template.json"
        )
        
        with open(template_path, 'r') as f:
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
            os.path.dirname(os.path.dirname(__file__)), 
            "tools.json"
        )
        
        with open(tools_path, 'r') as f:
            tools_data = json.load(f)
        
        # Should be a list of tools
        assert isinstance(tools_data, list)
        assert len(tools_data) == 5  # Expected 5 tools
        
        expected_tools = ["list_indices", "get_mappings", "search", "esql", "get_shards"]
        tool_names = [tool["name"] for tool in tools_data]
        
        for expected_tool in expected_tools:
            assert expected_tool in tool_names

    def test_tool_schemas(self):
        """Test tool input schemas."""
        tools_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 
            "tools.json"
        )
        
        with open(tools_path, 'r') as f:
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
            os.path.dirname(os.path.dirname(__file__)), 
            "template.json"
        )
        
        with open(template_path, 'r') as f:
            template_data = json.load(f)
        
        assert template_data["has_image"] == True
        assert template_data["origin"] == "external"
        assert template_data["docker_image"] == "docker.elastic.co/mcp/elasticsearch"
        assert template_data["docker_tag"] == "0.4.5"


if __name__ == "__main__":
    pytest.main([__file__])