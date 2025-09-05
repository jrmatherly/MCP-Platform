"""
Enhanced Interactive CLI using Typer for MCP Template management.

This module provides a modern interactive command-line interface built with Typer
that replaces the cmd2-based interactive CLI with:
- Dynamic argument handling using Typer
- Client-based operations for consistency with main CLI
- Better error handling and validation
- Rich formatting and user-friendly responses
- Session state management
- Command history with up/down arrow keys
- Tab completion for commands and template names
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Annotated, Any, Dict, List, Optional

try:
    import readline

    READLINE_AVAILABLE = True
except ImportError:
    READLINE_AVAILABLE = False

import shlex

import click
import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table
from typer.main import get_command as typer_get_command

from mcp_platform.client import MCPClient
from mcp_platform.core.cache import CacheManager
from mcp_platform.core.config_processor import ConfigProcessor
from mcp_platform.core.response_formatter import ResponseFormatter

console = Console()
logger = logging.getLogger(__name__)


# Selection/injection logic removed: commands must be called with an explicit template
# The previous implementation supported selecting a template for the session and
# auto-injecting it into commands; that feature has been removed to simplify the
# interactive CLI. Commands now require templates to be provided explicitly where
# applicable and provide clear error messages when omitted.


# Command completion setup
COMMANDS = [
    "help",
    "templates",
    "tools",
    "call",
    "configure",
    "show-config",
    "clear-config",
    "servers",
    "deploy",
    "logs",
    "stop",
    "status",
    "remove",
    "cleanup",
    "exit",
    "quit",
]


def setup_completion():
    """Setup readline completion if available."""
    if not READLINE_AVAILABLE:
        return

    def completer(text, state):
        """Custom completer for interactive CLI."""
        try:
            options = []

            # Get current line and split into parts
            line = readline.get_line_buffer()
            parts = line.split()

            if not parts or (len(parts) == 1 and not line.endswith(" ")):
                # Completing command
                options = [cmd for cmd in COMMANDS if cmd.startswith(text)]
            elif len(parts) >= 1:
                cmd = parts[0]
                if cmd in [
                    "tools",
                    "call",
                    "deploy",
                    "logs",
                    "stop",
                    "status",
                    "remove",
                ]:
                    # Try to complete template names
                    try:
                        session = get_session()
                        templates = session.client.list_templates()
                        options = [t for t in templates if t.startswith(text)]
                    except Exception:
                        options = []
                elif cmd == "configure":
                    # Basic config key completion
                    config_keys = ["backend", "timeout", "port", "host"]
                    options = [k for k in config_keys if k.startswith(text)]

            return options[state] if state < len(options) else None

        except (IndexError, AttributeError):
            return None

    # Setup readline
    readline.set_completer(completer)
    readline.parse_and_bind("tab: complete")
    # Enable history
    readline.parse_and_bind("set show-all-if-ambiguous on")

    # Try to load history from file
    history_file = os.path.expanduser("~/.mcp/.mcpp_history")
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(history_file), exist_ok=True)
        readline.read_history_file(history_file)
    except FileNotFoundError:
        pass  # No history file yet

    # Set history length
    readline.set_history_length(1000)

    return history_file


class InteractiveSession:
    """Manages interactive session state and configuration."""

    def __init__(self, backend_type: str = "docker"):
        self.backend_type = backend_type
        self.client = MCPClient(backend_type=backend_type)
        self.cache = CacheManager()
        self.formatter = ResponseFormatter()

        # Session configuration storage
        self.session_configs: Dict[str, Dict[str, Any]] = {}

        # Template selection state
        self.selected_template: Optional[str] = None

        # Load cached configurations
        self._load_cached_configs()

    def _load_cached_configs(self):
        """Load previously cached template configurations."""
        try:
            cached_configs = self.cache.get("interactive_session_configs")
            self.session_configs.update(cached_configs)
        except Exception:
            # Cache errors are non-fatal
            pass

    def _save_cached_configs(self):
        """Save current configurations to cache."""
        try:
            self.cache.set("interactive_session_configs", self.session_configs)
        except Exception:
            # Cache errors are non-fatal
            pass

    def get_template_config(self, template_name: str) -> Dict[str, Any]:
        """Get configuration for a template."""
        return self.session_configs.get(template_name, {})

    def update_template_config(self, template_name: str, config: Dict[str, Any]):
        """Update configuration for a template."""
        if template_name not in self.session_configs:
            self.session_configs[template_name] = {}
        self.session_configs[template_name].update(config)
        self._save_cached_configs()

    def clear_template_config(self, template_name: str):
        """Clear configuration for a template."""
        if template_name in self.session_configs:
            del self.session_configs[template_name]
            self._save_cached_configs()

    def select_template(self, template_name: str) -> bool:
        """Select a template for the session."""
        try:
            templates = self.client.list_templates()
            if template_name in templates:
                self.selected_template = template_name
                console.print(f"[green]✅ Selected template: {template_name}[/green]")
                return True
            else:
                console.print(f"[red]❌ Template '{template_name}' not found[/red]")
                return False
        except Exception as e:
            console.print(f"[red]❌ Error selecting template: {e}[/red]")
            return False

    def unselect_template(self):
        """Unselect the current template."""
        if self.selected_template:
            console.print(
                f"[yellow]📤 Unselected template: {self.selected_template}[/yellow]"
            )
            self.selected_template = None
        else:
            console.print("[yellow]⚠️ No template currently selected[/yellow]")

    def get_selected_template(self) -> Optional[str]:
        """Get the currently selected template."""
        return self.selected_template

    def get_prompt(self) -> str:
        """Get the interactive prompt based on current state."""
        if self.selected_template:
            return f"mcpp({self.selected_template})> "
        return "mcpp> "


# Global session instance
session = None


def get_session() -> InteractiveSession:
    """Get or create the interactive session."""
    global session
    if session is None:
        backend = os.getenv("MCP_BACKEND", "docker")
        session = InteractiveSession(backend_type=backend)
    # Environment-based template selection is no longer supported.
    return session


# Create Typer app for interactive commands
app = typer.Typer(
    name="mcpp-interactive",
    help="MCP Interactive CLI - Enhanced shell for MCP operations",
    rich_markup_mode="rich",
    add_completion=False,  # Disable completion in interactive mode
)


@app.callback()
def app_callback(
    backend: Annotated[
        str, typer.Option("--backend", help="Backend type to use")
    ] = "docker",
    verbose: Annotated[
        bool, typer.Option("--verbose", "-v", help="Enable verbose output")
    ] = False,
):
    """Interactive MCP CLI with dynamic command handling."""
    global session
    # Create session only if missing. Do NOT recreate an existing session
    # here — Typer may call this callback for every command and recreating
    # the session would drop selection/state unexpectedly.
    if session is None:
        session = InteractiveSession(backend_type=backend)
        # Restore selection from environment if present
        try:
            env_sel = os.environ.get("MCP_SELECTED_TEMPLATE")
            if env_sel:
                session.selected_template = env_sel
        except Exception:
            pass

    if verbose:
        logging.basicConfig(level=logging.DEBUG)
        console.print(f"[dim]Using backend: {backend}[/dim]")


@app.command(name="templates")
def list_templates(
    include_status: Annotated[
        bool, typer.Option("--status", help="Include deployment status")
    ] = False,
    all_backends: Annotated[
        bool, typer.Option("--all-backends", help="Check all backends")
    ] = False,
):
    """List available MCP server templates."""
    try:
        # Import and use the main CLI function to avoid duplication
        from mcp_platform.cli import list as cli_list

        # Call the main CLI function with the same parameters
        # Convert to the format the main CLI expects
        deployed_only = include_status
        backend = None if all_backends else os.getenv("MCP_BACKEND", "docker")
        output_format = "table"

        cli_list(
            deployed_only=deployed_only, backend=backend, output_format=output_format
        )

    except Exception as e:
        console.print(f"[red]❌ Error listing templates: {e}[/red]")


@app.command(name="tools")
def list_tools(
    template: Annotated[
        Optional[str],
        typer.Argument(help="Template name (optional if template is selected)"),
    ],
    force_refresh: Annotated[
        bool, typer.Option("--force-refresh", help="Force refresh cache")
    ] = False,
    show_help: Annotated[
        bool, typer.Option("--help-info", help="Show detailed help for tools")
    ] = False,
):
    """List available tools for a template."""
    try:
        # Commands now require explicit template names.
        if not template:
            console.print(
                "[red]❌ No template specified. Provide the template name as the first argument.[/red]"
            )
            return
        # Import and use the main CLI function to avoid duplication
        from mcp_platform.cli import list_tools as cli_list_tools

        # Call the main CLI function with the same parameters
        backend = os.getenv("MCP_BACKEND", "docker")
        output_format = "table"

        cli_list_tools(
            template=template,
            backend=backend,
            force_refresh=force_refresh,
            static=True,
            dynamic=True,
            output_format=output_format,
        )

        if show_help:
            _show_template_help(template, [])  # Simplified for now

    except Exception as e:
        console.print(f"[red]❌ Error listing tools: {e}[/red]")


@app.command(name="call")
def call_tool(
    template: Annotated[
        Optional[str],
        typer.Argument(help="Template name (optional if template is selected)"),
    ],
    tool_name: Annotated[Optional[str], typer.Argument(help="Tool name")],
    args: Annotated[
        Optional[str], typer.Argument(help="JSON arguments for the tool")
    ] = "{}",
    config_file: Annotated[
        Optional[Path], typer.Option("--config-file", "-f", help="Path to config file")
    ] = None,
    env: Annotated[
        Optional[List[str]],
        typer.Option("--env", "-e", help="Environment variables (KEY=VALUE)"),
    ] = None,
    config: Annotated[
        Optional[List[str]],
        typer.Option("--config", "-C", "-c", help="Config overrides (KEY=VALUE)"),
    ] = None,
    backend: Annotated[
        Optional[str],
        typer.Option(
            "--backend", "-b", help="Specific backend to use (docker, kubernetes, mock)"
        ),
    ] = None,
    no_pull: Annotated[
        bool, typer.Option("--no-pull", "-np", help="Don't pull Docker images")
    ] = False,
    raw: Annotated[
        bool, typer.Option("--raw", "-R", help="Show raw JSON response")
    ] = False,
    force_stdio: Annotated[
        bool, typer.Option("--stdio", help="Force stdio transport")
    ] = False,
):
    """Call a tool from a template."""

    try:
        # session is still required for later operations (template validation, config merging)
        session = globals().get("session") or get_session()

        # Template is required for the call command
        if not template:
            console.print(
                "[red]❌ No template specified. Provide the template name as the first argument.[/red]"
            )
            return

        # Handle tool name requirement
        if tool_name is None:
            console.print(
                "[red]❌ Tool name is required. Usage: call [template] <tool_name> [args][/red]"
            )
            return

        # Validate template exists
        templates = session.client.list_templates()
        if template not in templates:
            console.print(f"[red]❌ Template '{template}' not found[/red]")
            return

        # Parse JSON arguments
        try:
            tool_args = json.loads(args) if args else {}
        except json.JSONDecodeError as e:
            console.print(f"[red]❌ Invalid JSON arguments: {e}[/red]")
            return

        # Parse environment variables
        env_vars = {}
        if env:
            for env_var in env:
                if "=" in env_var:
                    key, value = env_var.split("=", 1)
                    env_vars[key] = value
                else:
                    console.print(
                        f"[yellow]⚠️  Ignoring invalid env var: {env_var}[/yellow]"
                    )

        # Parse config overrides
        config_overrides = {}
        if config:
            for config_var in config:
                if "=" in config_var:
                    key, value = config_var.split("=", 1)
                    config_overrides[key] = value
                else:
                    console.print(
                        f"[yellow]⚠️  Ignoring invalid config: {config_var}[/yellow]"
                    )

        # Merge with session config
        session_config = session.get_template_config(template)
        # Ensure session_config is a dict-like object; guard against mocked sessions
        if not isinstance(session_config, dict):
            try:
                session_config = dict(session_config)
            except Exception:
                session_config = {}
        final_config = {**session_config, **config_overrides}

        console.print(
            f"\n[cyan]🚀 Calling tool '{tool_name}' from template '{template}'[/cyan]"
        )

        # Check for missing required configuration
        template_info = session.client.get_template_info(
            template, include_deployed_status=True
        )
        if (
            template_info and not template_info.get("deployment_count", None)
        ) or force_stdio:
            missing_config = _check_missing_config(
                template_info,
                final_config,
                env_vars,
                config_file=str(config_file) if config_file else None,
            )
            if missing_config:
                console.print(
                    f"[yellow]⚠️  Missing required configuration: {', '.join(missing_config)}[/yellow]"
                )

                if Confirm.ask("Would you like to set the missing configuration now?"):
                    new_config = _prompt_for_config(template_info, missing_config)
                    final_config.update(new_config)
                    session.update_template_config(template, new_config)
                else:
                    console.print(
                        "[yellow]Cannot proceed without required configuration[/yellow]"
                    )
                    return

        # Call the tool
        result = session.client.call_tool_with_config(
            template_id=template,
            tool_name=tool_name,
            arguments=tool_args,
            config_file=str(config_file) if config_file else None,
            env_vars=env_vars,
            config_values=final_config,
            all_backends=not backend,
            pull_image=not no_pull,
            force_stdio=force_stdio,
        )
        # Display result
        if result and result.get("success"):
            if raw:
                console.print(json.dumps(result, indent=2))
            else:
                session.formatter.beautify_tool_response(result, template, tool_name)
                # _display_tool_result(result.get("result"), tool_name, raw=False)

                # Show additional info if available
                if result.get("backend_type"):
                    console.print(
                        f"[dim]Used backend: {result.get('backend_type')}[/dim]"
                    )
                if result.get("deployment_id"):
                    console.print(
                        f"[dim]Used deployment: {result.get('deployment_id')}[/dim]"
                    )
        else:
            error_msg = (
                result.get("error", "Tool execution failed")
                if result
                else "Tool execution failed"
            )
            console.print(f"[red]❌ Tool execution failed: {error_msg}[/red]")

            # Show helpful deploy command if template is not deployed and doesn't support stdio
            if result and not result.get("template_supports_stdio", True):
                deploy_cmd = result.get("deploy_command")
                if deploy_cmd:
                    console.print(
                        f"[yellow]💡 Try deploying first: {deploy_cmd}[/yellow]"
                    )

            # Show backend info if available
            if result and result.get("backend_type"):
                console.print(f"[dim]Backend used: {result.get('backend_type')}[/dim]")

    except Exception as e:
        console.print(f"[red]❌ Failed to execute tool: {e}[/red]")


@app.command(name="configure")
def configure_template(
    template: Annotated[
        Optional[str],
        typer.Argument(help="Template name (optional if template is selected)"),
    ],
    config_pairs: Annotated[
        Optional[List[str]], typer.Argument(help="Configuration KEY=VALUE pairs")
    ] = None,
):
    """Configure a template with key=value pairs."""
    try:
        session = globals().get("session") or get_session()

        if not template:
            console.print(
                "[red]❌ No template specified. Provide the template name as the first argument.[/red]"
            )
            return

        # Handle config pairs requirement
        if not config_pairs:
            console.print(
                "[red]❌ Configuration KEY=VALUE pairs are required. Usage: configure [template] key=value ...[/red]"
            )
            return

        # Validate template exists
        templates = session.client.list_templates()
        if template not in templates:
            console.print(f"[red]❌ Template '{template}' not found[/red]")
            return

        # Parse config pairs
        config_values = {}
        for pair in config_pairs:
            if "=" in pair:
                key, value = pair.split("=", 1)
                config_values[key] = value
            else:
                console.print(
                    f"[yellow]⚠️  Ignoring invalid config pair: {pair}[/yellow]"
                )

        if not config_values:
            console.print("[red]❌ No valid configuration pairs provided[/red]")
            return

        # Update session config
        session.update_template_config(template, config_values)

        console.print(
            f"[green]✅ Configuration saved for template '{template}'[/green]"
        )

        # Display current config
        show_config(template)

    except Exception as e:
        console.print(f"[red]❌ Error configuring template: {e}[/red]")


@app.command(name="show-config")
def show_config(
    template: Annotated[
        Optional[str],
        typer.Argument(help="Template name (optional if template is selected)"),
    ],
):
    """Show current configuration for a template with all available properties."""
    try:
        session = globals().get("session") or get_session()

        if not template:
            console.print(
                "[red]❌ No template specified. Provide the template name as the first argument.[/red]"
            )
            return

        # Get template info to understand schema
        template_info = session.client.get_template_info(template)
        if not template_info:
            console.print(f"[red]❌ Could not get template info for '{template}'[/red]")
            return

        config_schema = template_info.get("config_schema", {})
        properties = config_schema.get("properties", {})
        required_props = config_schema.get("required", [])

        # Get current configuration values
        current_config = session.get_template_config(template)

        if not properties:
            console.print(
                f"[yellow]Template '{template}' has no configurable properties[/yellow]"
            )
            return

        # Create enhanced table
        table = Table(title=f"Configuration for {template}")
        table.add_column("Property", style="cyan", width=20)
        table.add_column("Status", style="bold", width=12)
        table.add_column("Current Value", style="yellow", width=25)
        table.add_column("Type", style="blue", width=10)
        table.add_column("Description", style="white", width=40)
        table.add_column("Default", style="magenta", width=30)
        table.add_column("Options", style="magenta", width=30)

        # Enhanced status determination with conditional requirements
        # Use centralized validator (static schema-level helpers)
        validation_result = ConfigProcessor.validate_config_schema(
            config_schema, current_config
        )
        conditional_issues = validation_result.get("conditional_issues", [])
        suggestions = validation_result.get("suggestions", [])

        for prop_name, prop_info in properties.items():
            # Determine status with enhanced conditional logic
            is_basic_required = prop_name in required_props
            has_value = prop_name in current_config

            # Check if this property is conditionally required
            is_conditionally_required = ConfigProcessor.is_conditionally_required(
                prop_name, config_schema, current_config
            )

            if has_value:
                status = "[green]✅ SET[/green]"
            else:
                if is_basic_required:
                    status = "[red]❌ REQUIRED[/red]"
                elif is_conditionally_required:
                    status = "[yellow]⚠️ CONDITIONAL[/yellow]"
                else:
                    status = "[dim]⚪ OPTIONAL[/dim]"

            # Get current value with masking for sensitive data
            if has_value:
                current_value = current_config[prop_name]
                # Mask sensitive values
                if any(
                    sensitive in prop_name.lower()
                    for sensitive in ["token", "key", "secret", "password"]
                ):
                    display_value = "***"
                else:
                    display_value = str(current_value)
            else:
                # Check if there's a default value
                default_value = prop_info.get("default")
                if default_value is not None:
                    display_value = f"[dim](default: {default_value})[/dim]"
                else:
                    display_value = "[dim]<not set>[/dim]"

            # Get property type
            prop_type = prop_info.get("type", "unknown")
            default_value = str(prop_info.get("default", ""))

            # Get description
            description = prop_info.get("description", "No description available")
            options = prop_info.get(
                "enum", prop_info.get("options", prop_info.get("choices", []))
            )

            table.add_row(
                prop_name,
                status,
                display_value,
                prop_type,
                description,
                default_value,
                ", ".join(options),
            )

        console.print(table)

        # Enhanced summary with conditional validation
        total_props = len(properties)
        set_props = len(current_config)
        required_count = len(required_props)
        missing_required = len([p for p in required_props if p not in current_config])

        console.print(
            f"\n[dim]Summary: {set_props}/{total_props} properties configured"
        )

        if missing_required > 0:
            console.print(
                f"[red]⚠️  {missing_required} required properties missing[/red]"
            )
        else:
            console.print(
                f"[green]✅ All {required_count} required properties are set[/green]"
            )

        # Show conditional validation results
        if not validation_result.get("valid", True):
            console.print("\n[yellow]⚠️ Conditional Requirements Status:[/yellow]")

            if conditional_issues:
                console.print(
                    "[red]❌ Configuration does not satisfy conditional requirements[/red]"
                )

            if suggestions:
                console.print("\n[cyan]💡 Suggestions:[/cyan]")
                for suggestion in suggestions:
                    console.print(f"  • {suggestion}")
        else:
            console.print("[green]✅ All conditional requirements satisfied[/green]")

    except Exception as e:
        console.print(f"[red]❌ Error showing config: {e}[/red]")


@app.command(name="clear-config")
def clear_config(
    template: Annotated[
        Optional[str],
        typer.Argument(help="Template name (optional if template is selected)"),
    ],
):
    """Clear configuration for a template."""
    try:
        session = globals().get("session") or get_session()

        # Handle template selection
        if template is None:
            template = session.get_selected_template()
            if template is None:
                console.print(
                    "[red]❌ No template specified and none selected. Use 'select <template>' first or provide template name.[/red]"
                )
                return

        session.clear_template_config(template)
        console.print(
            f"[green]✅ Configuration cleared for template '{template}'[/green]"
        )

    except Exception as e:
        console.print(f"[red]❌ Error clearing config: {e}[/red]")


@app.command(name="servers")
def list_servers(
    template: Annotated[
        Optional[str], typer.Option("--template", help="Filter by template")
    ],
    all_backends: Annotated[
        bool, typer.Option("--all-backends", help="Check all backends")
    ] = False,
):
    """List deployed MCP servers."""
    try:
        # Import and use the main CLI function to avoid duplication
        from mcp_platform.cli import list_deployments

        # Call the main CLI function with the same parameters
        backend = None if all_backends else os.getenv("MCP_BACKEND", "docker")
        output_format = "table"

        list_deployments(
            template=template,
            backend=backend,
            status="running",
            output_format=output_format,
            all_statuses=False,
        )

    except Exception as e:
        console.print(f"[red]❌ Error listing servers: {e}[/red]")


@app.command(name="deploy")
def deploy_template(
    template: Annotated[str, typer.Argument(help="Template name")],
    config_file: Annotated[
        Optional[Path], typer.Option("--config-file", "-c", help="Path to config file")
    ] = None,
    env: Annotated[
        Optional[List[str]],
        typer.Option("--env", "-e", help="Environment variables (KEY=VALUE)"),
    ] = None,
    config: Annotated[
        Optional[List[str]],
        typer.Option("--config", "-C", help="Config overrides (KEY=VALUE)"),
    ] = None,
    transport: Annotated[
        Optional[str], typer.Option("--transport", "-t", help="Transport protocol")
    ] = "http",
    port: Annotated[
        Optional[int], typer.Option("--port", "-p", help="Port for HTTP transport")
    ] = None,
    no_pull: Annotated[
        bool, typer.Option("--no-pull", help="Don't pull Docker images")
    ] = False,
):
    """Deploy a template as a server."""
    try:
        # Import and use the main CLI function to avoid duplication
        from mcp_platform.cli import deploy

        # Get session config for this template
        session = get_session()
        session_config = session.get_template_config(template)
        # Ensure session_config is a dict-like object; guard against mocked sessions
        if not isinstance(session_config, dict):
            try:
                session_config = dict(session_config)
            except Exception:
                session_config = {}

        # Merge session config with CLI config parameters
        merged_config = list(config) if config else []
        for key, value in session_config.items():
            merged_config.append(f"{key}={value}")

        # Call the main CLI deploy function
        deploy(
            template=template,
            config_file=config_file,
            config=merged_config if merged_config else None,
            env=env,
            override=None,  # Not used in interactive mode
            backend_config=None,
            backend_config_file=None,
            volumes=None,
            host="0.0.0.0",
            transport=transport,
            port=port,
            no_pull=no_pull,
            dry_run=False,
        )

    except Exception as e:
        console.print(f"[red]❌ Error deploying template: {e}[/red]")


# Template selection commands removed: interactive CLI requires explicit template names


@app.command(name="help")
def show_help(
    command: Annotated[
        Optional[str], typer.Argument(help="Show help for specific command")
    ] = None,
):
    """Show help information."""
    if command:
        # Show help for specific command
        try:
            # Typer stores commands as CommandInfo objects in app.registered_commands.
            # Build a lightweight click.Command around the callback to show help.
            cmd_info = next(
                (c for c in app.registered_commands if c.name == command), None
            )
            if cmd_info is None or not getattr(cmd_info, "callback", None):
                console.print(f"[red]Unknown command: {command}[/red]")
                return
            # Create a click.Command wrapper for the callback to render help text.
            click_cmd = click.Command(
                name=cmd_info.name, callback=cmd_info.callback, params=[]
            )
            cmd_ctx = click.Context(click_cmd, info_name=click_cmd.name)
            help_text = click_cmd.get_help(cmd_ctx)
            console.print(
                Panel(help_text, title=f"Help: {command}", border_style="blue")
            )
        except Exception:
            console.print(f"[red]Unknown command: {command}[/red]")
    else:
        # Show general help
        console.print(
            Panel(
                """
