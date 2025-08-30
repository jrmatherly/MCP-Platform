"""
Unit tests for authentication and authorization.
"""

import secrets
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, Mock

import pytest

from mcp_platform.gateway.auth import AuthenticationError, AuthManager
from mcp_platform.gateway.database import DatabaseManager
from mcp_platform.gateway.models import APIKey, AuthConfig, User


@pytest.mark.unit
@pytest.mark.gateway
@pytest.mark.auth
@pytest.fixture
def auth_config():
    """Create test auth configuration."""
    return AuthConfig(
        secret_key="test-secret-key-for-jwt-tokens-123",
        algorithm="HS256",
        access_token_expire_minutes=30,
        api_key_expire_days=30,
    )


@pytest.fixture
def mock_db():
    """Create mock database manager."""
    return Mock(spec=DatabaseManager)


@pytest.fixture
def auth_manager(auth_config, mock_db):
    """Create test auth manager."""
    return AuthManager(auth_config, mock_db)


@pytest.mark.unit
@pytest.mark.gateway
@pytest.mark.auth
class TestPasswordHashing:
    """Test password hashing functionality."""

    def test_password_hashing(self, auth_manager):
        """Test password hashing and verification."""
        password = "secure_password_123"

        # Hash password
        hashed = auth_manager.get_password_hash(password)
        assert hashed != password
        assert hashed.startswith("$2b$")  # bcrypt prefix

        # Verify correct password
        assert auth_manager.verify_password(password, hashed) is True

        # Verify incorrect password
        assert auth_manager.verify_password("wrong_password", hashed) is False

    def test_different_passwords_different_hashes(self, auth_manager):
        """Test that different passwords produce different hashes."""
        password1 = "password1"
        password2 = "password2"

        hash1 = auth_manager.get_password_hash(password1)
        hash2 = auth_manager.get_password_hash(password2)

        assert hash1 != hash2

    def test_same_password_different_salts(self, auth_manager):
        """Test that same password produces different hashes (due to salt)."""
        password = "same_password"

        hash1 = auth_manager.get_password_hash(password)
        hash2 = auth_manager.get_password_hash(password)

        # Different hashes due to random salt
        assert hash1 != hash2

        # But both verify correctly
        assert auth_manager.verify_password(password, hash1) is True
        assert auth_manager.verify_password(password, hash2) is True


class TestJWTTokens:
    """Test JWT token creation and verification."""

    def test_create_access_token(self, auth_manager):
        """Test JWT token creation."""
        data = {"sub": "testuser", "scopes": ["read", "write"]}

        token = auth_manager.create_access_token(data)
        assert isinstance(token, str)
        assert len(token.split(".")) == 3  # JWT has 3 parts

    def test_verify_valid_token(self, auth_manager):
        """Test verifying valid JWT token."""
        data = {"sub": "testuser", "role": "admin"}

        token = auth_manager.create_access_token(data)
        payload = auth_manager.verify_token(token)

        assert payload["sub"] == "testuser"
        assert payload["role"] == "admin"
        assert "exp" in payload  # Expiration should be added

    def test_verify_invalid_token(self, auth_manager):
        """Test verifying invalid JWT token."""
        invalid_token = "invalid.jwt.token"

        with pytest.raises(AuthenticationError):
            auth_manager.verify_token(invalid_token)

    def test_verify_expired_token(self, auth_manager):
        """Test verifying expired JWT token."""
        data = {"sub": "testuser"}

        # Create token with very short expiration
        expires_delta = timedelta(seconds=-1)  # Already expired
        token = auth_manager.create_access_token(data, expires_delta)

        with pytest.raises(AuthenticationError):
            auth_manager.verify_token(token)

    def test_custom_expiration(self, auth_manager):
        """Test custom token expiration."""
        data = {"sub": "testuser"}
        expires_delta = timedelta(minutes=60)

        token = auth_manager.create_access_token(data, expires_delta)
        payload = auth_manager.verify_token(token)

        # Check expiration is approximately 1 hour from now
        exp_time = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        expected_exp = datetime.now(timezone.utc) + expires_delta

        # Allow 10 second tolerance
        assert abs((exp_time - expected_exp).total_seconds()) < 10


class TestAPIKeyManagement:
    """Test API key generation and validation."""

    def test_generate_api_key(self, auth_manager):
        """Test API key generation."""
        api_key = auth_manager.generate_api_key()

        assert api_key.startswith("mcp_")
        assert len(api_key) > 20  # Should be reasonably long

        # Generate multiple keys - should be unique
        key1 = auth_manager.generate_api_key()
        key2 = auth_manager.generate_api_key()
        assert key1 != key2

    def test_hash_api_key(self, auth_manager):
        """Test API key hashing."""
        api_key = "mcp_test_key_123"

        hashed = auth_manager.hash_api_key(api_key)
        assert hashed != api_key
        assert hashed.startswith("$2b$")  # bcrypt prefix

    def test_verify_api_key(self, auth_manager):
        """Test API key verification."""
        api_key = "mcp_test_key_456"
        hashed = auth_manager.hash_api_key(api_key)

        # Correct key should verify
        assert auth_manager.verify_api_key(api_key, hashed) is True

        # Wrong key should not verify
        assert auth_manager.verify_api_key("mcp_wrong_key", hashed) is False


