"""
Integration tests for Trino MCP server implementation.

Tests end-to-end functionality, FastMCP integration, and real-world scenarios
for the new Python-based Trino MCP server.
"""

import json
import os
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock, Mock
import tempfile

# Import the server and config modules
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:
    from server import TrinoMCPServer, create_server, setup_health_check
    from config import TrinoServerConfig, create_trino_config
except ImportError:
    # Handle import in different environments
    import importlib.util
    
    server_path = os.path.join(os.path.dirname(__file__), "..", "server.py")
    spec = importlib.util.spec_from_file_location("server", server_path)
    server_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(server_module)
    TrinoMCPServer = server_module.TrinoMCPServer
    create_server = server_module.create_server
    setup_health_check = server_module.setup_health_check
    
    config_path = os.path.join(os.path.dirname(__file__), "..", "config.py")
    spec = importlib.util.spec_from_file_location("config", config_path)
    config_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(config_module)
    TrinoServerConfig = config_module.TrinoServerConfig
    create_trino_config = config_module.create_trino_config


class TestTrinoTemplateStructure:
    """Test Trino MCP server template structure and files."""

    @pytest.fixture
    def template_dir(self) -> Path:
        """Get Trino template directory."""
        return Path(__file__).parent.parent

    def test_template_structure(self, template_dir):
        """Test Trino template has required files and structure for Python implementation."""
        # Required files for Python implementation
        required_files = [
            "template.json", 
            "README.md", 
            "server.py",
            "config.py",
            "__init__.py",
            "requirements.txt",
            "Dockerfile"
        ]

        for file_path in required_files:
            assert (
                template_dir / file_path
            ).exists(), f"Missing required file: {file_path}"

        # Required directories
        required_dirs = ["tests", "docs"]

        for dir_path in required_dirs:
            assert (
                template_dir / dir_path
            ).is_dir(), f"Missing required directory: {dir_path}"

        # Check that old files are removed
        old_files = ["script.sh"]
        for old_file in old_files:
            assert not (template_dir / old_file).exists(), f"Old file should be removed: {old_file}"

    def test_template_json_validity(self, template_dir):
        """Test template.json is valid JSON with required fields for new implementation."""
        template_file = template_dir / "template.json"

        with open(template_file, "r") as f:
            template_data = json.load(f)

        # Required fields
        required_fields = [
            "id", "name", "description", "version", "author", "category",
            "tags", "docker_image", "docker_tag", "ports", "transport",
            "config_schema", "capabilities", "tools", "examples"
        ]

        for field in required_fields:
            assert field in template_data, f"Missing required field: {field}"

        # Verify Python implementation specifics
        assert template_data["docker_image"] == "dataeverything/mcp-trino"
        assert template_data["origin"] == "internal"
        assert "fastmcp" in template_data["tags"]
        assert "sqlalchemy" in template_data["tags"]
        assert template_data["transport"]["default"] == "http"
        assert template_data["transport"]["port"] == 7091
        assert "http" in template_data["transport"]["supported"]

    def test_requirements_file(self, template_dir):
        """Test requirements.txt contains necessary dependencies."""
        requirements_file = template_dir / "requirements.txt"
        
        with open(requirements_file, "r") as f:
            requirements = f.read()

        # Required dependencies for Python implementation
        required_deps = [
            "fastmcp",
            "sqlalchemy",
            "trino",
            "sqlparse",
            "starlette",
            "pydantic"
        ]

        for dep in required_deps:
            assert dep in requirements, f"Missing required dependency: {dep}"

    def test_dockerfile_structure(self, template_dir):
        """Test Dockerfile is configured for Python implementation."""
        dockerfile = template_dir / "Dockerfile"
        
        with open(dockerfile, "r") as f:
            content = f.read()

        # Should be Python-based
        assert "python:" in content
        assert "requirements.txt" in content
        assert "server" in content  # Should run server module
        assert "7091" in content  # Should expose correct port