[cyan]Available Commands:[/cyan]

[yellow]Template Selection:[/yellow]
  • [bold]select[/bold] TEMPLATE  - Select a template for session (avoids repeating template name)
  • [bold]unselect[/bold]  - Unselect current template

[yellow]Template & Server Management:[/yellow]
  • [bold]templates[/bold] [--status] [--all-backends]  - List available templates
  • [bold]servers[/bold] [--template NAME] [--all-backends]  - List deployed servers
  • [bold]deploy[/bold] [TEMPLATE] [options]  - Deploy a template as server

[yellow]Tool Operations:[/yellow]
  • [bold]tools[/bold] [TEMPLATE] [--force-refresh] [--help-info]  - List tools for template
  • [bold]call[/bold] [TEMPLATE] TOOL [JSON_ARGS] [options]  - Call a tool
    [dim]Options: --config-file, --env KEY=VALUE, --config KEY=VALUE, --raw, --stdio[/dim]

[yellow]Server Operations:[/yellow]
  • [bold]logs[/bold] TARGET [--lines N]  - Get logs from deployment
  • [bold]stop[/bold] [TARGET] [--all] [--template NAME]  - Stop deployments
  • [bold]status[/bold] [--format FORMAT]  - Show backend health and deployments
  • [bold]remove[/bold] [TARGET] [--all] [--template NAME]  - Remove deployments
  • [bold]cleanup[/bold]  - Cleanup stopped containers

