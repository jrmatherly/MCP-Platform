#!/usr/bin/env python3
"""
Trino MCP Server Configuration Handler.

This module handles configuration loading, validation, and management for the
Trino MCP server template.
"""

import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, Optional

# Import base configuration from MCP Platform
try:
    from mcp_platform.template.config.base import ServerConfig
except ImportError:
    # Fallback for Docker execution or direct script runs
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    try:
        from mcp_platform.template.config.base import ServerConfig
    except ImportError:
        # Create a minimal fallback if base config is not available
        class ServerConfig:
            def __init__(self, config_dict: dict = None):
                self.config_dict = config_dict or {}
                self.logger = logging.getLogger(__name__)

            def get_template_config(self):
                return self.config_dict

            def get_template_data(self):
                # Try to load template.json for fallback
                try:
                    template_path = Path(__file__).parent / "template.json"
                    with open(template_path, mode="r", encoding="utf-8") as f:
                        template_data = json.load(f)
                    # Merge with config overrides
                    template_data.update(self.config_dict)
                    return template_data
                except (FileNotFoundError, json.JSONDecodeError):
                    return self.config_dict


class TrinoServerConfig(ServerConfig):
    """
    Trino-specific configuration handler.

    Extends the base ServerConfig to provide Trino-specific configuration
    validation and defaults.
    """

    def __init__(self, config_dict: dict = None, skip_validation: bool = False):
        """Initialize Trino server configuration."""
        super().__init__(config_dict or {})
        self.logger = logging.getLogger(__name__)

        # Load template data
        self.template_data = self._load_template()

        # Validate required configuration (skip for testing)
        if not skip_validation:
            self._validate_config()

        # Set up logging based on config
        self._setup_logging()

    def _get_config(
        self, key: str, env_var: str, default: Any, cast_to: Optional[type] = str
    ) -> Any:
        """
        Get configuration value with precedence handling.

        Args:
            key: Configuration key in config_dict
            env_var: Environment variable name
            default: Default value if not found
            cast_to: Cast environment variable value to this type

        Returns:
            Configuration value
        """
        # Check config_dict first
        if key in self.config_dict:
            self.logger.debug(
                "Using config_dict value for '%s': %s", key, self.config_dict[key]
            )
            return self.config_dict[key]

        # Check environment variable
        env_value = os.getenv(env_var)
        if env_value is not None:
            self.logger.debug("Using environment variable '%s': %s", env_var, env_value)
            try:
                if cast_to == bool:
                    # Handle boolean environment variables
                    return env_value.lower() in ("true", "1", "yes", "on")
                return cast_to(env_value)
            except (ValueError, TypeError) as e:
                self.logger.error(
                    "Error casting environment variable '%s': %s", env_var, e
                )
                return env_value

        # Return default
        self.logger.debug("Using default value for '%s': %s", key, default)
        return default

    def get_template_config(self) -> Dict[str, Any]:
        """
        Get configuration properties from the template.

        Returns:
            Dictionary containing template configuration properties
        """
        properties_dict = {}
        properties = self.template_data.get("config_schema", {}).get("properties", {})

        for key, value in properties.items():
            # Load default values from environment or template
            env_var = value.get("env_mapping", key.upper())
            default_value = value.get("default", None)
            data_type = value.get("type", "string")

            if data_type == "integer":
                cast_to = int
            elif data_type == "number":
                cast_to = float
            elif data_type == "boolean":
                cast_to = bool
            else:
                cast_to = str

            properties_dict[key] = self._get_config(
                key, env_var, default_value, cast_to
            )

        return properties_dict

    def _validate_config(self):
        """Validate Trino-specific configuration requirements."""
        config = self.get_template_config()

        # Check required fields
        trino_host = config.get("trino_host")
        if not trino_host:
            raise ValueError(
                "trino_host is required. Set it in config or TRINO_HOST environment variable."
            )

        trino_user = config.get("trino_user")
        if not trino_user:
            raise ValueError(
                "trino_user is required. Set it in config or TRINO_USER environment variable."
            )

        # Validate port range
        trino_port = config.get("trino_port", 8080)
        try:
            trino_port = int(trino_port)
            if not (1 <= trino_port <= 65535):
                raise ValueError("trino_port must be between 1 and 65535")
        except (ValueError, TypeError) as e:
            raise ValueError("trino_port must be a valid integer") from e

        # Validate scheme
        trino_scheme = config.get("trino_scheme", "https")
        if trino_scheme not in ["http", "https"]:
            raise ValueError("trino_scheme must be 'http' or 'https'")

        # Validate OAuth configuration if enabled
        oauth_enabled = config.get("oauth_enabled", False)
        if oauth_enabled:
            oauth_provider = config.get("oauth_provider")
            if not oauth_provider:
                raise ValueError(
                    "oauth_provider is required when oauth_enabled is true"
                )

            valid_providers = ["hmac", "okta", "google", "azure"]
            if oauth_provider not in valid_providers:
                raise ValueError(f"oauth_provider must be one of: {valid_providers}")

            # Provider-specific validation
            if oauth_provider == "hmac" and not config.get("jwt_secret"):
                raise ValueError("jwt_secret is required when oauth_provider is 'hmac'")

            if oauth_provider in ["okta", "google", "azure"]:
                required_oidc_fields = ["oidc_issuer", "oidc_client_id"]
                for field in required_oidc_fields:
                    if not config.get(field):
                        raise ValueError(
                            f"{field} is required when oauth_provider is '{oauth_provider}'"
                        )

        # Validate timeout format and convert to seconds
        query_timeout = config.get("trino_query_timeout", "300")
        if isinstance(query_timeout, str):
            timeout_seconds = self._parse_duration(query_timeout)
            if timeout_seconds < 10 or timeout_seconds > 3600:
                raise ValueError(
                    "trino_query_timeout must be between 10 and 3600 seconds"
                )
        elif isinstance(query_timeout, int):
            if query_timeout < 10 or query_timeout > 3600:
                raise ValueError(
                    "trino_query_timeout must be between 10 and 3600 seconds"
                )

        # Validate max_results (set default if not provided)
        max_results = config.get("trino_max_results", 1000)
        try:
            max_results = int(max_results)
            if not (1 <= max_results <= 10000):
                raise ValueError("trino_max_results must be between 1 and 10000")
        except (ValueError, TypeError) as e:
            raise ValueError("trino_max_results must be a valid integer") from e

        # Validate log level
        log_level = config.get("log_level", "info")
        valid_log_levels = ["debug", "info", "warning", "error"]
        if log_level not in valid_log_levels:
            self.logger.warning(
                "Invalid log_level '%s', defaulting to 'info'", log_level
            )
            config["log_level"] = "info"

    def _parse_duration(self, duration_str: str) -> int:
        """
        Parse duration string to seconds.

        Supports formats like: 300, 300s, 5m, 1h
        """
        if isinstance(duration_str, int):
            return duration_str

        duration_str = duration_str.strip().lower()

        # If it's just a number, assume seconds
        if duration_str.isdigit():
            return int(duration_str)

        # Parse units
        match = re.match(r"^(\d+)([smh])$", duration_str)
        if not match:
            raise ValueError(f"Invalid duration format: {duration_str}")

        value, unit = match.groups()
        value = int(value)

        if unit == "s":
            return value
        elif unit == "m":
            return value * 60
        elif unit == "h":
            return value * 3600
        else:
            raise ValueError(f"Invalid duration unit: {unit}")

    def _setup_logging(self):
        """Set up logging based on configuration."""
        config = self.get_template_config()
        log_level = config.get("log_level", "info").upper()

        # Map string levels to logging constants
        level_map = {
            "DEBUG": logging.DEBUG,
            "INFO": logging.INFO,
            "WARNING": logging.WARNING,
            "ERROR": logging.ERROR,
        }

        logging_level = level_map.get(log_level, logging.INFO)

        # Configure root logger
        logging.basicConfig(
            level=logging_level,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )

        # Update our logger level
        self.logger.setLevel(logging_level)

    def get_connection_config(self) -> Dict[str, Any]:
        """Get Trino connection configuration."""
        config = self.get_template_config()

        connection_config = {
            "host": config.get("trino_host"),
            "port": config.get("trino_port", 8080),
            "user": config.get("trino_user"),
            "catalog": config.get("trino_catalog"),
            "schema": config.get("trino_schema"),
            "http_scheme": config.get("trino_scheme", "https"),
            "verify": not config.get("trino_ssl_insecure", True),
        }

        # Add password if provided
        if config.get("trino_password"):
            connection_config["password"] = config.get("trino_password")

        # Add OAuth configuration if enabled
        if config.get("oauth_enabled", False):
            connection_config["auth"] = self._get_oauth_auth_config(config)

        return connection_config

    def _get_oauth_auth_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Get OAuth authentication configuration."""
        oauth_provider = config.get("oauth_provider")

        if oauth_provider == "hmac":
            return {
                "type": "jwt",
                "secret": config.get("jwt_secret"),
            }
        elif oauth_provider in ["okta", "google", "azure"]:
            return {
                "type": "oidc",
                "issuer": config.get("oidc_issuer"),
                "audience": config.get("oidc_audience"),
                "client_id": config.get("oidc_client_id"),
                "client_secret": config.get("oidc_client_secret"),
                "redirect_uri": config.get("oauth_redirect_uri"),
            }
        else:
            raise ValueError(f"Unsupported OAuth provider: {oauth_provider}")

    def get_query_limits(self) -> Dict[str, int]:
        """Get query execution limits."""
        config = self.get_template_config()

        timeout_str = config.get("trino_query_timeout", "300")
        timeout_seconds = self._parse_duration(timeout_str)

        return {
            "timeout": timeout_seconds,
            "max_results": config.get("trino_max_results", 1000),
        }

    def get_security_config(self) -> Dict[str, Any]:
        """Get security-related configuration."""
        config = self.get_template_config()
        return {
            "read_only": not config.get("trino_allow_write_queries", False),
            "ssl_verify": not config.get("trino_ssl_insecure", True),
        }

    def is_read_only(self) -> bool:
        """Check if server is in read-only mode."""
        return not self.get_template_config().get("trino_allow_write_queries", False)

    def log_config_summary(self):
        """Log a summary of the current configuration (without sensitive data)."""
        config = self.get_template_config()

        # Remove sensitive information for logging
        safe_config = {
            "trino_host": config["trino_host"],
            "trino_port": config["trino_port"],
            "trino_user": config["trino_user"],
            "trino_scheme": config["trino_scheme"],
            "read_only": not config.get("trino_allow_write_queries", False),
            "oauth_enabled": config.get("oauth_enabled", False),
            "log_level": config["log_level"],
        }

        if config.get("trino_catalog"):
            safe_config["trino_catalog"] = config["trino_catalog"]
        if config.get("trino_schema"):
            safe_config["trino_schema"] = config["trino_schema"]
        if config.get("oauth_enabled"):
            safe_config["oauth_provider"] = config.get("oauth_provider")

        self.logger.info("Trino MCP Server Configuration:")
        for key, value in safe_config.items():
            self.logger.info("  %s: %s", key, value)

    def _load_template(self, template_path: str = None) -> Dict[str, Any]:
        """
        Load template data from template.json file.

        Args:
            template_path: Path to the template JSON file

        Returns:
            Parsed template data as dictionary
        """
        if not template_path:
            template_path = Path(__file__).parent / "template.json"

        try:
            with open(template_path, mode="r", encoding="utf-8") as template_file:
                return json.load(template_file)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            self.logger.warning(
                f"Failed to load template data from {template_path}: {e}"
            )
            # Return minimal template data as fallback
            return {
                "name": "Trino MCP Server",
                "version": "1.0.0",
                "description": "Trino MCP Server",
                "transport": {"port": 7090},
            }

    def get_template_data(self) -> Dict[str, Any]:
        """
        Get the full template data, potentially modified by configuration overrides.

        Returns:
            Template data dictionary with any configuration overrides applied
        """
        # Start with base template data
        template_data = self.template_data.copy()

        # Apply any template-level overrides from config_dict
        template_config_keys = set(self.get_template_config().keys())
        for key, value in self.config_dict.items():
            if key.lower() not in template_config_keys:
                # Direct template-level override (not in config_schema)
                template_key = key.lower()
                template_data[template_key] = value
                self.logger.debug(
                    "Applied template override: %s = %s", template_key, value
                )

        return template_data


# Convenience function for creating configuration
def create_trino_config(
    config_dict: Optional[Dict[str, Any]] = None,
    skip_validation: bool = False,
) -> TrinoServerConfig:
    """
    Create a Trino server configuration instance.

    Args:
        config_dict: Optional configuration dictionary
        skip_validation: Skip validation for testing

    Returns:
        TrinoServerConfig: Configured instance
    """
    return TrinoServerConfig(config_dict, skip_validation=skip_validation)
