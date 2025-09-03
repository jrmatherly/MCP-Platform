"""
Additional tests for gateway models to reach 70% test coverage goal.

Simple tests focusing on model validation and edge cases.
"""

from datetime import datetime

import pytest

from mcp_platform.gateway.models import (APIKey, AuthConfig, DatabaseConfig,
                                         GatewayConfig, LoadBalancerConfig,
                                         LoadBalancingStrategy, ServerInstance,
                                         ServerStatus, ServerTemplate,
                                         TransportType, User)

pytestmark = pytest.mark.unit


class TestModelValidationEdgeCases:
    """Test model validation edge cases."""

    def test_server_instance_edge_cases(self):
        """Test ServerInstance edge cases."""
        # Test with minimal required fields
        instance = ServerInstance(id="test-min", template_name="minimal-template")
        assert instance.id == "test-min"
        assert instance.template_name == "minimal-template"
        assert instance.status == ServerStatus.UNKNOWN  # Default

    def test_server_instance_timestamps(self):
        """Test ServerInstance timestamps are set."""
        instance = ServerInstance(id="test-timestamps", template_name="test-template")
        assert instance.created_at is not None
        assert instance.updated_at is not None
        assert isinstance(instance.created_at, datetime)

    def test_server_instance_health_methods(self):
        """Test ServerInstance health helper methods."""
        healthy_instance = ServerInstance(
            id="healthy", template_name="test", status=ServerStatus.HEALTHY
        )
        assert healthy_instance.is_healthy() is True

        unhealthy_instance = ServerInstance(
            id="unhealthy", template_name="test", status=ServerStatus.UNHEALTHY
        )
        assert unhealthy_instance.is_healthy() is False

    def test_server_instance_update_health(self):
        """Test ServerInstance health update method."""
        instance = ServerInstance(id="test-update", template_name="test")

        # Update to healthy
        instance.update_health_status(True)
        assert instance.status == ServerStatus.HEALTHY
        assert instance.consecutive_failures == 0

        # Update to unhealthy
        instance.update_health_status(False)
        assert instance.status == ServerStatus.UNHEALTHY
        assert instance.consecutive_failures == 1


class TestConfigModelsAdvanced:
    """Test advanced config model scenarios."""

    def test_database_config_sqlite_url(self):
        """Test DatabaseConfig with SQLite URL."""
        config = DatabaseConfig(url="sqlite:///test.db")
        assert config.url == "sqlite:///test.db"

    def test_database_config_postgresql_url(self):
        """Test DatabaseConfig with PostgreSQL URL."""
        config = DatabaseConfig(url="postgresql://user:pass@localhost/db")
        assert "postgresql" in config.url

    def test_auth_config_token_expiration(self):
        """Test AuthConfig token expiration settings."""
        config = AuthConfig(
            secret_key="test-secret-key-12345", access_token_expire_minutes=60
        )
        assert config.access_token_expire_minutes == 60

    def test_gateway_config_with_custom_values(self):
        """Test GatewayConfig with custom values."""
        config = GatewayConfig(host="0.0.0.0", port=9000, workers=4, log_level="debug")
        assert config.host == "0.0.0.0"
        assert config.port == 9000
        assert config.workers == 4
        assert config.log_level == "debug"

    def test_load_balancer_config_strategies(self):
        """Test LoadBalancerConfig with different strategies."""
        config = LoadBalancerConfig(strategy=LoadBalancingStrategy.LEAST_CONNECTIONS)
        assert config.strategy == LoadBalancingStrategy.LEAST_CONNECTIONS

        config2 = LoadBalancerConfig(strategy=LoadBalancingStrategy.WEIGHTED)
        assert config2.strategy == LoadBalancingStrategy.WEIGHTED


