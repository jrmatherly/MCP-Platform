"""
Unit tests for the Enhanced CLI v2.
"""

import asyncio
import json
from unittest.mock import AsyncMock, Mock, patch

import pytest
from click.testing import CliRunner

from mcp_platform.gateway.auth import AuthManager
from mcp_platform.gateway.cli import (
    auth_group,
    cli,
    config,
    instances,
    stats,
    templates,
    users,
)
from mcp_platform.gateway.client import GatewayClient
from mcp_platform.gateway.database import DatabaseManager
from mcp_platform.gateway.models import (
    APIKey,
    ServerInstance,
    ServerStatus,
    ServerTemplate,
    User,
    UserRole,
)


class TestCLIConfiguration:
    """Test CLI configuration functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_config_init_command(self):
        """Test config init command."""
        with (
            patch("mcp_platform.gateway.cli.Path.exists", return_value=False),
            patch("builtins.open", create=True) as mock_open,
        ):

            result = self.runner.invoke(config, ["init"])

            assert result.exit_code == 0
            assert "Configuration initialized" in result.output
            mock_open.assert_called()

    def test_config_show_command(self):
        """Test config show command."""
        test_config = {
            "gateway_url": "http://localhost:8080",
            "api_key": "mcp_test_key",
            "timeout": 30,
        }

        with patch("mcp_platform.gateway.cli.load_config", return_value=test_config):
            result = self.runner.invoke(config, ["show"])

            assert result.exit_code == 0
            assert "gateway_url" in result.output
            assert "http://localhost:8080" in result.output

    def test_config_set_command(self):
        """Test config set command."""
        with (
            patch("mcp_platform.gateway.cli.load_config", return_value={}),
            patch("mcp_platform.gateway.cli.save_config") as mock_save,
        ):

            result = self.runner.invoke(
                config, ["set", "gateway_url", "https://new-gateway.com"]
            )

            assert result.exit_code == 0
            assert "Configuration updated" in result.output
            mock_save.assert_called_once()

    def test_config_get_command(self):
        """Test config get command."""
        test_config = {"gateway_url": "http://localhost:8080"}

        with patch("mcp_platform.gateway.cli.load_config", return_value=test_config):
            result = self.runner.invoke(config, ["get", "gateway_url"])

            assert result.exit_code == 0
            assert "http://localhost:8080" in result.output

    def test_config_get_nonexistent_key(self):
        """Test config get with nonexistent key."""
        with patch("mcp_platform.gateway.cli.load_config", return_value={}):
            result = self.runner.invoke(config, ["get", "nonexistent"])

            assert result.exit_code == 1
            assert "not found" in result.output


class TestTemplateCommands:
    """Test template management commands."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch("mcp_platform.gateway.cli.create_gateway_client")
    async def test_template_list_command(self, mock_create_client):
        """Test template list command."""
        # Mock client
        mock_client = Mock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.list_templates = AsyncMock(
            return_value=[
                {"name": "demo", "description": "Demo template"},
                {"name": "filesystem", "description": "File system template"},
            ]
        )
        mock_create_client.return_value = mock_client

        result = self.runner.invoke(templates, ["list"])

        assert result.exit_code == 0
        assert "demo" in result.output
        assert "filesystem" in result.output

    @patch("mcp_platform.gateway.cli.create_gateway_client")
    async def test_template_show_command(self, mock_create_client):
        """Test template show command."""
        mock_client = Mock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get_template = AsyncMock(
            return_value={
                "name": "demo",
                "description": "Demo template",
                "command": ["python", "-m", "demo"],
                "category": "demo",
            }
        )
        mock_create_client.return_value = mock_client

        result = self.runner.invoke(templates, ["show", "demo"])

        assert result.exit_code == 0
        assert "Demo template" in result.output

    @patch("mcp_platform.gateway.cli.create_gateway_client")
    async def test_template_register_command(self, mock_create_client):
        """Test template register command."""
        mock_client = Mock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.register_template = AsyncMock()
        mock_create_client.return_value = mock_client

        # Test with JSON file
        template_data = {
            "name": "new_template",
            "command": ["python", "-m", "new_server"],
            "args": [],
            "env": {},
            "description": "New template",
        }

        with patch("builtins.open", create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = (
                json.dumps(template_data)
            )

            result = self.runner.invoke(
                templates, ["register", "/path/to/template.json"]
            )

            assert result.exit_code == 0
            assert "Template registered successfully" in result.output

    @patch("mcp_platform.gateway.cli.create_gateway_client")
    async def test_template_delete_command(self, mock_create_client):
        """Test template delete command."""
        mock_client = Mock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.delete_template = AsyncMock()
        mock_create_client.return_value = mock_client

        result = self.runner.invoke(templates, ["delete", "demo", "--confirm"])

        assert result.exit_code == 0
        assert "Template deleted successfully" in result.output

    def test_template_delete_without_confirm(self):
        """Test template delete without confirmation."""
        result = self.runner.invoke(templates, ["delete", "demo"])

        assert result.exit_code == 1
        assert "confirmation required" in result.output.lower()


class TestInstanceCommands:
    """Test instance management commands."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch("mcp_platform.gateway.cli.create_gateway_client")
    async def test_instance_list_command(self, mock_create_client):
        """Test instance list command."""
        mock_client = Mock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.list_instances = AsyncMock(
            return_value=[
                {
                    "id": "demo-1",
                    "template_name": "demo",
                    "port": 8080,
                    "status": "running",
                },
                {
                    "id": "demo-2",
                    "template_name": "demo",
                    "port": 8081,
                    "status": "stopped",
                },
            ]
        )
        mock_create_client.return_value = mock_client

        result = self.runner.invoke(instances, ["list"])

        assert result.exit_code == 0
        assert "demo-1" in result.output
        assert "running" in result.output

    @patch("mcp_platform.gateway.cli.create_gateway_client")
    async def test_instance_create_command(self, mock_create_client):
        """Test instance create command."""
        mock_client = Mock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.create_instance = AsyncMock(
            return_value={
                "id": "demo-3",
                "template_name": "demo",
                "port": 8082,
                "status": "created",
            }
        )
        mock_create_client.return_value = mock_client

        result = self.runner.invoke(instances, ["create", "demo"])

        assert result.exit_code == 0
        assert "Instance created successfully" in result.output
        assert "demo-3" in result.output

    @patch("mcp_platform.gateway.cli.create_gateway_client")
    async def test_instance_start_command(self, mock_create_client):
        """Test instance start command."""
        mock_client = Mock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.start_instance = AsyncMock()
        mock_create_client.return_value = mock_client

        result = self.runner.invoke(instances, ["start", "demo-1"])

        assert result.exit_code == 0
        assert "Instance started successfully" in result.output

    @patch("mcp_platform.gateway.cli.create_gateway_client")
    async def test_instance_stop_command(self, mock_create_client):
        """Test instance stop command."""
        mock_client = Mock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.stop_instance = AsyncMock()
        mock_create_client.return_value = mock_client

        result = self.runner.invoke(instances, ["stop", "demo-1"])

        assert result.exit_code == 0
        assert "Instance stopped successfully" in result.output

    @patch("mcp_platform.gateway.cli.create_gateway_client")
    async def test_instance_logs_command(self, mock_create_client):
        """Test instance logs command."""
        mock_client = Mock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get_instance_logs = AsyncMock(
            return_value=[
                "2024-01-01 10:00:00 - Server started",
                "2024-01-01 10:01:00 - Handling request",
            ]
        )
        mock_create_client.return_value = mock_client

        result = self.runner.invoke(instances, ["logs", "demo-1"])

        assert result.exit_code == 0
        assert "Server started" in result.output

    @patch("mcp_platform.gateway.cli.create_gateway_client")
    async def test_instance_delete_command(self, mock_create_client):
        """Test instance delete command."""
        mock_client = Mock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.delete_instance = AsyncMock()
        mock_create_client.return_value = mock_client

        result = self.runner.invoke(instances, ["delete", "demo-1", "--confirm"])

        assert result.exit_code == 0
        assert "Instance deleted successfully" in result.output


class TestUserCommands:
    """Test user management commands."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch("mcp_platform.gateway.cli.DatabaseManager")
    @patch("mcp_platform.gateway.cli.AuthManager")
    async def test_user_create_command(
        self, mock_auth_manager_class, mock_db_manager_class
    ):
        """Test user create command."""
        # Mock managers
        mock_auth_manager = Mock()
        mock_auth_manager.create_user = AsyncMock(
            return_value=User(
                id="user-1",
                username="newuser",
                email="new@example.com",
                role=UserRole.USER,
            )
        )
        mock_auth_manager_class.return_value = mock_auth_manager

        mock_db_manager = Mock()
        mock_db_manager.initialize = AsyncMock()
        mock_db_manager_class.return_value = mock_db_manager

        result = self.runner.invoke(
            users, ["create", "newuser", "new@example.com", "password123"]
        )

        assert result.exit_code == 0
        assert "User created successfully" in result.output

    @patch("mcp_platform.gateway.cli.DatabaseManager")
    @patch("mcp_platform.gateway.cli.AuthManager")
    async def test_user_list_command(
        self, mock_auth_manager_class, mock_db_manager_class
    ):
        """Test user list command."""
        mock_auth_manager = Mock()
        mock_auth_manager.list_users = AsyncMock(
            return_value=[
                User(
                    id="user-1",
                    username="user1",
                    email="user1@example.com",
                    role=UserRole.USER,
                ),
                User(
                    id="user-2",
                    username="admin1",
                    email="admin1@example.com",
                    role=UserRole.ADMIN,
                ),
            ]
        )
        mock_auth_manager_class.return_value = mock_auth_manager

        mock_db_manager = Mock()
        mock_db_manager.initialize = AsyncMock()
        mock_db_manager_class.return_value = mock_db_manager

        result = self.runner.invoke(users, ["list"])

        assert result.exit_code == 0
        assert "user1" in result.output
        assert "admin1" in result.output

    @patch("mcp_platform.gateway.cli.DatabaseManager")
    @patch("mcp_platform.gateway.cli.AuthManager")
    async def test_user_delete_command(
        self, mock_auth_manager_class, mock_db_manager_class
    ):
        """Test user delete command."""
        mock_auth_manager = Mock()
        mock_auth_manager.delete_user = AsyncMock()
        mock_auth_manager_class.return_value = mock_auth_manager

        mock_db_manager = Mock()
        mock_db_manager.initialize = AsyncMock()
        mock_db_manager_class.return_value = mock_db_manager

        result = self.runner.invoke(users, ["delete", "testuser", "--confirm"])

        assert result.exit_code == 0
        assert "User deleted successfully" in result.output


class TestAuthCommands:
    """Test authentication commands."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch("mcp_platform.gateway.cli.DatabaseManager")
    @patch("mcp_platform.gateway.cli.AuthManager")
    async def test_auth_create_api_key_command(
        self, mock_auth_manager_class, mock_db_manager_class
    ):
        """Test auth create-api-key command."""
        mock_auth_manager = Mock()
        mock_auth_manager.create_api_key = AsyncMock(
            return_value=APIKey(
                id="key-1",
                user_id="user-1",
                key_hash="hashed_key",
                name="test_key",
                scopes=["read", "write"],
            )
        )
        mock_auth_manager_class.return_value = mock_auth_manager

        mock_db_manager = Mock()
        mock_db_manager.initialize = AsyncMock()
        mock_db_manager_class.return_value = mock_db_manager

        result = self.runner.invoke(
            auth_group, ["create-api-key", "user-1", "test_key"]
        )

        assert result.exit_code == 0
        assert "API key created successfully" in result.output

    @patch("mcp_platform.gateway.cli.DatabaseManager")
    @patch("mcp_platform.gateway.cli.AuthManager")
    async def test_auth_list_api_keys_command(
        self, mock_auth_manager_class, mock_db_manager_class
    ):
        """Test auth list-api-keys command."""
        mock_auth_manager = Mock()
        mock_auth_manager.list_api_keys = AsyncMock(
            return_value=[
                APIKey(
                    id="key-1",
                    user_id="user-1",
                    key_hash="hash1",
                    name="key1",
                    scopes=["read"],
                ),
                APIKey(
                    id="key-2",
                    user_id="user-1",
                    key_hash="hash2",
                    name="key2",
                    scopes=["read", "write"],
                ),
            ]
        )
        mock_auth_manager_class.return_value = mock_auth_manager

        mock_db_manager = Mock()
        mock_db_manager.initialize = AsyncMock()
        mock_db_manager_class.return_value = mock_db_manager

        result = self.runner.invoke(auth_group, ["list-api-keys", "user-1"])

        assert result.exit_code == 0
        assert "key1" in result.output
        assert "key2" in result.output

    @patch("mcp_platform.gateway.cli.DatabaseManager")
    @patch("mcp_platform.gateway.cli.AuthManager")
    async def test_auth_revoke_api_key_command(
        self, mock_auth_manager_class, mock_db_manager_class
    ):
        """Test auth revoke-api-key command."""
        mock_auth_manager = Mock()
        mock_auth_manager.revoke_api_key = AsyncMock()
        mock_auth_manager_class.return_value = mock_auth_manager

        mock_db_manager = Mock()
        mock_db_manager.initialize = AsyncMock()
        mock_db_manager_class.return_value = mock_db_manager

        result = self.runner.invoke(
            auth_group, ["revoke-api-key", "key-1", "--confirm"]
        )

        assert result.exit_code == 0
        assert "API key revoked successfully" in result.output


class TestStatsCommand:
    """Test stats command."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch("mcp_platform.gateway.cli.create_gateway_client")
    async def test_stats_command(self, mock_create_client):
        """Test stats command."""
        mock_client = Mock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get_stats = AsyncMock(
            return_value={
                "total_requests": 1000,
                "active_connections": 25,
                "templates": {"demo": {"total_instances": 3, "healthy_instances": 2}},
                "load_balancer": {
                    "requests_per_instance": {"demo-1": 500, "demo-2": 300}
                },
                "health_checker": {"running": True},
            }
        )
        mock_create_client.return_value = mock_client

        result = self.runner.invoke(stats)

        assert result.exit_code == 0
        assert "1000" in result.output  # total_requests
        assert "25" in result.output  # active_connections
        assert "demo" in result.output

    @patch("mcp_platform.gateway.cli.create_gateway_client")
    async def test_stats_command_json_format(self, mock_create_client):
        """Test stats command with JSON format."""
        mock_client = Mock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.get_stats = AsyncMock(
            return_value={"total_requests": 1000, "active_connections": 25}
        )
        mock_create_client.return_value = mock_client

        result = self.runner.invoke(stats, ["--format", "json"])

        assert result.exit_code == 0
        # Should be valid JSON
        data = json.loads(result.output)
        assert data["total_requests"] == 1000


class TestInteractiveCLI:
    """Test interactive CLI functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_interactive_mode_entry(self):
        """Test entering interactive mode."""
        with patch(
            "mcp_platform.gateway.cli.start_interactive_mode"
        ) as mock_interactive:
            result = self.runner.invoke(cli, ["--interactive"])

            assert result.exit_code == 0
            mock_interactive.assert_called_once()

    @patch("mcp_platform.gateway.cli.create_gateway_client")
    async def test_interactive_command_execution(self, mock_create_client):
        """Test command execution in interactive mode."""
        mock_client = Mock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client.list_templates = AsyncMock(return_value=[])
        mock_create_client.return_value = mock_client

        # Test interactive command execution
        with patch("builtins.input", side_effect=["templates list", "quit"]):
            result = self.runner.invoke(cli, ["--interactive"])

            # Should handle commands in interactive mode
            assert result.exit_code == 0


class TestErrorHandling:
    """Test CLI error handling."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    @patch("mcp_platform.gateway.cli.create_gateway_client")
    async def test_network_error_handling(self, mock_create_client):
        """Test handling of network errors."""
        # Mock client that raises network error
        mock_create_client.side_effect = Exception("Connection failed")

        result = self.runner.invoke(templates, ["list"])

        assert result.exit_code == 1
        assert "Error" in result.output

    def test_config_file_not_found(self):
        """Test handling when config file doesn't exist."""
        with patch(
            "mcp_platform.gateway.cli.load_config", side_effect=FileNotFoundError()
        ):
            result = self.runner.invoke(config, ["show"])

            assert result.exit_code == 1
            assert "Configuration file not found" in result.output

    def test_invalid_json_template_file(self):
        """Test handling of invalid JSON template file."""
        with patch("builtins.open", create=True) as mock_open:
            mock_open.return_value.__enter__.return_value.read.return_value = (
                "invalid json"
            )

            result = self.runner.invoke(
                templates, ["register", "/path/to/invalid.json"]
            )

            assert result.exit_code == 1
            assert "Invalid JSON" in result.output


class TestConfigHelpers:
    """Test configuration helper functions."""

    def test_load_config_success(self):
        """Test successful config loading."""
        test_config = {"gateway_url": "http://localhost:8080"}

        with (
            patch("pathlib.Path.exists", return_value=True),
            patch("builtins.open", create=True) as mock_open,
        ):
            mock_open.return_value.__enter__.return_value.read.return_value = (
                json.dumps(test_config)
            )

            from mcp_platform.gateway.cli import load_config

            config = load_config()

            assert config == test_config

    def test_save_config_success(self):
        """Test successful config saving."""
        test_config = {"gateway_url": "http://localhost:8080"}

        with patch("builtins.open", create=True) as mock_open:
            from mcp_platform.gateway.cli import save_config

            save_config(test_config)

            mock_open.assert_called()
            mock_file = mock_open.return_value.__enter__.return_value
            mock_file.write.assert_called_once()

    def test_get_config_value(self):
        """Test getting configuration values."""
        test_config = {"gateway_url": "http://localhost:8080", "timeout": 30}

        from mcp_platform.gateway.cli import get_config_value

        assert get_config_value(test_config, "gateway_url") == "http://localhost:8080"
        assert get_config_value(test_config, "timeout") == 30
        assert get_config_value(test_config, "nonexistent") is None
        assert get_config_value(test_config, "nonexistent", "default") == "default"


class TestOutputFormatting:
    """Test output formatting functions."""

    def test_format_table_output(self):
        """Test table output formatting."""
        data = [
            {"name": "template1", "status": "active"},
            {"name": "template2", "status": "inactive"},
        ]

        from mcp_platform.gateway.cli import format_table

        output = format_table(data, ["name", "status"])

        assert "template1" in output
        assert "active" in output
        assert "template2" in output

    def test_format_json_output(self):
        """Test JSON output formatting."""
        data = {"key": "value", "number": 42}

        from mcp_platform.gateway.cli import format_json

        output = format_json(data)

        # Should be valid JSON
        parsed = json.loads(output)
        assert parsed == data

    def test_format_status_indicators(self):
        """Test status indicator formatting."""
        from mcp_platform.gateway.cli import format_status

        assert "✓" in format_status("running")
        assert "✗" in format_status("stopped")
        assert "⚠" in format_status("unhealthy")


class TestAsyncCommandHandling:
    """Test async command handling."""

    def test_async_command_wrapper(self):
        """Test async command wrapper functionality."""
        from mcp_platform.gateway.cli import async_command

        @async_command
        async def test_async_func():
            await asyncio.sleep(0.01)
            return "success"

        # Should be able to call sync
        result = test_async_func()
        assert result == "success"

    def test_async_error_handling(self):
        """Test async error handling in commands."""
        from mcp_platform.gateway.cli import async_command

        @async_command
        async def test_failing_func():
            raise Exception("Test error")

        # Should handle exceptions properly
        with pytest.raises(Exception, match="Test error"):
            test_failing_func()


class TestCLIIntegration:
    """Test CLI integration scenarios."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_full_workflow_simulation(self):
        """Test a full workflow simulation."""
        # This would test a complete workflow:
        # 1. Initialize config
        # 2. Register template
        # 3. Create instance
        # 4. Start instance
        # 5. Check stats
        # 6. Stop instance
        # 7. Delete instance

        # Each step would be mocked appropriately
        pass

    def test_cli_help_system(self):
        """Test CLI help system."""
        # Test main help
        result = self.runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "Templates management" in result.output

        # Test subcommand help
        result = self.runner.invoke(templates, ["--help"])
        assert result.exit_code == 0
        assert "list" in result.output
        assert "register" in result.output

    def test_cli_version_command(self):
        """Test CLI version command."""
        result = self.runner.invoke(cli, ["--version"])
        assert result.exit_code == 0
        # Should display version information