class TestUserAuthentication:
    """Test user authentication methods."""

    async def test_authenticate_user_success(self, auth_manager):
        """Test successful user authentication."""
        # Mock user CRUD
        mock_user = User(
            id=1,
            username="testuser",
            hashed_password=auth_manager.get_password_hash("correct_password"),
        )

        auth_manager.user_crud.get_by_username = AsyncMock(return_value=mock_user)

        # Authenticate with correct credentials
        user = await auth_manager.authenticate_user("testuser", "correct_password")
        assert user is not None
        assert user.username == "testuser"

    async def test_authenticate_user_wrong_password(self, auth_manager):
        """Test authentication with wrong password."""
        mock_user = User(
            id=1,
            username="testuser",
            hashed_password=auth_manager.get_password_hash("correct_password"),
        )

        auth_manager.user_crud.get_by_username = AsyncMock(return_value=mock_user)

        # Authenticate with wrong password
        user = await auth_manager.authenticate_user("testuser", "wrong_password")
        assert user is None

    async def test_authenticate_nonexistent_user(self, auth_manager):
        """Test authentication with nonexistent user."""
        auth_manager.user_crud.get_by_username = AsyncMock(return_value=None)

        user = await auth_manager.authenticate_user("nonexistent", "password")
        assert user is None


class TestCreateUser:
    """Test user creation functionality."""

    async def test_create_user_success(self, auth_manager):
        """Test successful user creation."""
        mock_created_user = User(
            id=1,
            username="newuser",
            email="new@example.com",
            hashed_password="hashed_password",
        )

        auth_manager.user_crud.create = AsyncMock(return_value=mock_created_user)

        user = await auth_manager.create_user(
            username="newuser",
            password="secure_password",
            email="new@example.com",
        )

        assert user.username == "newuser"
        assert user.email == "new@example.com"

        # Verify password was hashed
        create_call = auth_manager.user_crud.create.call_args[0][0]
        assert create_call.hashed_password != "secure_password"
        assert auth_manager.verify_password(
            "secure_password", create_call.hashed_password
        )

    async def test_create_user_with_extra_fields(self, auth_manager):
        """Test creating user with additional fields."""
        mock_created_user = User(
            id=1,
            username="adminuser",
            hashed_password="hash",
            is_superuser=True,
            full_name="Admin User",
        )

        auth_manager.user_crud.create = AsyncMock(return_value=mock_created_user)

        user = await auth_manager.create_user(
            username="adminuser",
            password="admin_password",
            is_superuser=True,
            full_name="Admin User",
        )

        assert user.is_superuser is True
        assert user.full_name == "Admin User"


class TestCreateAPIKey:
    """Test API key creation functionality."""

    async def test_create_api_key_success(self, auth_manager):
        """Test successful API key creation."""
        mock_api_key_record = APIKey(
            id=1,
            name="test-key",
            description="Test API key",
            key_hash="hashed_key",
            user_id=1,
            scopes=["gateway:read"],
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        )

        auth_manager.api_key_crud.create = AsyncMock(return_value=mock_api_key_record)

        api_key_record, api_key = await auth_manager.create_api_key(
            user_id=1,
            name="test-key",
            description="Test API key",
            scopes=["gateway:read"],
        )

        assert api_key_record.name == "test-key"
        assert api_key_record.description == "Test API key"
        assert api_key_record.scopes == ["gateway:read"]
        assert api_key.startswith("mcp_")

        # Verify API key was hashed
        create_call = auth_manager.api_key_crud.create.call_args[0][0]
        assert auth_manager.verify_api_key(api_key, create_call.key_hash)

    async def test_create_api_key_custom_expiration(self, auth_manager):
        """Test creating API key with custom expiration."""
        mock_api_key_record = APIKey(
            id=1,
            name="short-key",
            key_hash="hash",
            user_id=1,
            expires_at=datetime.now(timezone.utc) + timedelta(days=7),
        )

        auth_manager.api_key_crud.create = AsyncMock(return_value=mock_api_key_record)

        _, _ = await auth_manager.create_api_key(
            user_id=1,
            name="short-key",
            expires_days=7,
        )

        # Check expiration was set correctly
        create_call = auth_manager.api_key_crud.create.call_args[0][0]
        expected_exp = datetime.now(timezone.utc) + timedelta(days=7)

        # Allow 10 second tolerance
        assert abs((create_call.expires_at - expected_exp).total_seconds()) < 10

    async def test_create_api_key_default_expiration(self, auth_manager):
        """Test creating API key with default expiration."""
        mock_api_key_record = APIKey(
            id=1,
            name="default-key",
            key_hash="hash",
            user_id=1,
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        )

        auth_manager.api_key_crud.create = AsyncMock(return_value=mock_api_key_record)

        _, _ = await auth_manager.create_api_key(
            user_id=1,
            name="default-key",
        )

        # Check default expiration was used
        create_call = auth_manager.api_key_crud.create.call_args[0][0]
        expected_exp = datetime.now(timezone.utc) + timedelta(days=30)

        # Allow 10 second tolerance
        assert abs((create_call.expires_at - expected_exp).total_seconds()) < 10