class TestModelSerialization:
    """Test model serialization capabilities."""

    def test_server_instance_json_serialization(self):
        """Test ServerInstance JSON serialization."""
        instance = ServerInstance(
            id="json-test",
            template_name="test-template",
            endpoint="http://localhost:8080",
            status=ServerStatus.HEALTHY,
        )

        json_data = instance.model_dump()
        assert json_data["id"] == "json-test"
        assert json_data["template_name"] == "test-template"
        assert json_data["endpoint"] == "http://localhost:8080"

    def test_config_json_serialization(self):
        """Test config model JSON serialization."""
        config = GatewayConfig(host="serialize-test", port=8888)

        json_data = config.model_dump()
        assert json_data["host"] == "serialize-test"
        assert json_data["port"] == 8888
        assert "database" in json_data

    def test_user_model_serialization(self):
        """Test User model serialization."""
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_password_123",
        )

        json_data = user.model_dump()
        assert json_data["username"] == "testuser"
        assert json_data["email"] == "test@example.com"


class TestModelRelationships:
    """Test model relationship functionality."""

    def test_server_template_basic_creation(self):
        """Test ServerTemplate creation."""
        template = ServerTemplate(name="test-template", description="A test template")
        assert template.name == "test-template"
        assert template.description == "A test template"

    def test_api_key_creation(self):
        """Test APIKey model creation."""
        api_key = APIKey(
            id="key-123",
            user_id="user-456",
            name="Test Key",
            key_hash="hashed_key_value",
        )
        assert api_key.id == "key-123"
        assert api_key.user_id == "user-456"
        assert api_key.name == "Test Key"

    def test_api_key_expiration_check(self):
        """Test APIKey expiration functionality."""
        # Test non-expired key (no expiration set)
        api_key = APIKey(
            id="never-expires",
            user_id="user-123",
            name="Never Expires",
            key_hash="hash123",
        )
        assert api_key.is_expired() is False


class TestEnumValidation:
    """Test enum validation in models."""

    def test_transport_type_validation(self):
        """Test TransportType enum validation."""
        # Test valid values
        instance_http = ServerInstance(
            id="http-test", template_name="test", transport=TransportType.HTTP
        )
        assert instance_http.transport == TransportType.HTTP

        instance_stdio = ServerInstance(
            id="stdio-test", template_name="test", transport=TransportType.STDIO
        )
        assert instance_stdio.transport == TransportType.STDIO

    def test_server_status_validation(self):
        """Test ServerStatus enum validation."""
        # Test all valid status values
        statuses = [ServerStatus.HEALTHY, ServerStatus.UNHEALTHY, ServerStatus.UNKNOWN]

        for status in statuses:
            instance = ServerInstance(
                id=f"status-{status.value}", template_name="test", status=status
            )
            assert instance.status == status

    def test_load_balancing_strategy_validation(self):
        """Test LoadBalancingStrategy enum validation."""
        strategies = [
            LoadBalancingStrategy.ROUND_ROBIN,
            LoadBalancingStrategy.LEAST_CONNECTIONS,
            LoadBalancingStrategy.WEIGHTED,
            LoadBalancingStrategy.HEALTH_BASED,
            LoadBalancingStrategy.RANDOM,
        ]

        for strategy in strategies:
            config = LoadBalancerConfig(strategy=strategy)
            assert config.strategy == strategy


class TestQuickValidationTests:
    """Quick tests to reach 70% coverage goal."""

    def test_server_instance_defaults(self):
        """Test ServerInstance default values."""
        instance = ServerInstance(id="defaults-test", template_name="test")
        assert instance.transport == TransportType.HTTP  # Default
        assert instance.consecutive_failures == 0
        assert instance.status == ServerStatus.UNKNOWN

    def test_config_model_defaults(self):
        """Test config model default values."""
        db_config = DatabaseConfig()
        assert db_config.echo is False  # Should have default

        gateway_config = GatewayConfig()
        assert gateway_config.reload is False
        assert gateway_config.workers == 1

    def test_model_string_representations(self):
        """Test model string representations work."""
        instance = ServerInstance(id="str-test", template_name="test")
        # Just test that str() doesn't crash
        str_repr = str(instance)
        assert isinstance(str_repr, str)
        assert "str-test" in str_repr