[yellow]Configuration Management:[/yellow]
  • [bold]configure[/bold] [TEMPLATE] KEY=VALUE [KEY2=VALUE2...]  - Set configuration
  • [bold]show-config[/bold] [TEMPLATE]  - Show current configuration
  • [bold]clear-config[/bold] [TEMPLATE]  - Clear configuration

[yellow]General:[/yellow]
  • [bold]help[/bold] [COMMAND]  - Show this help or help for specific command
  • [bold]exit[/bold] or Ctrl+C  - Exit interactive mode

[green]Examples with Template Selection:[/green]
  • [dim]select demo  # Select demo template[/dim]
  • [dim]tools  # List tools for selected template[/dim]
  • [dim]call say_hello '{"name": "Alice"}'  # Call tool without template name[/dim]
  • [dim]configure github_token=ghp_xxxx  # Configure selected template[/dim]
  • [dim]stop  # Stop selected template deployments[/dim]
  • [dim]logs  # Get logs for selected template[/dim]
  • [dim]unselect  # Unselect template[/dim]

[green]Traditional Examples:[/green]
  • [dim]templates --status[/dim]
  • [dim]configure github github_token=ghp_xxxx[/dim]
  • [dim]tools github --help-info[/dim]
  • [dim]call github search_repositories '{"query": "python"}'[/dim]
  • [dim]call --env API_KEY=xyz demo say_hello '{"name": "Alice"}'[/dim]
  • [dim]deploy demo --transport http --port 8080[/dim]
  • [dim]logs mcp-demo-12345 --lines 50[/dim]
  • [dim]stop --template demo[/dim]