class TestTrinoServerIntegration:
    """Test Trino MCP server integration and functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.test_config = {
            "trino_host": "localhost",
            "trino_user": "admin",
            "trino_port": 8080,
            "trino_catalog": "memory",
            "trino_schema": "default",
            "trino_max_results": 1000
        }

    @patch('server.create_engine')
    def test_server_creation_and_initialization(self, mock_create_engine):
        """Test server creation with proper initialization."""
        # Mock the engine
        mock_engine = Mock()
        mock_conn = Mock()
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=None)
        mock_conn.execute.return_value.fetchone.return_value = [1]
        mock_engine.connect.return_value = mock_conn
        mock_create_engine.return_value = mock_engine
        
        server = create_server(self.test_config)
        
        assert isinstance(server, TrinoMCPServer)
        assert server.engine is not None
        assert hasattr(server, 'mcp')
        assert hasattr(server, 'config')

    @patch('server.create_engine')
    def test_fastmcp_integration(self, mock_create_engine):
        """Test FastMCP integration and tool registration."""
        # Mock the engine
        mock_engine = Mock()
        mock_conn = Mock()
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=None)
        mock_conn.execute.return_value.fetchone.return_value = [1]
        mock_engine.connect.return_value = mock_conn
        mock_create_engine.return_value = mock_engine
        
        server = TrinoMCPServer(config_dict=self.test_config, skip_validation=True)
        
        # Verify FastMCP instance
        assert hasattr(server, 'mcp')
        assert server.mcp.name  # Should have a name
        
        # Verify tools are registered
        expected_tools = [
            "list_catalogs", "list_schemas", "list_tables", "describe_table",
            "execute_query", "get_query_status", "cancel_query", "get_cluster_info"
        ]
        
        for tool_name in expected_tools:
            assert hasattr(server, tool_name)

    @patch('server.create_engine')
    def test_authentication_configuration(self, mock_create_engine):
        """Test authentication configuration scenarios."""
        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine
        
        # Test basic authentication
        basic_config = {
            **self.test_config,
            "trino_password": "secret123"
        }
        
        server = TrinoMCPServer(config_dict=basic_config, skip_validation=True)
        conn_config = server.config.get_connection_config()
        
        assert "password" in conn_config
        
        # Test OAuth configuration
        oauth_config = {
            **self.test_config,
            "oauth_enabled": True,
            "oauth_provider": "google",
            "oidc_issuer": "https://accounts.google.com",
            "oidc_client_id": "client123"
        }
        
        oauth_server = TrinoMCPServer(config_dict=oauth_config, skip_validation=True)
        oauth_conn_config = oauth_server.config.get_connection_config()
        
        assert "auth" in oauth_conn_config

    @patch('server.create_engine')
    def test_read_only_mode_enforcement(self, mock_create_engine):
        """Test read-only mode enforcement in integration scenario."""
        mock_engine = Mock()
        mock_conn = Mock()
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=None)
        mock_create_engine.return_value = mock_engine
        
        # Test read-only mode (default)
        server = TrinoMCPServer(config_dict=self.test_config, skip_validation=True)
        
        # Should block write operations
        write_queries = [
            "INSERT INTO table VALUES (1)",
            "UPDATE table SET col = 'val'",
            "DELETE FROM table",
            "CREATE TABLE test (id int)",
            "DROP TABLE test"
        ]
        
        for query in write_queries:
            result = server.execute_query(query)
            assert result["success"] is False
            assert "Write operations are not allowed" in result["error"]

    @patch('server.create_engine')
    def test_write_mode_with_warning(self, mock_create_engine):
        """Test write mode enablement with warning."""
        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine
        
        write_config = {
            **self.test_config,
            "trino_allow_write_queries": True
        }
        
        with patch('builtins.print') as mock_print:
            server = TrinoMCPServer(config_dict=write_config, skip_validation=True)
            
            # Should have printed warning
            mock_print.assert_called()
            warning_calls = [str(call) for call in mock_print.call_args_list]
            warning_text = " ".join(warning_calls)
            assert "WARNING" in warning_text
            assert "write mode" in warning_text

    @patch('server.create_engine')
    def test_query_limits_enforcement(self, mock_create_engine):
        """Test query limits are properly enforced."""
        mock_engine = Mock()
        mock_conn = Mock()
        mock_result = Mock()
        
        # Create mock data with more rows than limit
        mock_rows = [Mock(_mapping={"id": i}) for i in range(10)]
        mock_result.__iter__ = Mock(return_value=iter(mock_rows))
        
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=None)
        mock_conn.execute.return_value = mock_result
        mock_engine.connect.return_value = mock_conn
        mock_create_engine.return_value = mock_engine
        
        # Set small limit for testing
        limited_config = {
            **self.test_config,
            "trino_max_results": 3
        }
        
        server = TrinoMCPServer(config_dict=limited_config, skip_validation=True)
        result = server.execute_query("SELECT * FROM large_table")
        
        # Should limit results
        assert result["max_results"] == 3

    @patch('server.create_engine')
    def test_health_check_setup(self, mock_create_engine):
        """Test health check endpoint setup."""
        mock_engine = Mock()
        mock_conn = Mock()
        mock_conn.__enter__ = Mock(return_value=mock_conn)
        mock_conn.__exit__ = Mock(return_value=None)
        mock_conn.execute.return_value.fetchone.return_value = [1]
        mock_engine.connect.return_value = mock_conn
        mock_create_engine.return_value = mock_engine
        
        server = TrinoMCPServer(config_dict=self.test_config, skip_validation=True)
        
        # Should be able to set up health check without errors
        setup_health_check(server)
        
        # Verify health check can be called
        assert hasattr(server.mcp, 'custom_route')

    @patch.dict(os.environ, {
        "TRINO_HOST": "env-host",
        "TRINO_USER": "env-user",
        "TRINO_PORT": "9090",
        "TRINO_MAX_RESULTS": "5000"
    })
    @patch('server.create_engine')
    def test_environment_variable_integration(self, mock_create_engine):
        """Test environment variable integration."""
        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine
        
        # Create server without explicit config (should use env vars)
        server = TrinoMCPServer(skip_validation=True)
        
        config_data = server.config_data
        assert config_data["trino_host"] == "env-host"
        assert config_data["trino_user"] == "env-user"
        assert config_data["trino_port"] == 9090
        assert config_data["trino_max_results"] == 5000

    @patch('server.create_engine')
    def test_configuration_validation_integration(self, mock_create_engine):
        """Test configuration validation in integration context."""
        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine
        
        # Invalid configurations should raise errors
        invalid_configs = [
            {},  # Missing required fields
            {"trino_host": "localhost"},  # Missing user
            {"trino_user": "admin"},  # Missing host
            {
                "trino_host": "localhost",
                "trino_user": "admin", 
                "trino_port": 70000  # Invalid port
            }
        ]
        
        for invalid_config in invalid_configs:
            with pytest.raises((ValueError, Exception)):
                TrinoMCPServer(config_dict=invalid_config)

    @patch('server.create_engine')
    def test_sqlalchemy_trino_integration(self, mock_create_engine):
        """Test SQLAlchemy-Trino integration setup."""
        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine
        
        server = TrinoMCPServer(config_dict=self.test_config, skip_validation=True)
        
        # Verify create_engine was called with Trino URL
        mock_create_engine.assert_called_once()
        call_args = mock_create_engine.call_args
        
        # Should be called with trino:// URL
        assert "trino://" in call_args[0][0]
        
        # Should have connect_args for Trino-specific settings
        assert "connect_args" in call_args[1]
        connect_args = call_args[1]["connect_args"]
        assert "http_scheme" in connect_args
        assert "verify" in connect_args

    def test_template_examples_accuracy(self):
        """Test that template examples are accurate for the implementation."""
        template_path = os.path.join(os.path.dirname(__file__), "..", "template.json")
        
        with open(template_path, "r") as f:
            template_data = json.load(f)
        
        examples = template_data["examples"]
        
        # HTTP endpoint should use correct port
        assert "7091" in examples["http_endpoint"]
        
        # CLI usage examples should be realistic
        cli_examples = examples["cli_usage"]
        assert len(cli_examples) >= 3
        
        # Should include basic authentication example
        basic_example = next((ex for ex in cli_examples if "trino_password" in ex), None)
        assert basic_example is not None
        
        # Should include OAuth example
        oauth_example = next((ex for ex in cli_examples if "oauth_enabled=true" in ex), None)
        assert oauth_example is not None
        
        # Client integration examples should work
        client_integration = examples["client_integration"]
        assert "fastmcp" in client_integration
        assert "curl" in client_integration
        assert "7091" in client_integration["curl"]

    @patch('server.create_engine')
    def test_error_recovery_and_resilience(self, mock_create_engine):
        """Test error recovery and resilience features."""
        # Test engine creation failure
        mock_create_engine.side_effect = Exception("Connection failed")
        
        # Should handle gracefully with skip_validation
        server = TrinoMCPServer(config_dict=self.test_config, skip_validation=True)
        assert server is not None
        
        # Should fail with validation enabled
        with pytest.raises(Exception):
            TrinoMCPServer(config_dict=self.test_config, skip_validation=False)

    @patch('server.create_engine')
    def test_logging_configuration(self, mock_create_engine):
        """Test logging configuration integration."""
        mock_engine = Mock()
        mock_create_engine.return_value = mock_engine
        
        log_config = {
            **self.test_config,
            "log_level": "debug"
        }
        
        with patch('logging.basicConfig') as mock_logging:
            server = TrinoMCPServer(config_dict=log_config, skip_validation=True)
            
            # Should have configured logging
            mock_logging.assert_called()
            
            # Should have set debug level
            assert server.config.get_template_config()["log_level"] == "debug"
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
