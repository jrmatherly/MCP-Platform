"""
Pydantic models for MCP Gateway using SQLModel.

This module provides type-safe data models with validation, serialization,
and optional database persistence capabilities.
"""

import os
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import field_validator
from sqlmodel import JSON, Column, Relationship, SQLModel
from sqlmodel import Field as SQLField


class TransportType(str, Enum):
    """Transport protocol types."""

    HTTP = "http"
    STDIO = "stdio"


class ServerStatus(str, Enum):
    """Server health status."""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class BackendType(str, Enum):
    """Backend deployment types."""

    DOCKER = "docker"
    KUBERNETES = "kubernetes"
    LOCAL = "local"
    MOCK = "mock"


class LoadBalancingStrategy(str, Enum):
    """Load balancing strategies."""

    ROUND_ROBIN = "round_robin"
    LEAST_CONNECTIONS = "least_connections"
    WEIGHTED = "weighted"
    HEALTH_BASED = "health_based"
    RANDOM = "random"


class ServerInstanceBase(SQLModel):
    """Base model for server instances."""

    id: str = SQLField(primary_key=True)
    endpoint: str | None = None
    command: list[str] | None = SQLField(default=None, sa_column=Column(JSON))
    transport: TransportType = TransportType.HTTP
    status: ServerStatus = ServerStatus.UNKNOWN
    backend: BackendType = BackendType.DOCKER

    # Container/deployment metadata
    container_id: str | None = None
    deployment_id: str | None = None
    namespace: str | None = None

    # Runtime configuration
    working_dir: str | None = None
    env_vars: dict[str, str] | None = SQLField(default=None, sa_column=Column(JSON))

    # Health tracking
    last_health_check: datetime | None = None
    consecutive_failures: int = 0
    is_active: bool = True  # Whether the instance is active/enabled

    # Metadata
    instance_metadata: dict[str, Any] | None = SQLField(
        default=None, sa_column=Column(JSON)
    )

    # Timestamps
    created_at: datetime = SQLField(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = SQLField(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("command", mode="before")
    @classmethod
    def validate_command(cls, v):
        """Ensure command is a list of strings if provided."""
        if v is None:
            return v
        if isinstance(v, str):
            return [v]
        if isinstance(v, list):
            return [str(item) for item in v]
        return v

    def is_healthy(self) -> bool:
        """Check if server instance is healthy."""
        return self.status == ServerStatus.HEALTHY

    def update_health_status(self, is_healthy: bool):
        """Update health status and tracking."""
        if is_healthy:
            self.status = ServerStatus.HEALTHY
            self.consecutive_failures = 0
        else:
            self.status = ServerStatus.UNHEALTHY
            self.consecutive_failures += 1

        self.last_health_check = datetime.now(timezone.utc)
        self.updated_at = datetime.now(timezone.utc)


class ServerInstance(ServerInstanceBase, table=True):
    """Server instance table model."""

    __tablename__ = "server_instances"

    # Foreign key to template
    template_name: str = SQLField(foreign_key="server_templates.name", index=True)

    # Relationship to template
    template: Optional["ServerTemplate"] = Relationship(back_populates="instances")


class ServerInstanceCreate(ServerInstanceBase):
    """Model for creating server instances."""

    template_name: str


class ServerInstanceUpdate(SQLModel):
    """Model for updating server instances."""

    endpoint: str | None = None
    command: list[str] | None = None
    transport: TransportType | None = None
    status: ServerStatus | None = None
    backend: BackendType | None = None
    container_id: str | None = None
    deployment_id: str | None = None
    namespace: str | None = None
    working_dir: str | None = None
    env_vars: dict[str, str] | None = None
    consecutive_failures: int | None = None
    instance_metadata: dict[str, Any] | None = None


class ServerInstanceRead(ServerInstanceBase):
    """Model for reading server instances."""

    template_name: str


class LoadBalancerConfigBase(SQLModel):
    """Base model for load balancer configuration."""

    strategy: LoadBalancingStrategy = LoadBalancingStrategy.ROUND_ROBIN
    health_check_interval: int = SQLField(default=30, ge=5, le=300)
    max_retries: int = SQLField(default=3, ge=1, le=10)
    pool_size: int = SQLField(default=3, ge=1, le=20)
    timeout: int = SQLField(default=60, ge=5, le=300)


class LoadBalancerConfig(LoadBalancerConfigBase, table=True):
    """Load balancer configuration table model."""

    __tablename__ = "load_balancer_configs"

    id: int | None = SQLField(default=None, primary_key=True)
    template_name: str = SQLField(foreign_key="server_templates.name", unique=True)

    # Relationship to template
    template: Optional["ServerTemplate"] = Relationship(back_populates="load_balancer")


class LoadBalancerConfigCreate(LoadBalancerConfigBase):
    """Model for creating load balancer configurations."""

    template_name: str


class LoadBalancerConfigUpdate(SQLModel):
    """Model for updating load balancer configurations."""

    strategy: LoadBalancingStrategy | None = None
    health_check_interval: int | None = SQLField(default=None, ge=5, le=300)
    max_retries: int | None = SQLField(default=None, ge=1, le=10)
    pool_size: int | None = SQLField(default=None, ge=1, le=20)
    timeout: int | None = SQLField(default=None, ge=5, le=300)


class LoadBalancerConfigRead(LoadBalancerConfigBase):
    """Model for reading load balancer configurations."""

    id: int
    template_name: str


class ServerTemplateBase(SQLModel):
    """Base model for server templates."""

    name: str = SQLField(primary_key=True)
    description: str | None = None
    created_at: datetime = SQLField(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = SQLField(default_factory=lambda: datetime.now(timezone.utc))


class ServerTemplate(ServerTemplateBase, table=True):
    """Server template table model."""

    __tablename__ = "server_templates"

    # Relationships
    instances: list[ServerInstance] = Relationship(back_populates="template")
    load_balancer: LoadBalancerConfig | None = Relationship(
        back_populates="template"
    )

    def get_healthy_instances(self) -> list[ServerInstance]:
        """Get all healthy instances for this template."""
        return [instance for instance in self.instances if instance.is_healthy()]


class ServerTemplateCreate(ServerTemplateBase):
    """Model for creating server templates."""

    pass


class ServerTemplateUpdate(SQLModel):
    """Model for updating server templates."""

    description: str | None = None


class ServerTemplateRead(ServerTemplateBase):
    """Model for reading server templates."""

    instances: list[ServerInstanceRead] = []
    load_balancer: LoadBalancerConfigRead | None = None


# Authentication Models


class UserBase(SQLModel):
    """Base model for users."""

    username: str = SQLField(index=True, unique=True)
    email: str | None = SQLField(default=None, index=True)
    full_name: str | None = None
    is_active: bool = True
    is_superuser: bool = False


class User(UserBase, table=True):
    """User table model."""

    __tablename__ = "users"

    id: int | None = SQLField(default=None, primary_key=True)
    hashed_password: str
    created_at: datetime = SQLField(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = SQLField(default_factory=lambda: datetime.now(timezone.utc))

    # Relationships
    api_keys: list["APIKey"] = Relationship(back_populates="user")


class UserCreate(UserBase):
    """Model for creating users."""

    password: str


class UserUpdate(SQLModel):
    """Model for updating users."""

    email: str | None = None
    full_name: str | None = None
    password: str | None = None
    is_active: bool | None = None
    is_superuser: bool | None = None


class UserRead(UserBase):
    """Model for reading users."""

    id: int
    created_at: datetime
    updated_at: datetime


class APIKeyBase(SQLModel):
    """Base model for API keys."""

    name: str
    description: str | None = None
    scopes: list[str] = SQLField(default=[], sa_column=Column(JSON))
    is_active: bool = True
    expires_at: datetime | None = None


class APIKey(APIKeyBase, table=True):
    """API key table model."""

    __tablename__ = "api_keys"

    id: int | None = SQLField(default=None, primary_key=True)
    key_hash: str = SQLField(index=True)
    user_id: int = SQLField(foreign_key="users.id")
    created_at: datetime = SQLField(default_factory=lambda: datetime.now(timezone.utc))
    last_used: datetime | None = None

    # Relationships
    user: User | None = Relationship(back_populates="api_keys")

    def is_expired(self) -> bool:
        """Check if API key is expired."""
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.expires_at


class APIKeyCreate(APIKeyBase):
    """Model for creating API keys."""

    user_id: int


class APIKeyUpdate(SQLModel):
    """Model for updating API keys."""

    name: str | None = None
    description: str | None = None
    scopes: list[str] | None = None
    is_active: bool | None = None
    expires_at: datetime | None = None


class APIKeyRead(APIKeyBase):
    """Model for reading API keys."""

    id: int
    user_id: int
    created_at: datetime
    last_used: datetime | None = None


class APIKeyResponse(APIKeyRead):
    """API key response with the actual key (only shown once)."""

    key: str


# Request/Response Models


class ToolCallRequest(SQLModel):
    """Request model for tool calls."""

    name: str
    arguments: dict[str, Any] = {}


class ToolCallResponse(SQLModel):
    """Response model for tool calls."""

    content: list[dict[str, Any]]
    isError: bool = False
    _gateway_info: dict[str, Any] | None = None


class HealthCheckResponse(SQLModel):
    """Response model for health checks."""

    status: str
    healthy_instances: int
    total_instances: int
    instances: list[dict[str, Any]]


class GatewayStatsResponse(SQLModel):
    """Response model for gateway statistics."""

    total_requests: int
    active_connections: int
    templates: dict[str, Any]
    load_balancer: dict[str, Any]
    health_checker: dict[str, Any]


class TokenResponse(SQLModel):
    """Response model for authentication tokens."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int


# Configuration Models


class DatabaseConfig(SQLModel):
    """Database configuration model."""

    url: str = "sqlite:///./gateway.db"
    echo: bool = False
    pool_size: int = 5
    max_overflow: int = 10


class AuthConfig(SQLModel):
    """Authentication configuration model."""

    secret_key: str = os.getenv(
        "MCP_PLATFORM_AUTH_SECRET_KEY", "change-this-in-production"
    )  # Default for development
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    api_key_expire_days: int = 30


class GatewayConfig(SQLModel):
    """Gateway configuration model."""

    host: str = "localhost"
    port: int = 8080
    reload: bool = False
    workers: int = 1
    log_level: str = "info"
    cors_origins: list[str] = ["*"]
    database: DatabaseConfig = DatabaseConfig()
    auth: AuthConfig | None = None
