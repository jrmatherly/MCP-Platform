"""
Unit tests for database operations and persistence.
"""

import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from mcp_platform.gateway.database import (
    APIKeyCRUD,
    DatabaseManager,
    ServerInstanceCRUD,
    ServerTemplateCRUD,
    UserCRUD,
)
from mcp_platform.gateway.models import (
    APIKey,
    DatabaseConfig,
    GatewayConfig,
    LoadBalancerConfig,
    ServerInstance,
    ServerTemplate,
    User,
)


@pytest.fixture
async def test_db():
    """Create a test database."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
        db_path = tmp_file.name

    config = GatewayConfig(database=DatabaseConfig(url=f"sqlite:///{db_path}"))

    db = DatabaseManager(config)
    await db.initialize()

    yield db

    await db.close()
    Path(db_path).unlink(missing_ok=True)


class TestDatabaseManager:
    """Test DatabaseManager functionality."""

    async def test_initialization(self, test_db):
        """Test database initialization."""
        assert test_db._initialized is True
        assert test_db.engine is not None
        assert test_db.session_factory is not None

    async def test_health_check(self, test_db):
        """Test database health check."""
        is_healthy = await test_db.health_check()
        assert is_healthy is True

    async def test_session_context_manager(self, test_db):
        """Test database session context manager."""
        async with test_db.get_session() as session:
            assert session is not None
            # Session should be automatically closed after context


class TestServerInstanceCRUD:
    """Test ServerInstanceCRUD operations."""

    async def test_create_instance(self, test_db):
        """Test creating a server instance."""
        crud = ServerInstanceCRUD(test_db)

        instance = ServerInstance(
            id="test-1",
            template_name="demo",
            endpoint="http://localhost:8080",
            transport="http",
            status="healthy",
        )

        created = await crud.create(instance)
        assert created.id == "test-1"
        assert created.template_name == "demo"
        assert created.endpoint == "http://localhost:8080"

    async def test_get_instance(self, test_db):
        """Test retrieving a server instance."""
        crud = ServerInstanceCRUD(test_db)

        # Create instance
        instance = ServerInstance(
            id="test-2",
            template_name="demo",
            endpoint="http://localhost:8081",
        )
        await crud.create(instance)

        # Retrieve instance
        retrieved = await crud.get("test-2")
        assert retrieved is not None
        assert retrieved.id == "test-2"
        assert retrieved.template_name == "demo"
        assert retrieved.endpoint == "http://localhost:8081"

        # Non-existent instance
        missing = await crud.get("nonexistent")
        assert missing is None

    async def test_get_by_template(self, test_db):
        """Test retrieving instances by template."""
        crud = ServerInstanceCRUD(test_db)

        # Create instances for different templates
        instance1 = ServerInstance(id="demo-1", template_name="demo")
        instance2 = ServerInstance(id="demo-2", template_name="demo")
        instance3 = ServerInstance(id="fs-1", template_name="filesystem")

        await crud.create(instance1)
        await crud.create(instance2)
        await crud.create(instance3)

        # Get demo instances
        demo_instances = await crud.get_by_template("demo")
        assert len(demo_instances) == 2
        assert all(inst.template_name == "demo" for inst in demo_instances)

        # Get filesystem instances
        fs_instances = await crud.get_by_template("filesystem")
        assert len(fs_instances) == 1
        assert fs_instances[0].template_name == "filesystem"

    async def test_get_healthy_instances(self, test_db):
        """Test retrieving healthy instances."""
        crud = ServerInstanceCRUD(test_db)

        # Create instances with different health status
        healthy1 = ServerInstance(id="h1", template_name="demo", status="healthy")
        healthy2 = ServerInstance(id="h2", template_name="demo", status="healthy")
        unhealthy = ServerInstance(id="u1", template_name="demo", status="unhealthy")

        await crud.create(healthy1)
        await crud.create(healthy2)
        await crud.create(unhealthy)

        # Get healthy instances
        healthy_instances = await crud.get_healthy_by_template("demo")
        assert len(healthy_instances) == 2
        assert all(inst.status == "healthy" for inst in healthy_instances)

    async def test_update_instance(self, test_db):
        """Test updating a server instance."""
        crud = ServerInstanceCRUD(test_db)

        # Create instance
        instance = ServerInstance(id="test-update", template_name="demo")
        await crud.create(instance)

        # Update instance
        updates = {
            "status": "healthy",
            "endpoint": "http://localhost:9000",
            "consecutive_failures": 0,
        }
        updated = await crud.update("test-update", updates)

        assert updated is not None
        assert updated.status == "healthy"
        assert updated.endpoint == "http://localhost:9000"
        assert updated.consecutive_failures == 0

    async def test_delete_instance(self, test_db):
        """Test deleting a server instance."""
        crud = ServerInstanceCRUD(test_db)

        # Create instance
        instance = ServerInstance(id="test-delete", template_name="demo")
        await crud.create(instance)

        # Verify it exists
        retrieved = await crud.get("test-delete")
        assert retrieved is not None

        # Delete instance
        deleted = await crud.delete("test-delete")
        assert deleted is True

        # Verify it's gone
        missing = await crud.get("test-delete")
        assert missing is None

        # Delete non-existent instance
        not_deleted = await crud.delete("nonexistent")
        assert not_deleted is False

    async def test_list_all_instances(self, test_db):
        """Test listing all instances."""
        crud = ServerInstanceCRUD(test_db)

        # Create multiple instances
        instance1 = ServerInstance(id="all-1", template_name="demo")
        instance2 = ServerInstance(id="all-2", template_name="filesystem")
        instance3 = ServerInstance(id="all-3", template_name="demo")

        await crud.create(instance1)
        await crud.create(instance2)
        await crud.create(instance3)

        # List all
        all_instances = await crud.list_all()
        assert len(all_instances) >= 3  # May have instances from other tests

        # Check our instances are in the list
        our_ids = {inst.id for inst in all_instances}
        assert "all-1" in our_ids
        assert "all-2" in our_ids
        assert "all-3" in our_ids


class TestServerTemplateCRUD:
    """Test ServerTemplateCRUD operations."""

    async def test_create_template(self, test_db):
        """Test creating a server template."""
        crud = ServerTemplateCRUD(test_db)

        template = ServerTemplate(
            name="test-template",
            description="Test template",
        )

        created = await crud.create(template)
        assert created.name == "test-template"
        assert created.description == "Test template"

    async def test_get_template(self, test_db):
        """Test retrieving a server template."""
        crud = ServerTemplateCRUD(test_db)

        # Create template
        template = ServerTemplate(name="get-test", description="Get test template")
        await crud.create(template)

        # Retrieve template
        retrieved = await crud.get("get-test")
        assert retrieved is not None
        assert retrieved.name == "get-test"
        assert retrieved.description == "Get test template"

        # Non-existent template
        missing = await crud.get("nonexistent")
        assert missing is None

    async def test_update_template(self, test_db):
        """Test updating a server template."""
        crud = ServerTemplateCRUD(test_db)

        # Create template
        template = ServerTemplate(name="update-test")
        await crud.create(template)

        # Update template
        updates = {"description": "Updated description"}
        updated = await crud.update("update-test", updates)

        assert updated is not None
        assert updated.description == "Updated description"

    async def test_delete_template(self, test_db):
        """Test deleting a server template."""
        crud = ServerTemplateCRUD(test_db)

        # Create template
        template = ServerTemplate(name="delete-test")
        await crud.create(template)

        # Verify it exists
        retrieved = await crud.get("delete-test")
        assert retrieved is not None

        # Delete template
        deleted = await crud.delete("delete-test")
        assert deleted is True

        # Verify it's gone
        missing = await crud.get("delete-test")
        assert missing is None

    async def test_list_all_templates(self, test_db):
        """Test listing all templates."""
        crud = ServerTemplateCRUD(test_db)

        # Create multiple templates
        template1 = ServerTemplate(name="list-1")
        template2 = ServerTemplate(name="list-2")

        await crud.create(template1)
        await crud.create(template2)

        # List all
        all_templates = await crud.list_all()
        assert len(all_templates) >= 2

        # Check our templates are in the list
        our_names = {tmpl.name for tmpl in all_templates}
        assert "list-1" in our_names
        assert "list-2" in our_names


class TestUserCRUD:
    """Test UserCRUD operations."""

    async def test_create_user(self, test_db):
        """Test creating a user."""
        crud = UserCRUD(test_db)

        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password="hashed_password",
            is_active=True,
        )

        created = await crud.create(user)
        assert created.username == "testuser"
        assert created.email == "test@example.com"
        assert created.is_active is True

    async def test_get_user(self, test_db):
        """Test retrieving a user."""
        crud = UserCRUD(test_db)

        # Create user
        user = User(username="getuser", hashed_password="hash")
        created = await crud.create(user)
        user_id = created.id

        # Retrieve by ID
        retrieved = await crud.get(user_id)
        assert retrieved is not None
        assert retrieved.username == "getuser"

        # Non-existent user
        missing = await crud.get(99999)
        assert missing is None

    async def test_get_user_by_username(self, test_db):
        """Test retrieving user by username."""
        crud = UserCRUD(test_db)

        # Create user
        user = User(username="uniqueuser", hashed_password="hash")
        await crud.create(user)

        # Retrieve by username
        retrieved = await crud.get_by_username("uniqueuser")
        assert retrieved is not None
        assert retrieved.username == "uniqueuser"

        # Non-existent username
        missing = await crud.get_by_username("nonexistent")
        assert missing is None

    async def test_update_user(self, test_db):
        """Test updating a user."""
        crud = UserCRUD(test_db)

        # Create user
        user = User(username="updateuser", hashed_password="hash")
        created = await crud.create(user)

        # Update user
        updates = {
            "email": "updated@example.com",
            "full_name": "Updated Name",
            "is_active": False,
        }
        updated = await crud.update(created.id, updates)

        assert updated is not None
        assert updated.email == "updated@example.com"
        assert updated.full_name == "Updated Name"
        assert updated.is_active is False

    async def test_delete_user(self, test_db):
        """Test deleting a user."""
        crud = UserCRUD(test_db)

        # Create user
        user = User(username="deleteuser", hashed_password="hash")
        created = await crud.create(user)

        # Delete user
        deleted = await crud.delete(created.id)
        assert deleted is True

        # Verify it's gone
        missing = await crud.get(created.id)
        assert missing is None


class TestAPIKeyCRUD:
    """Test APIKeyCRUD operations."""

    async def test_create_api_key(self, test_db):
        """Test creating an API key."""
        # First create a user
        user_crud = UserCRUD(test_db)
        user = User(username="keyuser", hashed_password="hash")
        created_user = await user_crud.create(user)

        # Create API key
        api_crud = APIKeyCRUD(test_db)
        api_key = APIKey(
            name="test-key",
            description="Test API key",
            key_hash="hashed_key",
            user_id=created_user.id,
            scopes=["gateway:read"],
        )

        created = await api_crud.create(api_key)
        assert created.name == "test-key"
        assert created.description == "Test API key"
        assert created.user_id == created_user.id
        assert created.scopes == ["gateway:read"]

    async def test_get_api_key(self, test_db):
        """Test retrieving an API key."""
        # Create user and API key
        user_crud = UserCRUD(test_db)
        user = await user_crud.create(User(username="keyuser2", hashed_password="hash"))

        api_crud = APIKeyCRUD(test_db)
        api_key = APIKey(
            name="get-key",
            key_hash="hash",
            user_id=user.id,
        )
        created = await api_crud.create(api_key)

        # Retrieve by ID
        retrieved = await api_crud.get(created.id)
        assert retrieved is not None
        assert retrieved.name == "get-key"

    async def test_get_api_key_by_hash(self, test_db):
        """Test retrieving API key by hash."""
        # Create user and API key
        user_crud = UserCRUD(test_db)
        user = await user_crud.create(User(username="hashuser", hashed_password="hash"))

        api_crud = APIKeyCRUD(test_db)
        api_key = APIKey(
            name="hash-key",
            key_hash="unique_hash_123",
            user_id=user.id,
        )
        await api_crud.create(api_key)

        # Retrieve by hash
        retrieved = await api_crud.get_by_hash("unique_hash_123")
        assert retrieved is not None
        assert retrieved.name == "hash-key"
        assert retrieved.key_hash == "unique_hash_123"

    async def test_get_api_keys_by_user(self, test_db):
        """Test retrieving API keys by user."""
        # Create user
        user_crud = UserCRUD(test_db)
        user = await user_crud.create(User(username="multikey", hashed_password="hash"))

        # Create multiple API keys for the user
        api_crud = APIKeyCRUD(test_db)
        key1 = APIKey(name="key1", key_hash="hash1", user_id=user.id)
        key2 = APIKey(name="key2", key_hash="hash2", user_id=user.id)

        await api_crud.create(key1)
        await api_crud.create(key2)

        # Retrieve all keys for user
        user_keys = await api_crud.get_by_user(user.id)
        assert len(user_keys) == 2
        assert all(key.user_id == user.id for key in user_keys)

    async def test_update_api_key(self, test_db):
        """Test updating an API key."""
        # Create user and API key
        user_crud = UserCRUD(test_db)
        user = await user_crud.create(
            User(username="updatekey", hashed_password="hash")
        )

        api_crud = APIKeyCRUD(test_db)
        api_key = APIKey(name="update-key", key_hash="hash", user_id=user.id)
        created = await api_crud.create(api_key)

        # Update API key
        updates = {
            "description": "Updated description",
            "is_active": False,
            "scopes": ["gateway:write"],
        }
        updated = await api_crud.update(created.id, updates)

        assert updated is not None
        assert updated.description == "Updated description"
        assert updated.is_active is False
        assert updated.scopes == ["gateway:write"]

    async def test_delete_api_key(self, test_db):
        """Test deleting an API key."""
        # Create user and API key
        user_crud = UserCRUD(test_db)
        user = await user_crud.create(
            User(username="deletekey", hashed_password="hash")
        )

        api_crud = APIKeyCRUD(test_db)
        api_key = APIKey(name="delete-key", key_hash="hash", user_id=user.id)
        created = await api_crud.create(api_key)

        # Delete API key
        deleted = await api_crud.delete(created.id)
        assert deleted is True

        # Verify it's gone
        missing = await api_crud.get(created.id)
        assert missing is None


class TestDatabaseTransactions:
    """Test database transaction handling."""

    async def test_transaction_rollback_on_error(self, test_db):
        """Test that transactions are rolled back on errors."""
        crud = UserCRUD(test_db)

        # This should cause an error (duplicate username)
        user1 = User(username="duplicate", hashed_password="hash1")
        await crud.create(user1)

        # Try to create another user with same username
        user2 = User(username="duplicate", hashed_password="hash2")

        with pytest.raises(Exception):  # Should raise integrity error
            await crud.create(user2)

        # Verify only one user exists
        retrieved = await crud.get_by_username("duplicate")
        assert retrieved is not None
        assert retrieved.hashed_password == "hash1"  # First user preserved

    async def test_concurrent_access(self, test_db):
        """Test concurrent database access."""
        crud = ServerInstanceCRUD(test_db)

        # Create instances concurrently
        import asyncio

        async def create_instance(instance_id):
            instance = ServerInstance(
                id=f"concurrent-{instance_id}", template_name="demo"
            )
            return await crud.create(instance)

        # Create 5 instances concurrently
        tasks = [create_instance(i) for i in range(5)]
        results = await asyncio.gather(*tasks)

        # All should be created successfully
        assert len(results) == 5
        assert all(result.id.startswith("concurrent-") for result in results)

        # Verify they all exist
        all_instances = await crud.list_all()
        concurrent_instances = [
            inst for inst in all_instances if inst.id.startswith("concurrent-")
        ]
        assert len(concurrent_instances) == 5
