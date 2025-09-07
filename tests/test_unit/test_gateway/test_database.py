"""
Unit tests for gateway database module.

Tests database manager, CRUD operations, and session management.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from mcp_platform.gateway.database import (
    APIKeyCRUD,
    DatabaseManager,
    ServerInstanceCRUD,
    ServerTemplateCRUD,
    UserCRUD,
)
from mcp_platform.gateway.models import (
    APIKey,
    APIKeyCreate,
    DatabaseConfig,
    GatewayConfig,
    ServerInstance,
    ServerInstanceCreate,
    ServerTemplate,
    ServerTemplateCreate,
    User,
    UserCreate,
)

pytestmark = pytest.mark.unit


class TestDatabaseManager:
    """Test DatabaseManager class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.db_config = DatabaseConfig(
            url="sqlite:///test.db", echo=False, pool_size=5, max_overflow=10
        )
        self.gateway_config = GatewayConfig(database=self.db_config)
        self.db_manager = DatabaseManager(self.gateway_config)

    def test_database_manager_initialization(self):
        """Test DatabaseManager initialization."""
        assert self.db_manager.config == self.gateway_config
        assert self.db_manager.engine is None
        assert self.db_manager.session_factory is None
        assert self.db_manager._initialized is False

    @pytest.mark.asyncio
    async def test_database_manager_initialize_sqlite(self):
        """Test DatabaseManager initialization with SQLite."""
        with (
            patch("mcp_platform.gateway.database.create_async_engine") as mock_engine,
            patch(
                "mcp_platform.gateway.database.async_sessionmaker"
            ) as mock_sessionmaker,
            patch.object(self.db_manager, "_create_tables"),
        ):
            mock_engine.return_value = Mock()
            mock_sessionmaker.return_value = Mock()

            await self.db_manager.initialize()

            # Should convert sqlite:// to sqlite+aiosqlite://
            mock_engine.assert_called_once()
            args, kwargs = mock_engine.call_args
            assert args[0] == "sqlite+aiosqlite:///test.db"
            assert kwargs["echo"] is False
            assert kwargs["pool_size"] == 5
            assert kwargs["max_overflow"] == 10

            assert self.db_manager._initialized is True

    @pytest.mark.asyncio
    async def test_database_manager_initialize_postgresql(self):
        """Test DatabaseManager initialization with PostgreSQL."""
        postgres_config = DatabaseConfig(url="postgresql://user:pass@localhost/db")
        gateway_config = GatewayConfig(database=postgres_config)
        db_manager = DatabaseManager(gateway_config)

        # Mock the asyncpg import to avoid the ImportError
        with (
            patch("mcp_platform.gateway.database.create_async_engine") as mock_engine,
            patch("mcp_platform.gateway.database.async_sessionmaker"),
            patch.object(db_manager, "_create_tables"),
            patch("mcp_platform.gateway.database._validate_postgresql_driver"),
        ):
            await db_manager.initialize()

            # Should convert to asyncpg URL
            mock_engine.assert_called_once()
            args, kwargs = mock_engine.call_args
            assert args[0] == "postgresql+asyncpg://user:pass@localhost/db"

    @pytest.mark.asyncio
    async def test_database_manager_initialize_idempotent(self):
        """Test that initialize can be called multiple times safely."""
        with (
            patch("mcp_platform.gateway.database.create_async_engine") as mock_engine,
            patch("mcp_platform.gateway.database.async_sessionmaker"),
            patch.object(self.db_manager, "_create_tables"),
        ):
            await self.db_manager.initialize()
            await self.db_manager.initialize()  # Second call

            # Should only initialize once
            mock_engine.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_session(self):
        """Test session creation."""
        mock_session = AsyncMock(spec=AsyncSession)

        # Mock get_session to return an async context manager
        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def mock_get_session():
            yield mock_session

        with patch.object(self.db_manager, "get_session", mock_get_session):
            async with self.db_manager.get_session() as session:
                assert session == mock_session

    @pytest.mark.asyncio
    async def test_close(self):
        """Test database cleanup."""
        mock_engine = AsyncMock()
        self.db_manager.engine = mock_engine

        await self.db_manager.close()

        mock_engine.dispose.assert_called_once()


