"""
Unit tests for Pydantic models and validation.
"""

from datetime import datetime, timezone
from typing import Any, Dict

import pytest

from mcp_platform.gateway.models import (
    APIKey,
    APIKeyCreate,
    GatewayConfig,
    LoadBalancerConfig,
    LoadBalancingStrategy,
    ServerInstance,
    ServerInstanceCreate,
    ServerStatus,
    ServerTemplate,
    TransportType,
    User,
    UserCreate,
)


class TestServerInstance:
    """Test ServerInstance model validation and methods."""

    def test_create_valid_instance(self):
        """Test creating a valid server instance."""
        instance = ServerInstance(
            id="test-1",
            template_name="demo",
            endpoint="http://localhost:8080",
            transport=TransportType.HTTP,
            status=ServerStatus.HEALTHY,
        )

        assert instance.id == "test-1"
        assert instance.template_name == "demo"
        assert instance.endpoint == "http://localhost:8080"
        assert instance.transport == TransportType.HTTP
        assert instance.status == ServerStatus.HEALTHY
        assert instance.is_healthy() is True

    def test_command_validation(self):
        """Test command field validation."""
        # String command should be converted to list
        instance = ServerInstanceCreate(
            id="test-1",
            template_name="demo",
            command="python server.py",
            transport=TransportType.STDIO,
        )

        assert instance.command == ["python server.py"]

        # List command should remain as list
        instance2 = ServerInstanceCreate(
            id="test-2",
            template_name="demo",
            command=["python", "server.py"],
            transport=TransportType.STDIO,
        )

        assert instance2.command == ["python", "server.py"]

    def test_health_status_update(self):
        """Test health status update method."""
        instance = ServerInstance(
            id="test-1",
            template_name="demo",
            endpoint="http://localhost:8080",
        )

        # Initially unknown
        assert instance.status == ServerStatus.UNKNOWN
        assert instance.consecutive_failures == 0

        # Mark as healthy
        instance.update_health_status(True)
        assert instance.status == ServerStatus.HEALTHY
        assert instance.consecutive_failures == 0
        assert instance.last_health_check is not None

        # Mark as unhealthy
        instance.update_health_status(False)
        assert instance.status == ServerStatus.UNHEALTHY
        assert instance.consecutive_failures == 1

    def test_defaults(self):
        """Test default values."""
        instance = ServerInstance(id="test-1", template_name="demo")

        assert instance.transport == TransportType.HTTP
        assert instance.status == ServerStatus.UNKNOWN
        assert instance.consecutive_failures == 0
        assert instance.created_at is not None
        assert instance.updated_at is not None


class TestLoadBalancerConfig:
    """Test LoadBalancerConfig model validation."""

    def test_create_valid_config(self):
        """Test creating valid load balancer config."""
        config = LoadBalancerConfig(
            template_name="demo",
            strategy=LoadBalancingStrategy.ROUND_ROBIN,
            health_check_interval=30,
            max_retries=3,
            pool_size=5,
            timeout=60,
        )

        assert config.template_name == "demo"
        assert config.strategy == LoadBalancingStrategy.ROUND_ROBIN
        assert config.health_check_interval == 30
        assert config.max_retries == 3
        assert config.pool_size == 5
        assert config.timeout == 60

    def test_defaults(self):
        """Test default values."""
        config = LoadBalancerConfig(template_name="demo")

        assert config.strategy == LoadBalancingStrategy.ROUND_ROBIN
        assert config.health_check_interval == 30
        assert config.max_retries == 3
        assert config.pool_size == 3
        assert config.timeout == 60

    def test_validation_ranges(self):
        """Test field validation ranges."""
        # Valid ranges
        config = LoadBalancerConfig(
            template_name="demo",
            health_check_interval=5,  # minimum
            max_retries=1,  # minimum
            pool_size=1,  # minimum
            timeout=5,  # minimum
        )
        assert config.health_check_interval == 5

        # Test maximum values
        config2 = LoadBalancerConfig(
            template_name="demo",
            health_check_interval=300,  # maximum
            max_retries=10,  # maximum
            pool_size=20,  # maximum
            timeout=300,  # maximum
        )
        assert config2.health_check_interval == 300