class TestAPIKeyAuthentication:
    """Test API key authentication methods."""

    async def test_authenticate_api_key_success(self, auth_manager):
        """Test successful API key authentication."""
        # This test is simplified since the actual implementation
        # would require more complex API key lookup logic
        api_key = "mcp_valid_key_123"

        mock_api_key_record = APIKey(
            id=1,
            name="valid-key",
            key_hash=auth_manager.hash_api_key(api_key),
            user_id=1,
            is_active=True,
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        )

        # Mock the lookup method
        auth_manager.api_key_crud.get_by_user = AsyncMock(
            return_value=[mock_api_key_record]
        )
        auth_manager.api_key_crud.update = AsyncMock(return_value=mock_api_key_record)

        authenticated_key = await auth_manager.authenticate_api_key(api_key)
        assert authenticated_key is not None
        assert authenticated_key.name == "valid-key"

    async def test_authenticate_invalid_api_key_format(self, auth_manager):
        """Test authentication with invalid API key format."""
        invalid_key = "invalid_key_format"

        authenticated_key = await auth_manager.authenticate_api_key(invalid_key)
        assert authenticated_key is None

    async def test_authenticate_expired_api_key(self, auth_manager):
        """Test authentication with expired API key."""
        api_key = "mcp_expired_key_123"

        mock_api_key_record = APIKey(
            id=1,
            name="expired-key",
            key_hash=auth_manager.hash_api_key(api_key),
            user_id=1,
            is_active=True,
            expires_at=datetime.now(timezone.utc) - timedelta(days=1),  # Expired
        )

        auth_manager.api_key_crud.get_by_user = AsyncMock(
            return_value=[mock_api_key_record]
        )

        authenticated_key = await auth_manager.authenticate_api_key(api_key)
        assert authenticated_key is None

    async def test_authenticate_inactive_api_key(self, auth_manager):
        """Test authentication with inactive API key."""
        api_key = "mcp_inactive_key_123"

        mock_api_key_record = APIKey(
            id=1,
            name="inactive-key",
            key_hash=auth_manager.hash_api_key(api_key),
            user_id=1,
            is_active=False,  # Inactive
            expires_at=datetime.now(timezone.utc) + timedelta(days=30),
        )

        auth_manager.api_key_crud.get_by_user = AsyncMock(
            return_value=[mock_api_key_record]
        )

        authenticated_key = await auth_manager.authenticate_api_key(api_key)
        assert authenticated_key is None


class TestConfigurationValidation:
    """Test authentication configuration validation."""

    def test_valid_auth_config(self):
        """Test valid authentication configuration."""
        config = AuthConfig(
            secret_key="valid-secret-key-123",
            algorithm="HS256",
            access_token_expire_minutes=60,
            api_key_expire_days=90,
        )

        assert config.secret_key == "valid-secret-key-123"
        assert config.algorithm == "HS256"
        assert config.access_token_expire_minutes == 60
        assert config.api_key_expire_days == 90

    def test_auth_config_defaults(self):
        """Test authentication configuration defaults."""
        config = AuthConfig(secret_key="test-key")

        assert config.algorithm == "HS256"
        assert config.access_token_expire_minutes == 30
        assert config.api_key_expire_days == 30

    def test_empty_secret_key_allowed(self):
        """Test that empty secret key is allowed (will be generated)."""
        config = AuthConfig(secret_key="")
        assert config.secret_key == ""


class TestSecurityBestPractices:
    """Test security best practices implementation."""

    def test_password_hash_strength(self, auth_manager):
        """Test that password hashes are strong."""
        password = "test_password"
        hash1 = auth_manager.get_password_hash(password)
        hash2 = auth_manager.get_password_hash(password)

        # Different salts should produce different hashes
        assert hash1 != hash2

        # Hash should be long enough (bcrypt produces 60 char hashes)
        assert len(hash1) == 60
        assert len(hash2) == 60

    def test_api_key_uniqueness(self, auth_manager):
        """Test that API keys are unique."""
        keys = set()
        for _ in range(100):
            key = auth_manager.generate_api_key()
            assert key not in keys
            keys.add(key)

    def test_api_key_length(self, auth_manager):
        """Test that API keys are sufficiently long."""
        for _ in range(10):
            key = auth_manager.generate_api_key()
            # Remove prefix and check length
            key_part = key[4:]  # Remove "mcp_"
            assert len(key_part) >= 32  # Should be at least 32 characters

    def test_jwt_includes_expiration(self, auth_manager):
        """Test that JWT tokens always include expiration."""
        data = {"sub": "testuser"}
        token = auth_manager.create_access_token(data)
        payload = auth_manager.verify_token(token)

        assert "exp" in payload
        assert isinstance(payload["exp"], (int, float))

        # Expiration should be in the future
        exp_time = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        assert exp_time > datetime.now(timezone.utc)
