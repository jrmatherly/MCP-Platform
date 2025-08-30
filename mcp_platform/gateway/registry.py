"""
Server Registry for MCP Gateway.

Manages registration, discovery, and metadata for MCP servers across different backends.
Provides persistent storage and dynamic updates for server instances.
"""

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

logger = logging.getLogger(__name__)


@dataclass
class ServerInstance:
    """Represents a single MCP server instance."""

    id: str
    template_name: str
    endpoint: Optional[str] = None  # HTTP endpoint URL
    command: Optional[List[str]] = None  # stdio command
    transport: str = "http"  # "http" or "stdio"
    status: str = "unknown"  # "healthy", "unhealthy", "unknown"
    backend: str = "docker"  # "docker", "kubernetes", "mock"

    # Container/deployment metadata
    container_id: Optional[str] = None
    deployment_id: Optional[str] = None
    namespace: Optional[str] = None  # Kubernetes namespace

    # Runtime configuration
    working_dir: Optional[str] = None
    env_vars: Optional[Dict[str, str]] = None

    # Health tracking
    last_health_check: Optional[str] = None
    consecutive_failures: int = 0

    # Metadata
    metadata: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ServerInstance":
        """Create from dictionary representation."""
        return cls(**data)

    def is_healthy(self) -> bool:
        """Check if server instance is healthy."""
        return self.status == "healthy"

    def update_health_status(self, is_healthy: bool):
        """Update health status and tracking."""
        if is_healthy:
            self.status = "healthy"
            self.consecutive_failures = 0
        else:
            self.status = "unhealthy"
            self.consecutive_failures += 1

        self.last_health_check = datetime.now(timezone.utc).isoformat()


@dataclass
class LoadBalancerConfig:
    """Load balancer configuration for a template."""

    strategy: str = (
        "round_robin"  # "round_robin", "least_connections", "weighted", "health_based"
    )
    health_check_interval: int = 30  # seconds
    max_retries: int = 3
    pool_size: int = 3  # For stdio servers
    timeout: int = 60  # Request timeout

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LoadBalancerConfig":
        """Create from dictionary representation."""
        return cls(**data)


@dataclass
class ServerTemplate:
    """Represents a template with its instances and configuration."""

    name: str
    instances: List[ServerInstance]
    load_balancer: LoadBalancerConfig

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "instances": [instance.to_dict() for instance in self.instances],
            "load_balancer": self.load_balancer.to_dict(),
        }

    @classmethod
    def from_dict(cls, name: str, data: Dict[str, Any]) -> "ServerTemplate":
        """Create from dictionary representation."""
        instances = [
            ServerInstance.from_dict(instance_data)
            for instance_data in data.get("instances", [])
        ]
        load_balancer = LoadBalancerConfig.from_dict(data.get("load_balancer", {}))
        return cls(name=name, instances=instances, load_balancer=load_balancer)

    def get_healthy_instances(self) -> List[ServerInstance]:
        """Get all healthy server instances."""
        return [instance for instance in self.instances if instance.is_healthy()]

    def get_instance_by_id(self, instance_id: str) -> Optional[ServerInstance]:
        """Get instance by ID."""
        for instance in self.instances:
            if instance.id == instance_id:
                return instance
        return None

    def add_instance(self, instance: ServerInstance):
        """Add a new server instance."""
        # Remove existing instance with same ID if exists
        self.instances = [inst for inst in self.instances if inst.id != instance.id]
        self.instances.append(instance)

    def remove_instance(self, instance_id: str) -> bool:
        """Remove server instance by ID."""
        original_count = len(self.instances)
        self.instances = [inst for inst in self.instances if inst.id != instance_id]
        return len(self.instances) < original_count