class TestUser:
    """Test User model validation."""

    def test_create_valid_user(self):
        """Test creating a valid user."""
        user = User(
            username="testuser",
            email="test@example.com",
            full_name="Test User",
            hashed_password="hashed_password",
            is_active=True,
            is_superuser=False,
        )

        assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.full_name == "Test User"
        assert user.is_active is True
        assert user.is_superuser is False

    def test_user_create_model(self):
        """Test UserCreate model."""
        user_create = UserCreate(
            username="newuser",
            email="new@example.com",
            password="secure_password",
            is_superuser=True,
        )

        assert user_create.username == "newuser"
        assert user_create.email == "new@example.com"
        assert user_create.password == "secure_password"
        assert user_create.is_superuser is True

    def test_defaults(self):
        """Test default values."""
        user = User(username="test", hashed_password="hash")

        assert user.is_active is True
        assert user.is_superuser is False
        assert user.email is None
        assert user.full_name is None


class TestAPIKey:
    """Test APIKey model validation."""

    def test_create_valid_api_key(self):
        """Test creating a valid API key."""
        api_key = APIKey(
            name="test-key",
            description="Test API key",
            key_hash="hashed_key",
            user_id=1,
            scopes=["gateway:read", "tools:call"],
            is_active=True,
        )

        assert api_key.name == "test-key"
        assert api_key.description == "Test API key"
        assert api_key.key_hash == "hashed_key"
        assert api_key.user_id == 1
        assert api_key.scopes == ["gateway:read", "tools:call"]
        assert api_key.is_active is True

    def test_expiration_check(self):
        """Test API key expiration check."""
        # Non-expiring key
        api_key = APIKey(
            name="test-key",
            key_hash="hash",
            user_id=1,
            expires_at=None,
        )
        assert api_key.is_expired() is False

        # Expired key
        past_time = datetime.now(timezone.utc).replace(year=2020)
        api_key_expired = APIKey(
            name="expired-key",
            key_hash="hash",
            user_id=1,
            expires_at=past_time,
        )
        assert api_key_expired.is_expired() is True

        # Future expiration
        future_time = datetime.now(timezone.utc).replace(year=2030)
        api_key_future = APIKey(
            name="future-key",
            key_hash="hash",
            user_id=1,
            expires_at=future_time,
        )
        assert api_key_future.is_expired() is False

    def test_api_key_create_model(self):
        """Test APIKeyCreate model."""
        api_key_create = APIKeyCreate(
            name="new-key",
            description="New test key",
            user_id=1,
            scopes=["gateway:write"],
        )

        assert api_key_create.name == "new-key"
        assert api_key_create.description == "New test key"
        assert api_key_create.user_id == 1
        assert api_key_create.scopes == ["gateway:write"]

    def test_defaults(self):
        """Test default values."""
        api_key = APIKey(name="test", key_hash="hash", user_id=1)

        assert api_key.scopes == []
        assert api_key.is_active is True
        assert api_key.expires_at is None
        assert api_key.description is None


class TestGatewayConfig:
    """Test GatewayConfig model validation."""

    def test_create_valid_config(self):
        """Test creating valid gateway config."""
        config = GatewayConfig(
            host="0.0.0.0",
            port=8080,
            cors_origins=["http://localhost:3000"],
        )

        assert config.host == "0.0.0.0"
        assert config.port == 8080
        assert config.cors_origins == ["http://localhost:3000"]

    def test_defaults(self):
        """Test default values."""
        config = GatewayConfig()

        assert config.host == "localhost"
        assert config.port == 8080
        assert config.reload is False
        assert config.workers == 1
        assert config.log_level == "info"
        assert config.cors_origins == ["*"]
        assert config.database is not None
        assert config.auth is not None

    def test_nested_configs(self):
        """Test nested configuration objects."""
        config = GatewayConfig()

        # Database config defaults
        assert config.database.url == "sqlite:///./gateway.db"
        assert config.database.echo is False
        assert config.database.pool_size == 5

        # Auth config defaults
        assert config.auth.algorithm == "HS256"
        assert config.auth.access_token_expire_minutes == 30
        assert config.auth.api_key_expire_days == 30