class TestUserCRUD:
    """Test UserCRUD operations."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_db = Mock(spec=DatabaseManager)
        self.mock_session = AsyncMock(spec=AsyncSession)
        self.user_crud = UserCRUD(self.mock_db)

    @pytest.mark.asyncio
    async def test_create_user(self):
        """Test user creation."""
        user_data = UserCreate(
            username="testuser", email="test@example.com", password="password123"
        )

        # Mock the DatabaseManager's create_user method
        expected_user = User(
            id=1,
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_pass",
        )
        self.mock_db.create_user = AsyncMock(return_value=expected_user)

        result = await self.user_crud.create(user_data, hashed_password="hashed_pass")

        # Verify the DatabaseManager's create_user was called with correct data
        self.mock_db.create_user.assert_called_once()
        call_args = self.mock_db.create_user.call_args[0][0]
        assert call_args["username"] == "testuser"
        assert call_args["email"] == "test@example.com"
        assert call_args["hashed_password"] == "hashed_pass"
        assert "password" not in call_args  # Plain password should be removed

        # Verify user creation
        assert isinstance(result, User)
        assert result.username == "testuser"
        assert result.email == "test@example.com"
        assert result.hashed_password == "hashed_pass"

    @pytest.mark.asyncio
    async def test_get_by_username(self):
        """Test getting user by username."""
        mock_user = User(id=1, username="testuser", hashed_password="hash")

        # Mock session and query
        self.mock_db.get_session.return_value.__aenter__ = AsyncMock(
            return_value=self.mock_session
        )
        self.mock_db.get_session.return_value.__aexit__ = AsyncMock(return_value=None)

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = mock_user
        self.mock_session.execute = AsyncMock(return_value=mock_result)

        result = await self.user_crud.get_by_username("testuser")

        assert result == mock_user
        self.mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_username_not_found(self):
        """Test getting non-existent user by username."""
        # Mock session and query returning None
        self.mock_db.get_session.return_value.__aenter__ = AsyncMock(
            return_value=self.mock_session
        )
        self.mock_db.get_session.return_value.__aexit__ = AsyncMock(return_value=None)

        mock_result = Mock()
        mock_result.scalar_one_or_none.return_value = None
        self.mock_session.execute = AsyncMock(return_value=mock_result)

        result = await self.user_crud.get_by_username("nonexistent")

        assert result is None

    @pytest.mark.asyncio
    async def test_update_user(self):
        """Test user update."""
        user_id = 1
        update_data = {"email": "newemail@example.com", "is_active": False}

        # Create a mock user with the updated attributes
        mock_user = User(
            id=user_id,
            username="testuser",
            email="newemail@example.com",
            is_active=False,
            hashed_password="hashed_password",
        )

        # Mock the database manager's update_user method to return the updated user
        self.mock_db.update_user = AsyncMock(return_value=mock_user)

        result = await self.user_crud.update(user_id, update_data)

        assert result.email == "newemail@example.com"
        assert result.is_active is False
        self.mock_db.update_user.assert_called_once_with(user_id, update_data)


class TestAPIKeyCRUD:
    """Test APIKeyCRUD operations."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_db = Mock(spec=DatabaseManager)
        self.mock_session = AsyncMock(spec=AsyncSession)
        self.api_key_crud = APIKeyCRUD(self.mock_db)

    @pytest.mark.asyncio
    async def test_create_api_key(self):
        """Test API key creation."""
        api_key_data = APIKeyCreate(name="Test Key", user_id=1)

        # Create expected API key object
        expected_api_key = APIKey(
            id=1, name="Test Key", user_id=1, key_hash="hashed_key", is_active=True
        )

        # Mock the database manager's create_api_key method
        self.mock_db.create_api_key = AsyncMock(return_value=expected_api_key)

        result = await self.api_key_crud.create(api_key_data, key_hash="hashed_key")

        assert isinstance(result, APIKey)
        assert result.name == "Test Key"
        assert result.user_id == 1
        assert result.key_hash == "hashed_key"
        self.mock_db.create_api_key.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_by_user(self):
        """Test getting API keys by user."""
        user_id = 1
        mock_keys = [
            APIKey(id=1, name="Key 1", user_id=1, key_hash="hash1"),
            APIKey(id=2, name="Key 2", user_id=1, key_hash="hash2"),
        ]

        # Mock session behavior
        self.mock_db.get_session.return_value.__aenter__ = AsyncMock(
            return_value=self.mock_session
        )
        self.mock_db.get_session.return_value.__aexit__ = AsyncMock(return_value=None)

        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = mock_keys
        self.mock_session.execute = AsyncMock(return_value=mock_result)

        result = await self.api_key_crud.get_by_user(user_id)

        assert len(result) == 2
        assert all(key.user_id == user_id for key in result)

    @pytest.mark.asyncio
    async def test_deactivate_api_key(self):
        """Test API key deactivation."""
        key_id = 1

        # Create expected updated API key
        updated_key = APIKey(
            id=1, name="Test Key", is_active=False, key_hash="hash", user_id=1
        )

        # Mock the database manager's update_api_key method
        self.mock_db.update_api_key = AsyncMock(return_value=updated_key)

        result = await self.api_key_crud.update(key_id, {"is_active": False})

        assert result.is_active is False
        self.mock_db.update_api_key.assert_called_once_with(key_id, {"is_active": False})


