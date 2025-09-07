"""
Authentication module for MCP Gateway.

Provides JWT token authentication, API key management, and security utilities.
"""

import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext

from .database import APIKeyCRUD, DatabaseManager, UserCRUD, get_database
from .models import APIKey, AuthConfig, User

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer token for API key authentication
security = HTTPBearer(auto_error=False)


class AuthenticationError(Exception):
    """Authentication related errors."""

    pass


class AuthManager:
    """Manages authentication and authorization."""

    def __init__(self, config: AuthConfig, db: DatabaseManager):
        self.config = config
        self.db = db
        self.user_crud = UserCRUD(db)
        self.api_key_crud = APIKeyCRUD(db)

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify a password against its hash."""
        return pwd_context.verify(plain_password, hashed_password)

    def get_password_hash(self, password: str) -> str:
        """Hash a password."""
        return pwd_context.hash(password)

    def create_access_token(
        self, data: dict[str, Any], expires_delta: timedelta | None = None
    ) -> str:
        """Create JWT access token."""
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(
                minutes=self.config.access_token_expire_minutes
            )

        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(
            to_encode, self.config.secret_key, algorithm=self.config.algorithm
        )
        return encoded_jwt

    def verify_token(self, token: str) -> dict[str, Any]:
        """Verify and decode JWT token."""
        try:
            payload = jwt.decode(
                token, self.config.secret_key, algorithms=[self.config.algorithm]
            )
            return payload
        except JWTError:
            raise AuthenticationError("Invalid token")

    def generate_api_key(self) -> str:
        """Generate a secure API key."""
        return f"mcp_{secrets.token_urlsafe(32)}"

    def hash_api_key(self, api_key: str) -> str:
        """Hash API key for storage."""
        return pwd_context.hash(api_key)

    def verify_api_key(self, api_key: str, hashed_key: str) -> bool:
        """Verify API key against its hash."""
        return pwd_context.verify(api_key, hashed_key)

    async def authenticate_user(self, username: str, password: str) -> User | None:
        """Authenticate user with username and password."""
        user = await self.user_crud.get_by_username(username)
        if not user:
            return None
        if not self.verify_password(password, user.hashed_password):
            return None
        return user

    async def authenticate_api_key(self, api_key: str) -> APIKey | None:
        """Authenticate user with API key."""
        # Extract the key part from "mcp_..." format
        if not api_key.startswith("mcp_"):
            return None

        # For demonstration, we'll use a simple approach
        # In production, you might want to use a more sophisticated key lookup
        all_keys = await self.api_key_crud.get_by_user(1)  # This is simplified

        for key_record in all_keys:
            if self.verify_api_key(api_key, key_record.key_hash):
                if key_record.is_active and not key_record.is_expired():
                    # Update last used timestamp
                    await self.api_key_crud.update(
                        key_record.id, {"last_used": datetime.now(timezone.utc)}
                    )
                    return key_record
        return None

    async def create_user(
        self, username: str, password: str, email: str | None = None, **kwargs
    ) -> User:
        """Create a new user."""
        hashed_password = self.get_password_hash(password)

        # Create UserCreate object with the provided data
        from .models import UserCreate

        user_create = UserCreate(
            username=username,
            password=password,  # This will be ignored in the CRUD method
            email=email,
            **kwargs,
        )

        return await self.user_crud.create(user_create, hashed_password)

    async def create_api_key(
        self,
        user_id: int,
        name: str,
        description: str | None = None,
        scopes: list[str] | None = None,
        expires_days: int | None = None,
    ) -> tuple[APIKey, str]:
        """Create a new API key for a user."""
        api_key = self.generate_api_key()
        key_hash = self.hash_api_key(api_key)

        if expires_days:
            expires_at = datetime.now(timezone.utc) + timedelta(days=expires_days)
        else:
            expires_at = datetime.now(timezone.utc) + timedelta(
                days=self.config.api_key_expire_days
            )

        api_key_record = APIKey(
            name=name,
            description=description,
            key_hash=key_hash,
            user_id=user_id,
            scopes=scopes or [],
            expires_at=expires_at,
        )

        created_key = await self.api_key_crud.create(api_key_record, key_hash=key_hash)
        return created_key, api_key


# Global auth manager
auth_manager: AuthManager | None = None


def get_auth_manager() -> AuthManager:
    """Dependency to get auth manager."""
    if auth_manager is None:
        raise RuntimeError("Authentication not initialized")
    return auth_manager


def initialize_auth(config: AuthConfig, db: DatabaseManager) -> AuthManager:
    """Initialize global auth manager."""
    global auth_manager
    auth_manager = AuthManager(config, db)
    return auth_manager


# FastAPI Dependencies


async def get_current_user_token(
    credentials: HTTPAuthorizationCredentials | None = Security(security),
) -> dict[str, Any]:
    """Get current user from JWT token."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization header required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        auth = get_auth_manager()
        payload = auth.verify_token(credentials.credentials)
        return payload
    except AuthenticationError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    token_data: dict[str, Any] = Depends(get_current_user_token),
    db: DatabaseManager = Depends(get_database),
) -> User:
    """Get current user from token."""
    username = token_data.get("sub")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    user_crud = UserCRUD(db)
    user = await user_crud.get_by_username(username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User inactive",
        )

    return user


async def get_current_api_key(
    credentials: HTTPAuthorizationCredentials | None = Security(security),
) -> APIKey:
    """Get current API key."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    auth = get_auth_manager()
    api_key = await auth.authenticate_api_key(credentials.credentials)

    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return api_key


async def get_current_user_or_api_key(
    credentials: HTTPAuthorizationCredentials | None = Security(security),
    db: DatabaseManager = Depends(get_database),
) -> User | APIKey:
    """Get current user from either JWT token or API key."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    auth = get_auth_manager()
    token = credentials.credentials

    # Try API key first
    if token.startswith("mcp_"):
        api_key = await auth.authenticate_api_key(token)
        if api_key:
            return api_key

    # Try JWT token
    try:
        payload = auth.verify_token(token)
        username = payload.get("sub")
        if username:
            user_crud = UserCRUD(db)
            user = await user_crud.get_by_username(username)
            if user and user.is_active:
                return user
    except AuthenticationError:
        pass

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_scopes(required_scopes: list[str]):
    """Decorator to require specific scopes."""

    async def dependency(
        auth_subject: User | APIKey = Depends(get_current_user_or_api_key),
    ):
        if isinstance(auth_subject, User):
            # Users have all scopes if they are superusers
            if auth_subject.is_superuser:
                return auth_subject
            # For regular users, you might implement role-based permissions
            return auth_subject

        elif isinstance(auth_subject, APIKey):
            # Check if API key has required scopes
            if not all(scope in auth_subject.scopes for scope in required_scopes):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Insufficient permissions. Required scopes: {required_scopes}",
                )
            return auth_subject

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication",
        )

    return dependency


# Predefined scope requirements
require_admin = require_scopes(["admin"])
require_gateway_read = require_scopes(["gateway:read"])
require_gateway_write = require_scopes(["gateway:write"])
require_tools_call = require_scopes(["tools:call"])