class ServerRegistry:
    """
    Central registry for managing MCP server instances across backends.

    Provides persistent storage, dynamic updates, and metadata management
    for all registered MCP servers.
    """

    def __init__(self, registry_file: Optional[Union[str, Path]] = None):
        """
        Initialize server registry.

        Args:
            registry_file: Path to JSON file for persistence. If None, uses in-memory only.
        """
        self.registry_file = Path(registry_file) if registry_file else None
        self.templates: Dict[str, ServerTemplate] = {}
        self._load_registry()

    def _load_registry(self):
        """Load registry from persistent storage."""
        if not self.registry_file or not self.registry_file.exists():
            logger.info("No existing registry file found, starting with empty registry")
            return

        try:
            with open(self.registry_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            servers_data = data.get("servers", {})
            for template_name, template_data in servers_data.items():
                self.templates[template_name] = ServerTemplate.from_dict(
                    template_name, template_data
                )

            logger.info(f"Loaded registry with {len(self.templates)} templates")

        except Exception as e:
            logger.error(f"Failed to load registry from {self.registry_file}: {e}")
            # Continue with empty registry

    def _save_registry(self):
        """Save registry to persistent storage."""
        if not self.registry_file:
            return  # In-memory only mode

        try:
            # Ensure directory exists
            self.registry_file.parent.mkdir(parents=True, exist_ok=True)

            # Prepare data structure
            data = {
                "servers": {
                    name: template.to_dict()
                    for name, template in self.templates.items()
                },
                "last_updated": datetime.now(timezone.utc).isoformat(),
            }

            # Write to file atomically
            temp_file = self.registry_file.with_suffix(".tmp")
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)

            temp_file.rename(self.registry_file)
            logger.debug(f"Registry saved to {self.registry_file}")

        except Exception as e:
            logger.error(f"Failed to save registry to {self.registry_file}: {e}")

    def register_server(
        self,
        template_name: str,
        instance: ServerInstance,
        load_balancer_config: Optional[LoadBalancerConfig] = None,
    ):
        """
        Register a new server instance.

        Args:
            template_name: Name of the template/server type
            instance: Server instance to register
            load_balancer_config: Optional load balancer configuration
        """
        # Ensure instance has correct template name
        instance.template_name = template_name

        # Get or create template
        if template_name not in self.templates:
            lb_config = load_balancer_config or LoadBalancerConfig()
            self.templates[template_name] = ServerTemplate(
                name=template_name, instances=[], load_balancer=lb_config
            )

        # Add instance to template
        self.templates[template_name].add_instance(instance)

        # Save to persistence
        self._save_registry()

        logger.info(
            f"Registered server instance {instance.id} for template {template_name}"
        )

    def deregister_server(self, template_name: str, instance_id: str) -> bool:
        """
        Deregister a server instance.

        Args:
            template_name: Name of the template
            instance_id: ID of the instance to remove

        Returns:
            True if instance was removed, False if not found
        """
        if template_name not in self.templates:
            return False

        template = self.templates[template_name]
        removed = template.remove_instance(instance_id)

        # Remove template if no instances remain
        if not template.instances:
            del self.templates[template_name]

        if removed:
            self._save_registry()
            logger.info(
                f"Deregistered server instance {instance_id} from template {template_name}"
            )

        return removed

    def get_template(self, template_name: str) -> Optional[ServerTemplate]:
        """Get server template by name."""
        return self.templates.get(template_name)

    def get_healthy_instances(self, template_name: str) -> List[ServerInstance]:
        """Get all healthy instances for a template."""
        template = self.get_template(template_name)
        if not template:
            return []
        return template.get_healthy_instances()

    def get_instance(
        self, template_name: str, instance_id: str
    ) -> Optional[ServerInstance]:
        """Get specific server instance."""
        template = self.get_template(template_name)
        if not template:
            return None
        return template.get_instance_by_id(instance_id)

    def list_templates(self) -> List[str]:
        """List all registered template names."""
        return list(self.templates.keys())

    def list_instances(self, template_name: str) -> List[ServerInstance]:
        """List all instances for a specific template."""
        template = self.get_template(template_name)
        if not template:
            return []
        return template.instances

    def list_all_instances(self) -> List[ServerInstance]:
        """List all registered server instances across all templates."""
        instances = []
        for template in self.templates.values():
            instances.extend(template.instances)
        return instances

    def update_instance_health(
        self, template_name: str, instance_id: str, is_healthy: bool
    ) -> bool:
        """
        Update health status of a server instance.

        Args:
            template_name: Name of the template
            instance_id: ID of the instance
            is_healthy: Whether the instance is healthy

        Returns:
            True if instance was updated, False if not found
        """
        instance = self.get_instance(template_name, instance_id)
        if not instance:
            return False

        instance.update_health_status(is_healthy)
        self._save_registry()
        return True

    def get_registry_stats(self) -> Dict[str, Any]:
        """Get registry statistics and overview."""
        total_instances = sum(
            len(template.instances) for template in self.templates.values()
        )
        healthy_instances = sum(
            len(template.get_healthy_instances())
            for template in self.templates.values()
        )

        return {
            "total_templates": len(self.templates),
            "total_instances": total_instances,
            "healthy_instances": healthy_instances,
            "unhealthy_instances": total_instances - healthy_instances,
            "templates": {
                name: {
                    "total_instances": len(template.instances),
                    "healthy_instances": len(template.get_healthy_instances()),
                    "load_balancer_strategy": template.load_balancer.strategy,
                }
                for name, template in self.templates.items()
            },
        }

    def clear_unhealthy_instances(self, max_failures: int = 5):
        """
        Remove instances that have exceeded maximum consecutive failures.

        Args:
            max_failures: Maximum consecutive failures before removal
        """
        removed_count = 0

        for template_name, template in list(self.templates.items()):
            original_count = len(template.instances)
            template.instances = [
                instance
                for instance in template.instances
                if instance.consecutive_failures < max_failures
            ]

            removed_from_template = original_count - len(template.instances)
            removed_count += removed_from_template

            if removed_from_template > 0:
                logger.info(
                    f"Removed {removed_from_template} unhealthy instances from template {template_name}"
                )

            # Remove template if no instances remain
            if not template.instances:
                del self.templates[template_name]
                logger.info(f"Removed empty template {template_name}")

        if removed_count > 0:
            self._save_registry()
            logger.info(f"Cleared {removed_count} unhealthy instances from registry")

        return removed_count