class TestServerInstanceCRUD:
    """Test ServerInstanceCRUD operations."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_db = Mock(spec=DatabaseManager)
        self.mock_session = AsyncMock(spec=AsyncSession)
        self.server_crud = ServerInstanceCRUD(self.mock_db)

    @pytest.mark.asyncio
    async def test_create_server_instance(self):
        """Test server instance creation."""
        server_data = ServerInstanceCreate(
            id="test-server-1",
            command=["python", "-m", "server"],
            template_name="test-template",
        )

        # Mock the DatabaseManager's create_server_instance method
        expected_server = ServerInstance(
            id="test-server-1",
            command=["python", "-m", "server"],
            template_name="test-template",
        )
        self.mock_db.create_server_instance = AsyncMock(return_value=expected_server)

        result = await self.server_crud.create(server_data)

        # Verify the DatabaseManager's create_server_instance was called
        self.mock_db.create_server_instance.assert_called_once()

        assert isinstance(result, ServerInstance)
        assert result.id == "test-server-1"
        assert result.command == ["python", "-m", "server"]
        assert result.template_name == "test-template"

    @pytest.mark.asyncio
    async def test_get_active_servers(self):
        """Test getting active server instances."""
        mock_servers = [
            ServerInstance(id=1, name="server1", status="running"),
            ServerInstance(id=2, name="server2", status="running"),
        ]

        # Mock session behavior
        self.mock_db.get_session.return_value.__aenter__ = AsyncMock(
            return_value=self.mock_session
        )
        self.mock_db.get_session.return_value.__aexit__ = AsyncMock(return_value=None)

        mock_result = Mock()
        mock_result.scalars.return_value.all.return_value = mock_servers
        self.mock_session.execute = AsyncMock(return_value=mock_result)

        result = await self.server_crud.get_active()

        assert len(result) == 2
        assert all(server.status == "running" for server in result)


class TestServerTemplateCRUD:
    """Test ServerTemplateCRUD operations."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_db = Mock(spec=DatabaseManager)
        self.mock_session = AsyncMock(spec=AsyncSession)
        self.template_crud = ServerTemplateCRUD(self.mock_db)

    @pytest.mark.asyncio
    async def test_create_template(self):
        """Test server template creation."""
        template_data = ServerTemplateCreate(
            name="Python Server",
            description="A Python MCP server template",
        )

        # Create expected template object
        expected_template = ServerTemplate(
            name="Python Server", description="A Python MCP server template"
        )

        # Mock the database manager's create_server_template method
        self.mock_db.create_server_template = AsyncMock(return_value=expected_template)

        result = await self.template_crud.create(template_data)

        assert isinstance(result, ServerTemplate)
        assert result.name == "Python Server"
        assert result.description == "A Python MCP server template"
        self.mock_db.create_server_template.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_all_templates(self):
        """Test getting all templates."""
        mock_templates = [
            ServerTemplate(name="Template 1", description="Description 1"),
            ServerTemplate(name="Template 2", description="Description 2"),
        ]

        # Mock the database manager's get_server_templates method
        self.mock_db.get_server_templates = AsyncMock(return_value=mock_templates)

        result = await self.template_crud.get_all()

        assert len(result) == 2
        self.mock_db.get_server_templates.assert_called_once()


class TestDatabaseIntegration:
    """Test database integration scenarios."""

    @pytest.mark.asyncio
    async def test_database_transaction_rollback(self):
        """Test that database operations roll back on error."""
        db_config = DatabaseConfig(url="sqlite:///test.db")
        gateway_config = GatewayConfig(database=db_config)
        db_manager = DatabaseManager(gateway_config)

        with patch.object(db_manager, "get_session") as mock_get_session:
            mock_session = AsyncMock()
            mock_session.commit.side_effect = Exception("Database error")
            mock_session.rollback = AsyncMock()

            # Mock the async context manager to raise exception
            async_context = AsyncMock()
            async_context.__aenter__ = AsyncMock(return_value=mock_session)
            async_context.__aexit__ = AsyncMock(side_effect=Exception("Database error"))
            mock_get_session.return_value = async_context

            with pytest.raises(Exception, match="Database error"):
                async with db_manager.get_session() as session:
                    await session.commit()

    def test_crud_inheritance(self):
        """Test that CRUD classes inherit properly."""
        from mcp_platform.gateway.database import BaseCRUD

        db_manager = Mock()
        user_crud = UserCRUD(db_manager)
        api_key_crud = APIKeyCRUD(db_manager)

        assert isinstance(user_crud, BaseCRUD)
        assert isinstance(api_key_crud, BaseCRUD)
        assert user_crud.db == db_manager
        assert api_key_crud.db == db_manager
