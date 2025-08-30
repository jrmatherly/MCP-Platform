"""
Gateway CLI commands for MCP Platform.

Adds gateway management commands to the existing CLI interface.
"""

import asyncio
import logging
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from mcp_platform.core.multi_backend_manager import MultiBackendManager
from mcp_platform.gateway import MCPGatewayServer
from mcp_platform.gateway.integration import GatewayIntegration
from mcp_platform.gateway.registry import ServerRegistry

logger = logging.getLogger(__name__)
console = Console()

# Gateway CLI app
gateway_app = typer.Typer(
    name="gateway", help="MCP Gateway management commands", rich_markup_mode="rich"
)


@gateway_app.command("start")
def start_gateway(
    host: str = typer.Option(
        "0.0.0.0", "--host", "-h", help="Host to bind the gateway to"
    ),
    port: int = typer.Option(8080, "--port", "-p", help="Port to bind the gateway to"),
    registry_file: Optional[str] = typer.Option(
        None, "--registry", "-r", help="Path to registry file for persistence"
    ),
    sync_deployments: bool = typer.Option(
        True, "--sync/--no-sync", help="Sync with existing deployments on startup"
    ),
    health_check_interval: int = typer.Option(
        30, "--health-interval", help="Health check interval in seconds"
    ),
    log_level: str = typer.Option("INFO", "--log-level", help="Log level"),
):
    """
    Start the MCP Gateway server.

    The gateway provides a unified HTTP endpoint for accessing all deployed MCP servers
    with automatic load balancing and health checking.
    """
    # Setup logging
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # Default registry file location
    if not registry_file:
        registry_file = str(Path.home() / ".mcp" / "gateway_registry.json")

    try:
        # Create gateway server
        gateway = MCPGatewayServer(
            host=host,
            port=port,
            registry_file=registry_file,
            health_check_interval=health_check_interval,
        )

        # Sync with existing deployments if requested
        if sync_deployments:
            console.print("[blue]Syncing with existing deployments...[/blue]")
            integration = GatewayIntegration(gateway.registry)
            integration.sync_with_deployments()

            stats = gateway.registry.get_registry_stats()
            console.print(
                f"[green]✓[/green] Registered {stats['total_instances']} instances "
                f"across {stats['total_templates']} templates"
            )

        # Display startup info
        console.print(
            Panel.fit(
                f"[bold]MCP Gateway Server[/bold]\n\n"
                f"• Gateway URL: [cyan]http://{host}:{port}[/cyan]\n"
                f"• Registry file: [dim]{registry_file}[/dim]\n"
                f"• Health check interval: [dim]{health_check_interval}s[/dim]\n"
                f"• Log level: [dim]{log_level}[/dim]\n\n"
                f"[bold]Access patterns:[/bold]\n"
                f"• List tools: [cyan]GET /mcp/{{template}}/tools/list[/cyan]\n"
                f"• Call tool: [cyan]POST /mcp/{{template}}/tools/call[/cyan]\n"
                f"• Gateway health: [cyan]GET /gateway/health[/cyan]\n"
                f"• Registry status: [cyan]GET /gateway/registry[/cyan]",
                title="🚀 Starting Gateway",
                border_style="green",
            )
        )

        # Run the server
        asyncio.run(gateway.start())
        gateway.run()

    except KeyboardInterrupt:
        console.print("[yellow]Gateway shutdown requested[/yellow]")
    except Exception as e:
        console.print(f"[red]❌ Failed to start gateway: {e}[/red]")
        raise typer.Exit(1)


@gateway_app.command("status")
def gateway_status(
    registry_file: Optional[str] = typer.Option(
        None, "--registry", "-r", help="Path to registry file"
    ),
):
    """
    Show current gateway status and registered servers.
    """
    # Default registry file location
    if not registry_file:
        registry_file = str(Path.home() / ".mcp" / "gateway_registry.json")

    try:
        registry = ServerRegistry(registry_file)
        stats = registry.get_registry_stats()

        # Main status table
        status_table = Table(title="Gateway Registry Status")
        status_table.add_column("Metric", style="cyan")
        status_table.add_column("Value", style="green")

        status_table.add_row("Total Templates", str(stats["total_templates"]))
        status_table.add_row("Total Instances", str(stats["total_instances"]))
        status_table.add_row("Healthy Instances", str(stats["healthy_instances"]))
        status_table.add_row("Unhealthy Instances", str(stats["unhealthy_instances"]))

        console.print(status_table)

        if stats["total_templates"] > 0:
            # Templates table
            templates_table = Table(title="Registered Templates")
            templates_table.add_column("Template", style="cyan")
            templates_table.add_column("Instances", style="yellow")
            templates_table.add_column("Healthy", style="green")
            templates_table.add_column("Strategy", style="blue")

            for template_name, template_stats in stats["templates"].items():
                templates_table.add_row(
                    template_name,
                    str(template_stats["total_instances"]),
                    str(template_stats["healthy_instances"]),
                    template_stats["load_balancer_strategy"],
                )

            console.print(templates_table)

            # Instances table
            instances_table = Table(title="Server Instances")
            instances_table.add_column("Instance ID", style="cyan")
            instances_table.add_column("Template", style="yellow")
            instances_table.add_column("Transport", style="blue")
            instances_table.add_column("Status", style="white")
            instances_table.add_column("Endpoint/Command", style="dim")

            all_instances = registry.list_all_instances()
            for instance in all_instances:
                status_style = "green" if instance.is_healthy() else "red"
                endpoint_display = instance.endpoint or " ".join(instance.command or [])
                if len(endpoint_display) > 50:
                    endpoint_display = endpoint_display[:47] + "..."

                instances_table.add_row(
                    instance.id,
                    instance.template_name,
                    instance.transport,
                    f"[{status_style}]{instance.status}[/{status_style}]",
                    endpoint_display,
                )

            console.print(instances_table)

    except Exception as e:
        console.print(f"[red]❌ Failed to get gateway status: {e}[/red]")
        raise typer.Exit(1)


