"""
Enhanced Server Registry for MCP Gateway using SQLModel and Pydantic.

Provides persistent storage using SQLAlchemy with fallback to JSON file storage,
dynamic updates, and full CRUD operations for server instances and templates.
"""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .database import DatabaseManager, ServerInstanceCRUD, ServerTemplateCRUD
from .models import (
    LoadBalancerConfig,
    LoadBalancerConfigCreate,
    ServerInstance,
    ServerInstanceCreate,
    ServerStatus,
    ServerTemplate,
    ServerTemplateCreate,
)

logger = logging.getLogger(__name__)


class RegistryError(Exception):
    """Registry related errors."""

    pass


class ServerRegistry:
    """
    Enhanced server registry with database persistence and Pydantic models.

    Provides backward compatibility with the original registry while adding
    new features like database persistence, better validation, and async operations.
    """

    def __init__(
        self,
        db: DatabaseManager | None = None,
        fallback_file: str | Path | None = None,
    ):
        """
        Initialize enhanced server registry.

        Args:
            db: Database manager for persistence. If None, falls back to file storage.
            fallback_file: JSON file for fallback storage when database is unavailable.
        """
        self.db = db
        self.fallback_file = Path(fallback_file) if fallback_file else None
        self.instance_crud = ServerInstanceCRUD(db) if db else None
        self.template_crud = ServerTemplateCRUD(db) if db else None

        # In-memory cache for when database is not available
        self._memory_templates: dict[str, ServerTemplate] = {}
        self._use_memory = db is None

        if self._use_memory:
            self._load_from_file()

    async def _ensure_template_exists(self, template_name: str) -> ServerTemplate:
        """Ensure template exists in database."""
        if self._use_memory:
            if template_name not in self._memory_templates:
                template = ServerTemplate(
                    name=template_name, instances=[], load_balancer=None
                )
                self._memory_templates[template_name] = template
            return self._memory_templates[template_name]

        template = await self.template_crud.get(template_name)
        if not template:
            template_create = ServerTemplateCreate(name=template_name)
            template = await self.template_crud.create(
                ServerTemplate(**template_create.dict())
            )

            # Create default load balancer config
            lb_config = LoadBalancerConfig(template_name=template_name)
            template.load_balancer = lb_config

        return template

    def _load_from_file(self):
        """Load registry from JSON file (fallback mode)."""
        if not self.fallback_file or not self.fallback_file.exists():
            logger.info("No fallback registry file found, starting with empty registry")
            return

        try:
            with open(self.fallback_file, encoding="utf-8") as f:
                data = json.load(f)

            # Convert old format to new Pydantic models
            servers_data = data.get("servers", {})
            for template_name, template_data in servers_data.items():
                instances = []
                for instance_data in template_data.get("instances", []):
                    # Convert old format to new model
                    if "command" in instance_data and isinstance(
                        instance_data["command"], str
                    ):
                        instance_data["command"] = [instance_data["command"]]

                    instance = ServerInstance(**instance_data)
                    instances.append(instance)

                template = ServerTemplate(
                    name=template_name, instances=instances, load_balancer=None
                )
                self._memory_templates[template_name] = template

            logger.info(
                f"Loaded fallback registry with {len(self._memory_templates)} templates"
            )

        except Exception as e:
            logger.error(
                f"Failed to load fallback registry from {self.fallback_file}: {e}"
            )

    def _save_to_file(self):
        """Save registry to JSON file (fallback mode)."""
        if not self.fallback_file or not self._use_memory:
            return

        try:
            self.fallback_file.parent.mkdir(parents=True, exist_ok=True)

            data = {
                "servers": {
                    name: {
                        "instances": [
                            instance.dict() for instance in template.instances
                        ],
                        "load_balancer": (
                            template.load_balancer.dict()
                            if template.load_balancer
                            else {}
                        ),
                    }
                    for name, template in self._memory_templates.items()
                },
                "last_updated": datetime.now(timezone.utc).isoformat(),
            }

            temp_file = self.fallback_file.with_suffix(".tmp")
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)

            temp_file.rename(self.fallback_file)
            logger.debug(f"Registry saved to {self.fallback_file}")

        except Exception as e:
            logger.error(f"Failed to save registry to {self.fallback_file}: {e}")

    async def register_server(
        self,
        template_name: str,
        instance: ServerInstance | ServerInstanceCreate | dict[str, Any],
        load_balancer_config: LoadBalancerConfigCreate | None = None,
    ) -> ServerInstance:
        """
        Register a new server instance.

        Args:
            template_name: Name of the template/server type
            instance: Server instance to register
            load_balancer_config: Optional load balancer configuration

        Returns:
            The registered server instance
        """
        # Convert to ServerInstance if needed
        if isinstance(instance, dict):
            instance = ServerInstanceCreate(**instance)
        if isinstance(instance, ServerInstanceCreate):
            instance = ServerInstance(**instance.dict())

        # Ensure instance has correct template name
        instance.template_name = template_name

        if self._use_memory:
            # Memory mode
            await self._ensure_template_exists(template_name)
            template = self._memory_templates[template_name]

            # Remove existing instance with same ID
            template.instances = [
                inst for inst in template.instances if inst.id != instance.id
            ]
            template.instances.append(instance)

            self._save_to_file()
        else:
            # Database mode
            await self._ensure_template_exists(template_name)
            instance = await self.instance_crud.create(instance)

        logger.info(
            f"Registered server instance {instance.id} for template {template_name}"
        )
        return instance

    async def deregister_server(self, template_name: str, instance_id: str) -> bool:
        """
        Deregister a server instance.

        Args:
            template_name: Name of the template
            instance_id: ID of the instance to remove

        Returns:
            True if instance was removed, False if not found
        """
        if self._use_memory:
            if template_name not in self._memory_templates:
                return False

            template = self._memory_templates[template_name]
            original_count = len(template.instances)
            template.instances = [
                inst for inst in template.instances if inst.id != instance_id
            ]
            removed = len(template.instances) < original_count

            if not template.instances:
                del self._memory_templates[template_name]

            if removed:
                self._save_to_file()
        else:
            removed = await self.instance_crud.delete(instance_id)

        if removed:
            logger.info(
                f"Deregistered server instance {instance_id} from template {template_name}"
            )

        return removed

    async def get_template(self, template_name: str) -> ServerTemplate | None:
        """Get server template by name."""
        if self._use_memory:
            return self._memory_templates.get(template_name)
        else:
            return await self.template_crud.get(template_name)

    async def get_healthy_instances(self, template_name: str) -> list[ServerInstance]:
        """Get all healthy instances for a template."""
        if self._use_memory:
            template = self._memory_templates.get(template_name)
            if not template:
                return []
            return [inst for inst in template.instances if inst.is_healthy()]
        else:
            return await self.instance_crud.get_healthy_by_template(template_name)

    async def get_instance(
        self, template_name: str, instance_id: str
    ) -> ServerInstance | None:
        """Get specific server instance."""
        if self._use_memory:
            template = self._memory_templates.get(template_name)
            if not template:
                return None
            return next(
                (inst for inst in template.instances if inst.id == instance_id), None
            )
        else:
            return await self.instance_crud.get(instance_id)

    async def list_templates(self) -> list[str]:
        """List all registered template names."""
        if self._use_memory:
            return list(self._memory_templates.keys())
        else:
            templates = await self.template_crud.list_all()
            return [template.name for template in templates]

    async def list_instances(self, template_name: str) -> list[ServerInstance]:
        """List all instances for a specific template."""
        if self._use_memory:
            template = self._memory_templates.get(template_name)
            return template.instances if template else []
        else:
            return await self.instance_crud.get_by_template(template_name)

    async def list_all_instances(self) -> list[ServerInstance]:
        """List all registered server instances across all templates."""
        if self._use_memory:
            instances = []
            for template in self._memory_templates.values():
                instances.extend(template.instances)
            return instances
        else:
            return await self.instance_crud.list_all()

    async def update_instance_health(
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
        if self._use_memory:
            instance = await self.get_instance(template_name, instance_id)
            if not instance:
                return False

            instance.update_health_status(is_healthy)
            self._save_to_file()
            return True
        else:
            updates = {
                "status": (
                    ServerStatus.HEALTHY if is_healthy else ServerStatus.UNHEALTHY
                ),
                "last_health_check": datetime.now(timezone.utc),
                "consecutive_failures": 0 if is_healthy else None,
            }

            instance = await self.instance_crud.update(instance_id, updates)
            return instance is not None

    async def get_registry_stats(self) -> dict[str, Any]:
        """Get registry statistics and overview."""
        if self._use_memory:
            total_instances = sum(
                len(template.instances) for template in self._memory_templates.values()
            )
            healthy_instances = sum(
                len([inst for inst in template.instances if inst.is_healthy()])
                for template in self._memory_templates.values()
            )

            templates_stats = {}
            for name, template in self._memory_templates.items():
                healthy_count = len(
                    [inst for inst in template.instances if inst.is_healthy()]
                )
                templates_stats[name] = {
                    "total_instances": len(template.instances),
                    "healthy_instances": healthy_count,
                    "load_balancer_strategy": (
                        template.load_balancer.strategy
                        if template.load_balancer
                        else "round_robin"
                    ),
                }
        else:
            all_instances = await self.list_all_instances()
            total_instances = len(all_instances)
            healthy_instances = len(
                [inst for inst in all_instances if inst.is_healthy()]
            )

            templates = await self.template_crud.list_all()
            templates_stats = {}
            for template in templates:
                template_instances = await self.list_instances(template.name)
                healthy_count = len(
                    [inst for inst in template_instances if inst.is_healthy()]
                )
                templates_stats[template.name] = {
                    "total_instances": len(template_instances),
                    "healthy_instances": healthy_count,
                    "load_balancer_strategy": (
                        template.load_balancer.strategy
                        if template.load_balancer
                        else "round_robin"
                    ),
                }

        return {
            "total_templates": len(templates_stats),
            "total_instances": total_instances,
            "healthy_instances": healthy_instances,
            "unhealthy_instances": total_instances - healthy_instances,
            "templates": templates_stats,
        }

    async def clear_unhealthy_instances(self, max_failures: int = 5) -> int:
        """
        Remove instances that have exceeded maximum consecutive failures.

        Args:
            max_failures: Maximum consecutive failures before removal

        Returns:
            Number of instances removed
        """
        removed_count = 0

        if self._use_memory:
            for template_name, template in list(self._memory_templates.items()):
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

                if not template.instances:
                    del self._memory_templates[template_name]
                    logger.info(f"Removed empty template {template_name}")

            if removed_count > 0:
                self._save_to_file()
        else:
            # For database mode, we need to query and delete unhealthy instances
            all_instances = await self.list_all_instances()
            for instance in all_instances:
                if instance.consecutive_failures >= max_failures:
                    await self.deregister_server(instance.template_name, instance.id)
                    removed_count += 1

        if removed_count > 0:
            logger.info(f"Cleared {removed_count} unhealthy instances from registry")

        return removed_count
