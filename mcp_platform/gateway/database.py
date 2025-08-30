"""
Database module for MCP Gateway.

Provides database connectivity, session management, and CRUD operations
using SQLModel and SQLAlchemy.
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator, List, Optional

from sqlalchemy import event, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.sql import text
from sqlmodel import SQLModel

from .models import APIKey, GatewayConfig, ServerInstance, ServerTemplate, User

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database connections and operations."""

    def __init__(self, config: GatewayConfig):
        self.config = config
        self.engine = None
        self.session_factory = None
        self._initialized = False

    async def initialize(self):
        """Initialize database connection and create tables."""
        if self._initialized:
            return

        # Convert SQLite URL to async if needed
        db_url = self.config.database.url
        if db_url.startswith("sqlite:///"):
            db_url = db_url.replace("sqlite:///", "sqlite+aiosqlite:///")
        elif db_url.startswith("sqlite://"):
            db_url = db_url.replace("sqlite://", "sqlite+aiosqlite://")

        self.engine = create_async_engine(
            db_url,
            echo=self.config.database.echo,
            pool_size=self.config.database.pool_size,
            max_overflow=self.config.database.max_overflow,
            future=True,
        )

        # Enable foreign keys for SQLite
        if "sqlite" in db_url:

            @event.listens_for(self.engine.sync_engine, "connect")
            def set_sqlite_pragma(dbapi_connection, connection_record):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()

        self.session_factory = async_sessionmaker(
            self.engine, class_=AsyncSession, expire_on_commit=False
        )

        # Create tables
        async with self.engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)

        self._initialized = True
        logger.info(f"Database initialized with URL: {db_url}")

    async def close(self):
        """Close database connection."""
        if self.engine:
            await self.engine.dispose()
            self._initialized = False
            logger.info("Database connection closed")

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Get database session."""
        if not self._initialized:
            await self.initialize()

        async with self.session_factory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()

    async def health_check(self) -> bool:
        """Check database health."""
        try:
            async with self.get_session() as session:
                await session.execute(text("SELECT 1"))
                return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False


class ServerInstanceCRUD:
    """CRUD operations for server instances."""

    def __init__(self, db: DatabaseManager):
        self.db = db

    async def create(self, instance: ServerInstance) -> ServerInstance:
        """Create a new server instance."""
        async with self.db.get_session() as session:
            session.add(instance)
            await session.commit()
            await session.refresh(instance)
            return instance

    async def get(self, instance_id: str) -> Optional[ServerInstance]:
        """Get server instance by ID."""
        async with self.db.get_session() as session:
            result = await session.execute(
                select(ServerInstance).where(ServerInstance.id == instance_id)
            )
            return result.scalar_one_or_none()

    async def get_by_template(self, template_name: str) -> List[ServerInstance]:
        """Get all instances for a template."""
        async with self.db.get_session() as session:
            result = await session.execute(
                select(ServerInstance).where(
                    ServerInstance.template_name == template_name
                )
            )
            return list(result.scalars().all())

    async def get_healthy_by_template(self, template_name: str) -> List[ServerInstance]:
        """Get healthy instances for a template."""
        async with self.db.get_session() as session:
            result = await session.execute(
                select(ServerInstance).where(
                    ServerInstance.template_name == template_name,
                    ServerInstance.status == "healthy",
                )
            )
            return list(result.scalars().all())

    async def update(self, instance_id: str, updates: dict) -> Optional[ServerInstance]:
        """Update server instance."""
        async with self.db.get_session() as session:
            result = await session.execute(
                select(ServerInstance).where(ServerInstance.id == instance_id)
            )
            instance = result.scalar_one_or_none()
            if instance:
                for key, value in updates.items():
                    setattr(instance, key, value)
                await session.commit()
                await session.refresh(instance)
            return instance

    async def delete(self, instance_id: str) -> bool:
        """Delete server instance."""
        async with self.db.get_session() as session:
            result = await session.execute(
                select(ServerInstance).where(ServerInstance.id == instance_id)
            )
            instance = result.scalar_one_or_none()
            if instance:
                await session.delete(instance)
                await session.commit()
                return True
            return False

    async def list_all(self) -> List[ServerInstance]:
        """List all server instances."""
        async with self.db.get_session() as session:
            result = await session.execute(select(ServerInstance))
            return list(result.scalars().all())


class ServerTemplateCRUD:
    """CRUD operations for server templates."""

    def __init__(self, db: DatabaseManager):
        self.db = db

    async def create(self, template: ServerTemplate) -> ServerTemplate:
        """Create a new server template."""
        async with self.db.get_session() as session:
            session.add(template)
            await session.commit()
            await session.refresh(template)
            return template

    async def get(self, name: str) -> Optional[ServerTemplate]:
        """Get server template by name."""
        async with self.db.get_session() as session:
            result = await session.execute(
                select(ServerTemplate).where(ServerTemplate.name == name)
            )
            return result.scalar_one_or_none()

    async def update(self, name: str, updates: dict) -> Optional[ServerTemplate]:
        """Update server template."""
        async with self.db.get_session() as session:
            result = await session.execute(
                select(ServerTemplate).where(ServerTemplate.name == name)
            )
            template = result.scalar_one_or_none()
            if template:
                for key, value in updates.items():
                    setattr(template, key, value)
                await session.commit()
                await session.refresh(template)
            return template

    async def delete(self, name: str) -> bool:
        """Delete server template."""
        async with self.db.get_session() as session:
            result = await session.execute(
                select(ServerTemplate).where(ServerTemplate.name == name)
            )
            template = result.scalar_one_or_none()
            if template:
                await session.delete(template)
                await session.commit()
                return True
            return False

    async def list_all(self) -> List[ServerTemplate]:
        """List all server templates."""
        async with self.db.get_session() as session:
            result = await session.execute(select(ServerTemplate))
            return list(result.scalars().all())


class UserCRUD:
    """CRUD operations for users."""

    def __init__(self, db: DatabaseManager):
        self.db = db

    async def create(self, user: User) -> User:
        """Create a new user."""
        async with self.db.get_session() as session:
            session.add(user)
            await session.commit()
            await session.refresh(user)
            return user

    async def get(self, user_id: int) -> Optional[User]:
        """Get user by ID."""
        async with self.db.get_session() as session:
            result = await session.execute(select(User).where(User.id == user_id))
            return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> Optional[User]:
        """Get user by username."""
        async with self.db.get_session() as session:
            result = await session.execute(
                select(User).where(User.username == username)
            )
            return result.scalar_one_or_none()

    async def update(self, user_id: int, updates: dict) -> Optional[User]:
        """Update user."""
        async with self.db.get_session() as session:
            result = await session.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if user:
                for key, value in updates.items():
                    setattr(user, key, value)
                await session.commit()
                await session.refresh(user)
            return user

    async def delete(self, user_id: int) -> bool:
        """Delete user."""
        async with self.db.get_session() as session:
            result = await session.execute(select(User).where(User.id == user_id))
            user = result.scalar_one_or_none()
            if user:
                await session.delete(user)
                await session.commit()
                return True
            return False


class APIKeyCRUD:
    """CRUD operations for API keys."""

    def __init__(self, db: DatabaseManager):
        self.db = db

    async def create(self, api_key: APIKey) -> APIKey:
        """Create a new API key."""
        async with self.db.get_session() as session:
            session.add(api_key)
            await session.commit()
            await session.refresh(api_key)
            return api_key

    async def get(self, key_id: int) -> Optional[APIKey]:
        """Get API key by ID."""
        async with self.db.get_session() as session:
            result = await session.execute(select(APIKey).where(APIKey.id == key_id))
            return result.scalar_one_or_none()

    async def get_by_hash(self, key_hash: str) -> Optional[APIKey]:
        """Get API key by hash."""
        async with self.db.get_session() as session:
            result = await session.execute(
                select(APIKey).where(APIKey.key_hash == key_hash)
            )
            return result.scalar_one_or_none()

    async def get_by_user(self, user_id: int) -> List[APIKey]:
        """Get all API keys for a user."""
        async with self.db.get_session() as session:
            result = await session.execute(
                select(APIKey).where(APIKey.user_id == user_id)
            )
            return list(result.scalars().all())

    async def update(self, key_id: int, updates: dict) -> Optional[APIKey]:
        """Update API key."""
        async with self.db.get_session() as session:
            result = await session.execute(select(APIKey).where(APIKey.id == key_id))
            api_key = result.scalar_one_or_none()
            if api_key:
                for key, value in updates.items():
                    setattr(api_key, key, value)
                await session.commit()
                await session.refresh(api_key)
            return api_key

    async def delete(self, key_id: int) -> bool:
        """Delete API key."""
        async with self.db.get_session() as session:
            result = await session.execute(select(APIKey).where(APIKey.id == key_id))
            api_key = result.scalar_one_or_none()
            if api_key:
                await session.delete(api_key)
                await session.commit()
                return True
            return False


# Global database instance
db_manager: Optional[DatabaseManager] = None


async def get_database() -> DatabaseManager:
    """Dependency to get database manager."""
    if db_manager is None:
        raise RuntimeError("Database not initialized")
    return db_manager


async def initialize_database(config: GatewayConfig) -> DatabaseManager:
    """Initialize global database manager."""
    global db_manager
    db_manager = DatabaseManager(config)
    await db_manager.initialize()
    return db_manager


async def close_database():
    """Close global database manager."""
    global db_manager
    if db_manager:
        await db_manager.close()
        db_manager = None