@gateway_app.command("sync")
def sync_deployments(
    registry_file: Optional[str] = typer.Option(
        None, "--registry", "-r", help="Path to registry file"
    ),
    backend: Optional[str] = typer.Option(
        None,
        "--backend",
        "-b",
        help="Specific backend to sync (docker, kubernetes, etc.)",
    ),
):
    """
    Sync gateway registry with current deployments.

    Discovers running MCP server deployments and registers them with the gateway.
    Removes stale registrations for deployments that no longer exist.
    """
    # Default registry file location
    if not registry_file:
        registry_file = str(Path.home() / ".mcp" / "gateway_registry.json")

    try:
        registry = ServerRegistry(registry_file)

        # Create backend manager
        if backend:
            backend_manager = MultiBackendManager([backend])
        else:
            backend_manager = MultiBackendManager()

        # Create integration and sync
        integration = GatewayIntegration(registry, backend_manager)

        console.print("[blue]Syncing with current deployments...[/blue]")

        # Get stats before sync
        before_stats = registry.get_registry_stats()

        # Perform sync
        integration.sync_with_deployments()

        # Get stats after sync
        after_stats = registry.get_registry_stats()

        # Show results
        instances_added = (
            after_stats["total_instances"] - before_stats["total_instances"]
        )

        sync_table = Table(title="Sync Results")
        sync_table.add_column("Metric", style="cyan")
        sync_table.add_column("Before", style="yellow")
        sync_table.add_column("After", style="green")
        sync_table.add_column("Change", style="blue")

        sync_table.add_row(
            "Templates",
            str(before_stats["total_templates"]),
            str(after_stats["total_templates"]),
            f"+{after_stats['total_templates'] - before_stats['total_templates']}",
        )
        sync_table.add_row(
            "Instances",
            str(before_stats["total_instances"]),
            str(after_stats["total_instances"]),
            f"+{instances_added}" if instances_added >= 0 else str(instances_added),
        )

        console.print(sync_table)

        if instances_added > 0:
            console.print(
                f"[green]✓[/green] Added {instances_added} new instances to gateway"
            )
        elif instances_added < 0:
            console.print(
                f"[yellow]✓[/yellow] Removed {abs(instances_added)} stale instances from gateway"
            )
        else:
            console.print("[blue]✓[/blue] Gateway registry is already up to date")

    except Exception as e:
        console.print(f"[red]❌ Failed to sync deployments: {e}[/red]")
        raise typer.Exit(1)


@gateway_app.command("register")
def register_server(
    template_name: str = typer.Argument(..., help="Template name"),
    endpoint: Optional[str] = typer.Option(
        None, "--endpoint", "-e", help="HTTP endpoint URL"
    ),
    command: Optional[str] = typer.Option(
        None, "--command", "-c", help="stdio command (space-separated)"
    ),
    instance_id: Optional[str] = typer.Option(
        None, "--id", help="Instance ID (auto-generated if not provided)"
    ),
    transport: str = typer.Option(
        "http", "--transport", "-t", help="Transport type (http or stdio)"
    ),
    backend: str = typer.Option("docker", "--backend", "-b", help="Backend type"),
    registry_file: Optional[str] = typer.Option(
        None, "--registry", "-r", help="Path to registry file"
    ),
):
    """
    Manually register a server instance with the gateway.
    """
    # Default registry file location
    if not registry_file:
        registry_file = str(Path.home() / ".mcp" / "gateway_registry.json")

    try:
        from mcp_platform.gateway.registry import ServerInstance

        registry = ServerRegistry(registry_file)

        # Validate inputs
        if transport == "http" and not endpoint:
            console.print("[red]❌ HTTP transport requires --endpoint[/red]")
            raise typer.Exit(1)

        if transport == "stdio" and not command:
            console.print("[red]❌ stdio transport requires --command[/red]")
            raise typer.Exit(1)

        # Generate instance ID if not provided
        if not instance_id:
            import time

            instance_id = f"{template_name}-{int(time.time())}"

        # Create server instance
        instance = ServerInstance(
            id=instance_id,
            template_name=template_name,
            endpoint=endpoint,
            command=command.split() if command else None,
            transport=transport,
            backend=backend,
            status="unknown",
        )

        # Register with gateway
        registry.register_server(template_name, instance)

        console.print(
            f"[green]✓[/green] Registered instance [cyan]{instance_id}[/cyan] "
            f"for template [yellow]{template_name}[/yellow]"
        )

        # Show instance details
        details_table = Table(title="Registered Instance")
        details_table.add_column("Property", style="cyan")
        details_table.add_column("Value", style="white")

        details_table.add_row("Instance ID", instance_id)
        details_table.add_row("Template", template_name)
        details_table.add_row("Transport", transport)
        details_table.add_row("Backend", backend)

        if endpoint:
            details_table.add_row("Endpoint", endpoint)
        if command:
            details_table.add_row("Command", command)

        console.print(details_table)

    except Exception as e:
        console.print(f"[red]❌ Failed to register server: {e}[/red]")
        raise typer.Exit(1)