""",
                title="MCP Interactive CLI Help",
                border_style="blue",
            )
        )


@app.command(name="logs")
def get_logs(
    target: Annotated[str, typer.Argument(help="Deployment ID or template name")],
    backend: Annotated[
        Optional[str],
        typer.Option("--backend", help="Specify backend if auto-detection fails"),
    ] = None,
    lines: Annotated[
        int, typer.Option("--lines", "-n", help="Number of log lines to retrieve")
    ] = 100,
):
    """Get logs from a running MCP server deployment."""
    try:
        # Import and use the main CLI function to avoid duplication
        from mcp_platform.cli import logs as cli_logs

        # Call the main CLI function with the same parameters
        cli_logs(target=target, backend=backend, lines=lines)

    except Exception as e:
        console.print(f"[red]❌ Error getting logs: {e}[/red]")


@app.command(name="stop")
def stop_server(
    target: Annotated[
        Optional[str],
        typer.Argument(
            help="Deployment ID, template name, or 'all' to stop deployments"
        ),
    ] = None,
    backend: Annotated[
        Optional[str],
        typer.Option("--backend", help="Specify backend if auto-detection fails"),
    ] = None,
    all: Annotated[
        bool, typer.Option("--all", help="Stop all running deployments")
    ] = False,
    template: Annotated[
        Optional[str],
        typer.Option("--template", help="Stop all deployments for a specific template"),
    ] = None,
    dry_run: Annotated[
        bool, typer.Option("--dry-run", help="Show what would be stopped")
    ] = False,
    timeout: Annotated[
        int, typer.Option("--timeout", help="Stop timeout in seconds")
    ] = 30,
    force: Annotated[
        bool, typer.Option("--force", help="Force stop without confirmation")
    ] = False,
):
    """Stop MCP server deployments."""
    try:
        # Require explicit target/template or use --all
        if target is None and not all and template is None:
            console.print(
                "[red]❌ Target required: deployment ID, template name, or use --all[/red]"
            )
            return

        # Import and use the main CLI function to avoid duplication
        from mcp_platform.cli import stop as cli_stop

        # Call the main CLI function with the same parameters
        cli_stop(
            target=target,
            backend=backend,
            all=all,
            template=template,
            dry_run=dry_run,
            timeout=timeout,
            force=force,
        )

    except Exception as e:
        console.print(f"[red]❌ Error stopping server: {e}[/red]")


@app.command(name="status")
def show_status(
    output_format: Annotated[
        str, typer.Option("--format", help="Output format: table, json, yaml")
    ] = "table",
):
    """Show backend health status and deployment summary."""
    try:
        # Import and use the main CLI function to avoid duplication
        from mcp_platform.cli import status as cli_status

        # Call the main CLI function with the same parameters
        cli_status(output_format=output_format)

    except Exception as e:
        console.print(f"[red]❌ Error getting status: {e}[/red]")


@app.command(name="remove")
def remove_server(
    target: Annotated[
        Optional[str],
        typer.Argument(help="Deployment ID or template name to remove"),
    ] = None,
    backend: Annotated[
        Optional[str],
        typer.Option("--backend", help="Specify backend if auto-detection fails"),
    ] = None,
    all: Annotated[bool, typer.Option("--all", help="Remove all deployments")] = False,
    template: Annotated[
        Optional[str],
        typer.Option(
            "--template", help="Remove all deployments for a specific template"
        ),
    ] = None,
    force: Annotated[
        bool, typer.Option("--force", help="Force removal without confirmation")
    ] = False,
):
    """Remove MCP server deployments."""
    try:
        # Require explicit target/template or use --all
        if target is None and not all and template is None:
            console.print(
                "[red]❌ Target required: deployment ID, template name, or use --all[/red]"
            )
            return

        # Import and use the main CLI function if it exists
        try:
            from mcp_platform.cli import stop as cli_remove

            cli_remove(
                target=target,
                backend=backend,
                all=all,
                template=template,
                force=force,
            )
        except ImportError:
            # Fallback implementation
            session = get_session()
            if all:
                result = session.client.stop_all_servers(force=force)
            elif template:
                result = session.client.stop_all_servers(template=template, force=force)
            else:
                result = session.client.stop_server(deployment_id=target)

            if result:
                console.print(
                    f"[green]✅ Successfully removed: {target or 'all'}[/green]"
                )
            else:
                console.print(f"[red]❌ Failed to remove: {target or 'all'}[/red]")

    except Exception as e:
        console.print(f"[red]❌ Error removing server: {e}[/red]")


@app.command(name="cleanup")
def cleanup_resources():
    """Cleanup stopped containers and unused resources."""
    session = get_session()
    result = asyncio.run(session.client.cleanup())
    if result:
        console.print("[green]✅ Cleanup completed successfully[/green]")
    else:
        console.print("[red]❌ Cleanup failed[/red]")


def _check_missing_config(
    template_info: Dict[str, Any],
    config: Dict[str, Any],
    env_vars: Dict[str, str],
    config_file: Optional[str] = None,
) -> List[str]:
    """Check for missing required configuration with conditional requirements support."""
    config_schema = template_info.get("config_schema", {})

    # Combine config and env_vars for validation
    effective_config = dict(config)
    properties = config_schema.get("properties", {})

    # Add env vars using their property mappings
    for prop_name, prop_info in properties.items():
        env_mapping = prop_info.get("env_mapping", prop_name.upper())
        if env_mapping in env_vars and prop_name not in effective_config:
            effective_config[prop_name] = env_vars[env_mapping]

    # Check for validation errors using centralized ConfigProcessor
    cp = ConfigProcessor()
    # Pass through the config_file so the ConfigProcessor can load and map
    # values from a YAML/JSON config file (e.g., secrets/trino.yaml).
    validation_result = cp.check_missing_config(
        template_info,
        effective_config,
        env_vars,
        config_file=config_file,
    )

    # Maintain backward-compatible return shape (list of missing props)
    return validation_result.missing_required


def _prompt_for_config(
    template_info: Dict[str, Any], missing_props: List[str]
) -> Dict[str, str]:
    """Prompt user for missing configuration values with intelligent conditional handling."""
    config_schema = template_info.get("config_schema", {})
    properties = config_schema.get("properties", {})

    new_config = {}

    # If we have conditional requirements, provide smart prompting
    if "anyOf" in config_schema or "oneOf" in config_schema:
        return _prompt_for_conditional_config(template_info, missing_props)

    # Fallback to simple prompting for basic schemas
    for prop in missing_props:
        prop_info = properties.get(prop, {})
        description = prop_info.get("description", f"Value for {prop}")

        # Check if it's a sensitive field
        is_sensitive = any(
            sensitive in prop.lower()
            for sensitive in ["token", "key", "secret", "password"]
        )

        if is_sensitive:
            value = Prompt.ask(f"[cyan]{description}[/cyan]", password=True)
        else:
            default = prop_info.get("default")
            value = Prompt.ask(f"[cyan]{description}[/cyan]", default=default)

        if value:
            new_config[prop] = value

    return new_config


def _prompt_for_conditional_config(
    template_info: Dict[str, Any], missing_props: List[str]
) -> Dict[str, str]:
    """Handle intelligent prompting for templates with conditional requirements."""
    config_schema = template_info.get("config_schema", {})
    properties = config_schema.get("properties", {})
    new_config = {}

    # Special handling for engine type templates
    if "engine_type" in properties:
        return _prompt_for_engine_config(template_info, missing_props)

    # Generic conditional prompting
    console.print(
        "[yellow]This template has conditional requirements. Let's configure it step by step.[/yellow]"
    )

    for prop in missing_props:
        prop_info = properties.get(prop, {})
        description = prop_info.get("description", f"Value for {prop}")

        is_sensitive = any(
            sensitive in prop.lower()
            for sensitive in ["token", "key", "secret", "password"]
        )

        if is_sensitive:
            value = Prompt.ask(f"[cyan]{description}[/cyan]", password=True)
        else:
            default = prop_info.get("default")
            if "enum" in prop_info:
                choices = prop_info["enum"]
                console.print(f"[dim]Available options: {', '.join(choices)}[/dim]")
            value = Prompt.ask(f"[cyan]{description}[/cyan]", default=default)

        if value:
            new_config[prop] = value

    return new_config


def _prompt_for_engine_config(
    template_info: Dict[str, Any], missing_props: List[str]
) -> Dict[str, str]:
    """Handle smart prompting for search engine templates (Elasticsearch/OpenSearch)."""
    config_schema = template_info.get("config_schema", {})
    properties = config_schema.get("properties", {})
    new_config = {}

    # First, determine the engine type
    engine_type = None
    if "engine_type" in properties:
        default_engine = properties["engine_type"].get("default", "elasticsearch")
        available_engines = properties["engine_type"].get(
            "enum", ["elasticsearch", "opensearch"]
        )

        console.print(
            "[cyan]🔍 Which search engine would you like to configure?[/cyan]"
        )
        for i, engine in enumerate(available_engines, 1):
            console.print(f"  {i}. {engine.title()}")

        while True:
            choice = Prompt.ask(
                f"[cyan]Choose engine type ({'/'.join(available_engines)})[/cyan]",
                default=default_engine,
            )
            if choice in available_engines:
                engine_type = choice
                new_config["engine_type"] = choice
                break
            else:
                console.print(
                    f"[red]Please choose from: {', '.join(available_engines)}[/red]"
                )

    # Configure based on engine type
    if engine_type == "elasticsearch":
        console.print("\n[cyan]📡 Configuring Elasticsearch connection...[/cyan]")

        # Hosts
        if "elasticsearch_hosts" not in new_config:
            hosts = Prompt.ask(
                "[cyan]Elasticsearch hosts (comma-separated)[/cyan]",
                default="https://localhost:9200",
            )
            if hosts:
                new_config["elasticsearch_hosts"] = hosts

        # Authentication method
        console.print("\n[cyan]🔐 Choose authentication method:[/cyan]")
        console.print("  1. API Key (recommended)")
        console.print("  2. Username & Password")

        auth_choice = Prompt.ask(
            "[cyan]Authentication method (1/2)[/cyan]", default="1"
        )

        if auth_choice == "1":
            api_key = Prompt.ask("[cyan]Elasticsearch API key[/cyan]", password=True)
            if api_key:
                new_config["elasticsearch_api_key"] = api_key
        else:
            username = Prompt.ask("[cyan]Elasticsearch username[/cyan]")
            if username:
                new_config["elasticsearch_username"] = username
            password = Prompt.ask("[cyan]Elasticsearch password[/cyan]", password=True)
            if password:
                new_config["elasticsearch_password"] = password

        # SSL verification
        verify_certs = Confirm.ask(
            "[cyan]Verify SSL certificates?[/cyan]", default=False
        )
        new_config["elasticsearch_verify_certs"] = verify_certs

    elif engine_type == "opensearch":
        console.print("\n[cyan]📡 Configuring OpenSearch connection...[/cyan]")

        # Hosts
        hosts = Prompt.ask(
            "[cyan]OpenSearch hosts (comma-separated)[/cyan]",
            default="https://localhost:9200",
        )
        if hosts:
            new_config["opensearch_hosts"] = hosts

        # Authentication (required for OpenSearch)
        username = Prompt.ask("[cyan]OpenSearch username[/cyan]")
        if username:
            new_config["opensearch_username"] = username

        password = Prompt.ask("[cyan]OpenSearch password[/cyan]", password=True)
        if password:
            new_config["opensearch_password"] = password

        # SSL verification
        verify_certs = Confirm.ask(
            "[cyan]Verify SSL certificates?[/cyan]", default=False
        )
        new_config["opensearch_verify_certs"] = verify_certs

    return new_config


def _show_template_help(template: str, tools: List[Dict[str, Any]]):
    """Show detailed help for a template and its tools."""
    console.print(f"\n[cyan]📖 Detailed Help for Template: {template}[/cyan]")

    for tool in tools:
        tool_name = tool.get("name", "Unknown")
        description = tool.get("description", "No description available")

        console.print(f"\n[yellow]🔧 {tool_name}[/yellow]")
        console.print(f"[dim]{description}[/dim]")

        # Show parameters if available
        parameters = tool.get("parameters", {})
        input_schema = tool.get("inputSchema", {})

        schema_to_use = parameters if parameters else input_schema
        if schema_to_use and "properties" in schema_to_use:
            props = schema_to_use["properties"]
            required = schema_to_use.get("required", [])

            if props:
                param_table = Table(title=f"Parameters for {tool_name}")
                param_table.add_column("Parameter", style="cyan")
                param_table.add_column("Type", style="yellow")
                param_table.add_column("Required", style="red")
                param_table.add_column("Description", style="white")

                for param, param_info in props.items():
                    param_type = param_info.get("type", "unknown")
                    is_required = "✓" if param in required else "✗"
                    param_desc = param_info.get("description", "No description")

                    param_table.add_row(param, param_type, is_required, param_desc)

                console.print(param_table)


def run_interactive_shell():
    """Run the interactive shell with command processing."""

    # Setup readline completion and history
    history_file = None
    if READLINE_AVAILABLE:
        history_file = setup_completion()
        console.print("[dim]✨ Command history and tab completion enabled[/dim]")
    else:
        console.print(
            "[dim]💡 Install readline for command history and tab completion[/dim]"
        )

    # Show welcome message
    console.print(
        Panel(
            """