class TestEnumValidation:
    """Test enum validation in models."""

    def test_transport_type_enum(self):
        """Test TransportType enum validation."""
        # Valid values
        instance1 = ServerInstance(id="1", template_name="demo", transport="http")
        assert instance1.transport == TransportType.HTTP

        instance2 = ServerInstance(id="2", template_name="demo", transport="stdio")
        assert instance2.transport == TransportType.STDIO

        # Invalid values should raise validation error
        with pytest.raises(ValueError):
            ServerInstance(id="3", template_name="demo", transport="invalid")

    def test_server_status_enum(self):
        """Test ServerStatus enum validation."""
        # Valid values
        instance1 = ServerInstance(id="1", template_name="demo", status="healthy")
        assert instance1.status == ServerStatus.HEALTHY

        instance2 = ServerInstance(id="2", template_name="demo", status="unhealthy")
        assert instance2.status == ServerStatus.UNHEALTHY

        instance3 = ServerInstance(id="3", template_name="demo", status="unknown")
        assert instance3.status == ServerStatus.UNKNOWN

        # Invalid values should raise validation error
        with pytest.raises(ValueError):
            ServerInstance(id="4", template_name="demo", status="invalid")

    def test_load_balancing_strategy_enum(self):
        """Test LoadBalancingStrategy enum validation."""
        # Valid values
        config1 = LoadBalancerConfig(template_name="demo", strategy="round_robin")
        assert config1.strategy == LoadBalancingStrategy.ROUND_ROBIN

        config2 = LoadBalancerConfig(template_name="demo", strategy="least_connections")
        assert config2.strategy == LoadBalancingStrategy.LEAST_CONNECTIONS

        # Invalid values should raise validation error
        with pytest.raises(ValueError):
            LoadBalancerConfig(template_name="demo", strategy="invalid")


class TestModelSerialization:
    """Test model serialization and deserialization."""

    def test_server_instance_serialization(self):
        """Test ServerInstance serialization."""
        instance = ServerInstance(
            id="test-1",
            template_name="demo",
            endpoint="http://localhost:8080",
            transport=TransportType.HTTP,
            status=ServerStatus.HEALTHY,
            metadata={"key": "value"},
        )

        # Serialize to dict
        data = instance.dict()
        assert data["id"] == "test-1"
        assert data["template_name"] == "demo"
        assert data["endpoint"] == "http://localhost:8080"
        assert data["transport"] == "http"
        assert data["status"] == "healthy"
        assert data["metadata"] == {"key": "value"}

        # Deserialize from dict
        instance2 = ServerInstance(**data)
        assert instance2.id == instance.id
        assert instance2.template_name == instance.template_name
        assert instance2.endpoint == instance.endpoint
        assert instance2.transport == instance.transport
        assert instance2.status == instance.status

    def test_json_serialization(self):
        """Test JSON serialization."""
        instance = ServerInstance(
            id="test-1",
            template_name="demo",
            command=["python", "server.py"],
            env_vars={"DEBUG": "true"},
        )

        # Should be able to serialize to JSON
        json_str = instance.json()
        assert '"id":"test-1"' in json_str
        assert '"template_name":"demo"' in json_str

        # Should be able to deserialize from JSON
        instance2 = ServerInstance.parse_raw(json_str)
        assert instance2.id == instance.id
        assert instance2.command == instance.command
        assert instance2.env_vars == instance.env_vars