@gateway_app.command("deregister")
def deregister_server(
    template_name: str = typer.Argument(..., help="Template name"),
    instance_id: str = typer.Argument(..., help="Instance ID to deregister"),
    registry_file: Optional[str] = typer.Option(
        None, "--registry", "-r", help="Path to registry file"
    ),
):
    """
    Deregister a server instance from the gateway.
    """
    # Default registry file location
    if not registry_file:
        registry_file = str(Path.home() / ".mcp" / "gateway_registry.json")

    try:
        registry = ServerRegistry(registry_file)

        # Check if instance exists
        instance = registry.get_instance(template_name, instance_id)
        if not instance:
            console.print(
                f"[red]❌ Instance [cyan]{instance_id}[/cyan] not found "
                f"in template [yellow]{template_name}[/yellow][/red]"
            )
            raise typer.Exit(1)

        # Deregister
        success = registry.deregister_server(template_name, instance_id)

        if success:
            console.print(
                f"[green]✓[/green] Deregistered instance [cyan]{instance_id}[/cyan] "
                f"from template [yellow]{template_name}[/yellow]"
            )
        else:
            console.print(
                f"[red]❌ Failed to deregister instance [cyan]{instance_id}[/cyan][/red]"
            )
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]❌ Failed to deregister server: {e}[/red]")
        raise typer.Exit(1)


@gateway_app.command("cleanup")
def cleanup_registry(
    registry_file: Optional[str] = typer.Option(
        None, "--registry", "-r", help="Path to registry file"
    ),
    max_failures: int = typer.Option(
        5, "--max-failures", help="Max consecutive failures before removal"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Show what would be removed without actually removing"
    ),
):
    """
    Clean up unhealthy instances from the gateway registry.

    Removes instances that have exceeded the maximum number of consecutive health check failures.
    """
    # Default registry file location
    if not registry_file:
        registry_file = str(Path.home() / ".mcp" / "gateway_registry.json")

    try:
        registry = ServerRegistry(registry_file)

        # Get instances that would be removed
        instances_to_remove = []
        for template_name, template in registry.templates.items():
            for instance in template.instances:
                if instance.consecutive_failures >= max_failures:
                    instances_to_remove.append((template_name, instance))

        if not instances_to_remove:
            console.print("[green]✓[/green] No unhealthy instances found to clean up")
            return

        # Show what will be removed
        cleanup_table = Table(
            title=f"Instances to {'Remove' if not dry_run else 'Remove (Dry Run)'}"
        )
        cleanup_table.add_column("Instance ID", style="cyan")
        cleanup_table.add_column("Template", style="yellow")
        cleanup_table.add_column("Failures", style="red")
        cleanup_table.add_column("Status", style="white")

        for template_name, instance in instances_to_remove:
            cleanup_table.add_row(
                instance.id,
                template_name,
                str(instance.consecutive_failures),
                instance.status,
            )

        console.print(cleanup_table)

        if dry_run:
            console.print(
                f"[blue]Would remove {len(instances_to_remove)} unhealthy instances[/blue]"
            )
        else:
            # Confirm removal
            if len(instances_to_remove) > 0:
                confirm = typer.confirm(
                    f"Remove {len(instances_to_remove)} unhealthy instances?"
                )
                if not confirm:
                    console.print("[yellow]Cleanup cancelled[/yellow]")
                    return

            # Perform cleanup
            removed_count = registry.clear_unhealthy_instances(max_failures)

            console.print(
                f"[green]✓[/green] Removed {removed_count} unhealthy instances"
            )

    except Exception as e:
        console.print(f"[red]❌ Failed to cleanup registry: {e}[/red]")
        raise typer.Exit(1)
