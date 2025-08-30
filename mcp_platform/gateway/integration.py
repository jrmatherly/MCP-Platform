"""
Gateway Integration - Connects MCP Gateway with existing deployment system.

Automatically registers/deregisters servers with the gateway when they are
deployed or removed through the existing MCP Platform.
"""

import logging
from typing import Any, Dict, Optional

from mcp_platform.core.multi_backend_manager import MultiBackendManager

from .registry import LoadBalancerConfig, ServerInstance, ServerRegistry

logger = logging.getLogger(__name__)


class GatewayIntegration:
    """
    Integrates MCP Gateway with existing deployment system.

    Monitors deployments and automatically registers/deregisters
    servers with the gateway registry.
    """

    def __init__(
        self,
        registry: ServerRegistry,
        backend_manager: Optional[MultiBackendManager] = None,
    ):
        """
        Initialize gateway integration.

        Args:
            registry: Gateway server registry
            backend_manager: Multi-backend manager for deployment monitoring
        """
        self.registry = registry
        self.backend_manager = backend_manager or MultiBackendManager()

    def sync_with_deployments(self):
        """
        Synchronize gateway registry with current deployments.

        Discovers running deployments and registers them with the gateway
        if they're not already registered.
        """
        try:
            # Get all deployments across backends
            all_deployments = self.backend_manager.get_all_deployments()
            logger.info(f"Found {len(all_deployments)} total deployments")

            # Track what we find vs what's registered
            found_instances = set()

            for deployment in all_deployments:
                if deployment.get("status") != "running":
                    continue  # Only register running deployments

                instance = self._deployment_to_server_instance(deployment)
                if instance:
                    # Register with gateway
                    self.register_deployment(instance.template_name, deployment)
                    found_instances.add((instance.template_name, instance.id))

            # Remove any registered instances that are no longer deployed
            self._cleanup_stale_registrations(found_instances)

            logger.info("Gateway registry synchronized with deployments")

        except Exception as e:
            logger.error(f"Failed to sync gateway with deployments: {e}")

    def register_deployment(
        self, template_name: str, deployment_info: Dict[str, Any]
    ) -> bool:
        """
        Register a deployment with the gateway.

        Args:
            template_name: Name of the template
            deployment_info: Deployment information from backend

        Returns:
            True if registration was successful
        """
        try:
            instance = self._deployment_to_server_instance(deployment_info)
            if not instance:
                logger.warning(
                    f"Could not convert deployment to server instance: {deployment_info}"
                )
                return False

            # Check if already registered
            existing = self.registry.get_instance(template_name, instance.id)
            if existing:
                # Update existing registration
                logger.debug(f"Updating existing registration for {instance.id}")
                existing.endpoint = instance.endpoint
                existing.command = instance.command
                existing.transport = instance.transport
                existing.backend = instance.backend
                existing.container_id = instance.container_id
                existing.deployment_id = instance.deployment_id
                existing.env_vars = instance.env_vars
                existing.instance_metadata = instance.instance_metadata
            else:
                # Create load balancer config if template doesn't exist
                lb_config = self._get_load_balancer_config(deployment_info)

                # Register new instance
                self.registry.register_server(template_name, instance, lb_config)
                logger.info(f"Registered deployment {instance.id} with gateway")

            return True

        except Exception as e:
            logger.error(f"Failed to register deployment with gateway: {e}")
            return False

    def deregister_deployment(self, template_name: str, deployment_id: str) -> bool:
        """
        Deregister a deployment from the gateway.

        Args:
            template_name: Name of the template
            deployment_id: Deployment ID to deregister

        Returns:
            True if deregistration was successful
        """
        try:
            # Find instance by deployment ID
            template = self.registry.get_template(template_name)
            if not template:
                return False

            instance_to_remove = None
            for instance in template.instances:
                if instance.deployment_id == deployment_id:
                    instance_to_remove = instance
                    break

            if not instance_to_remove:
                logger.warning(f"No instance found for deployment {deployment_id}")
                return False

            # Deregister from gateway
            success = self.registry.deregister_server(
                template_name, instance_to_remove.id
            )
            if success:
                logger.info(f"Deregistered deployment {deployment_id} from gateway")

            return success

        except Exception as e:
            logger.error(f"Failed to deregister deployment from gateway: {e}")
            return False

    def _deployment_to_server_instance(
        self, deployment_info: Dict[str, Any]
    ) -> Optional[ServerInstance]:
        """
        Convert deployment info to server instance.

        Args:
            deployment_info: Deployment information from backend

        Returns:
            ServerInstance or None if conversion fails
        """
        try:
            # Extract basic info
            deployment_id = deployment_info.get("id") or deployment_info.get(
                "deployment_id"
            )
            template_name = deployment_info.get("template") or deployment_info.get(
                "Template"
            )
            backend_type = deployment_info.get("backend_type", "docker")

            if not deployment_id or not template_name:
                logger.warning(
                    f"Missing required fields in deployment info: {deployment_info}"
                )
                return None

            # Create instance ID from deployment ID
            instance_id = f"{template_name}-{deployment_id[:8]}"

            # Determine transport and endpoint/command
            endpoint = deployment_info.get("endpoint")
            transport = "http" if endpoint else "stdio"
            command = None

            # For stdio transport, try to extract command from deployment
            if transport == "stdio":
                # Try to get command from various sources
                command_sources = [
                    deployment_info.get("command"),
                    deployment_info.get("args"),
                    deployment_info.get("config", {}).get("command"),
                ]

                for cmd_source in command_sources:
                    if cmd_source:
                        if isinstance(cmd_source, list):
                            command = cmd_source
                        elif isinstance(cmd_source, str):
                            command = cmd_source.split()
                        break

                # Default stdio command for containers
                if not command and deployment_info.get("container_id"):
                    command = [
                        "docker",
                        "exec",
                        "-i",
                        deployment_info["container_id"],
                        "python",
                        "server.py",
                    ]

            # Extract container/pod information
            container_id = deployment_info.get("container_id") or deployment_info.get(
                "ContainerID"
            )
            namespace = deployment_info.get("namespace")

            # Extract environment variables
            env_vars = {}
            env_sources = [
                deployment_info.get("env_vars"),
                deployment_info.get("environment"),
                deployment_info.get("config", {}).get("env_vars"),
            ]

            for env_source in env_sources:
                if isinstance(env_source, dict):
                    env_vars.update(env_source)

            # Create server instance
            instance = ServerInstance(
                id=instance_id,
                template_name=template_name,
                endpoint=endpoint,
                command=command,
                transport=transport,
                status="unknown",  # Will be updated by health checker
                backend=backend_type,
                container_id=container_id,
                deployment_id=deployment_id,
                namespace=namespace,
                env_vars=env_vars if env_vars else None,
                metadata={
                    "ports": deployment_info.get("ports"),
                    "image": deployment_info.get("image"),
                    "created": deployment_info.get("created"),
                    "config": deployment_info.get("config", {}),
                },
            )

            return instance

        except Exception as e:
            logger.error(f"Failed to convert deployment to server instance: {e}")
            return None

    def _get_load_balancer_config(
        self, deployment_info: Dict[str, Any]
    ) -> LoadBalancerConfig:
        """
        Get load balancer configuration for a deployment.

        Args:
            deployment_info: Deployment information

        Returns:
            LoadBalancerConfig with appropriate settings
        """
        # Try to get config from deployment metadata
        config_data = deployment_info.get("load_balancer", {})
        if isinstance(config_data, dict):
            return LoadBalancerConfig.from_dict(config_data)

        # Use defaults based on transport type
        transport = "http" if deployment_info.get("endpoint") else "stdio"

        if transport == "http":
            return LoadBalancerConfig(
                strategy="round_robin",
                health_check_interval=30,
                max_retries=3,
                timeout=60,
            )
        else:  # stdio
            return LoadBalancerConfig(
                strategy="round_robin",
                health_check_interval=60,  # Less frequent for stdio
                max_retries=2,
                pool_size=3,
                timeout=30,
            )

    def _cleanup_stale_registrations(self, found_instances: set):
        """
        Remove registered instances that are no longer deployed.

        Args:
            found_instances: Set of (template_name, instance_id) tuples for active deployments
        """
        try:
            stale_instances = []

            # Find instances in registry that weren't found in deployments
            for template_name, template in self.registry.templates.items():
                for instance in template.instances:
                    if (template_name, instance.id) not in found_instances:
                        stale_instances.append((template_name, instance.id))

            # Remove stale instances
            removed_count = 0
            for template_name, instance_id in stale_instances:
                success = self.registry.deregister_server(template_name, instance_id)
                if success:
                    removed_count += 1
                    logger.info(
                        f"Removed stale registration: {template_name}/{instance_id}"
                    )

            if removed_count > 0:
                logger.info(f"Cleaned up {removed_count} stale registrations")

        except Exception as e:
            logger.error(f"Failed to cleanup stale registrations: {e}")

    def get_integration_stats(self) -> Dict[str, Any]:
        """Get integration statistics."""
        try:
            # Get deployment counts per backend
            all_deployments = self.backend_manager.get_all_deployments()
            backend_counts = {}

            for deployment in all_deployments:
                backend_type = deployment.get("backend_type", "unknown")
                status = deployment.get("status", "unknown")

                if backend_type not in backend_counts:
                    backend_counts[backend_type] = {"running": 0, "total": 0}

                backend_counts[backend_type]["total"] += 1
                if status == "running":
                    backend_counts[backend_type]["running"] += 1

            # Get registry stats
            registry_stats = self.registry.get_registry_stats()

            return {
                "deployments": {
                    "total": len(all_deployments),
                    "by_backend": backend_counts,
                },
                "registry": registry_stats,
                "sync_ratio": {
                    "registered_instances": registry_stats["total_instances"],
                    "running_deployments": sum(
                        counts["running"] for counts in backend_counts.values()
                    ),
                },
            }

        except Exception as e:
            logger.error(f"Failed to get integration stats: {e}")
            return {"error": str(e)}