[cyan]🚀 Welcome to MCP Interactive CLI v2[/cyan]

This is an enhanced interactive shell for managing MCP servers and calling tools.
Type [bold]help[/bold] for available commands or [bold]help COMMAND[/bold] for specific help.

[green]Quick Start:[/green]
• [dim]templates  # List available templates[/dim]
• [dim]select demo  # Select demo template for session[/dim]
• [dim]tools  # List tools for selected template[/dim]
• [dim]call say_hello '{"name": "Alice"}'  # Call a tool (no template needed)[/dim]
• [dim]unselect  # Unselect template[/dim]

[green]Template Selection:[/green]
• [dim]select <template>  # Select a template to avoid repeating in commands[/dim]
• [dim]unselect  # Unselect current template[/dim]

[yellow]Note:[/yellow] Use [bold]exit[/bold] or [bold]quit[/bold] to leave the interactive mode.
""",
            title="MCP Interactive CLI",
            border_style="blue",
        )
    )

    # Main interactive loop
    try:
        while True:
            try:
                # Get session for dynamic prompt and publish it to module global
                session = get_session()
                # No environment-based template selection; templates must be provided explicitly
                globals()["session"] = session
                prompt_text = session.get_prompt()

                # Use input() with prompt parameter to avoid Rich console conflicts
                if READLINE_AVAILABLE:
                    # With readline, use a simple prompt to avoid display issues
                    command = input(prompt_text).strip()
                else:
                    # Without readline, use Rich formatting
                    console.print(f"[bold blue]{prompt_text}[/bold blue]", end="")
                    command = input().strip()

                if not command:
                    continue

                if command in ["exit", "quit", "/q"]:
                    # Save command history before exiting
                    if READLINE_AVAILABLE and history_file:
                        try:
                            readline.write_history_file(history_file)
                        except:
                            pass  # Ignore history save errors
                    console.print("[yellow]Goodbye![/yellow]")
                    break

                # Parse and execute command using direct function calls
                try:
                    # Split command into args, respecting quoted strings
                    args = shlex.split(command)

                    if not args:
                        continue

                    cmd = args[0]
                    cmd_args = args[1:]

                    # Generic dispatch via Typer/Click to leverage automatic parsing
                    # and validation from the Typer command definitions.
                    if cmd == "help":
                        if cmd_args:
                            show_help(cmd_args[0])
                        else:
                            show_help()
                    else:
                        try:
                            # Build argv for Click/Typer: command + its args
                            argv = [cmd] + cmd_args

                            # Get the click.Command for this Typer app and let Click parse/validate
                            click_cmd = typer_get_command(app)

                            # If the command isn't registered, show a friendly unknown-command message
                            if cmd not in getattr(click_cmd, "commands", {}):
                                console.print(f"[red]❌ Unknown command: {cmd}[/red]")
                                continue

                            # Create a Click context which parses and validates argv
                            ctx = click_cmd.make_context(
                                info_name=(
                                    app.info.name
                                    if getattr(app, "info", None)
                                    else "mcpp"
                                ),
                                args=argv,
                            )

                            # Invoke the Click command (which will dispatch to the Typer callbacks)
                            click_cmd.invoke(ctx)

                        except click.ClickException as ce:
                            # Preserve the original user-facing error prints where possible
                            console.print(f"[red]❌ {ce.format_message()}[/red]")
                            try:
                                help_text = ce.format_message()
                                console.print(
                                    Panel(
                                        help_text,
                                        title=f"Help: {cmd}",
                                        border_style="blue",
                                    )
                                )
                            except Exception:
                                pass
                        except SystemExit:
                            # Click may call sys.exit for bad args; ignore to keep shell alive
                            pass
                        except Exception as e:
                            console.print(f"[red]❌ Error executing command: {e}[/red]")

                except Exception as e:
                    console.print(f"[red]❌ Error executing command: {e}[/red]")

            except KeyboardInterrupt:
                console.print(
                    "\n[yellow]Use 'exit' or 'quit' to leave the interactive shell[/yellow]"
                )
            except EOFError:
                # Save command history before exiting
                if READLINE_AVAILABLE and history_file:
                    try:
                        readline.write_history_file(history_file)
                    except:
                        pass  # Ignore history save errors
                console.print("\n[yellow]Goodbye![/yellow]")
                break

    except Exception as e:
        console.print(f"[red]❌ Fatal error in interactive shell: {e}[/red]")
        sys.exit(1)


def main():
    """Main entry point for standalone execution."""
    if len(sys.argv) > 1 and sys.argv[1] in ["--help", "-h"]:
        console.print("Enhanced MCP Interactive CLI")
        console.print("Usage: python -m mcp_platform.cli.interactive_cli_v2")
        console.print("       or: python interactive_cli_v2.py")
        return

    run_interactive_shell()


if __name__ == "__main__":
    main()
