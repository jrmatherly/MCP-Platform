#!/usr/bin/env python3
"""
Response formatter for Elasticsearch template.

This module provides custom response formatting for elasticsearch/opensearch tools
to display data in beautiful, structured tables instead of raw text.
"""

import json
import logging
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

logger = logging.getLogger(__name__)


class ElasticsearchResponseFormatter:
    """Custom response formatter for Elasticsearch tools."""

    def __init__(self, console: Optional[Console] = None):
        """Initialize the formatter."""
        self.console = console or Console()

    def format_tool_response(self, tool_name: str, raw_response: str) -> None:
        """
        Format tool response for display.

        Args:
            tool_name: Name of the tool that was called
            raw_response: Raw response string from the tool
        """
        try:
            # Handle different tool types
            if tool_name == "list_indices":
                self._format_list_indices(raw_response)
            elif tool_name == "get_index":
                self._format_get_index(raw_response)
            elif tool_name == "search":
                self._format_search_results(raw_response)
            else:
                # Default formatting for unknown tools
                self._format_default(raw_response)

        except Exception as e:
            logger.warning(f"Failed to format response for {tool_name}: {e}")
            # Fallback to default formatting
            self._format_default(raw_response)

    def _format_list_indices(self, response: str) -> None:
        """Format elasticsearch index listing."""
        # Clean the response (remove quotes if JSON-encoded)
        clean_response = self._clean_response_text(response)
        lines = [line.strip() for line in clean_response.split("\n") if line.strip()]

        if not lines:
            self.console.print("[yellow]No indices found[/yellow]")
            return

        # Parse elasticsearch index format
        indices = []
        for line in lines:
            parts = line.split()
            if len(parts) >= 9:  # Elasticsearch format has at least 9 columns
                indices.append(
                    {
                        "Health": parts[0],
                        "Status": parts[1],
                        "Index": parts[2],
                        "UUID": (
                            parts[3][:22] + "..." if len(parts[3]) > 25 else parts[3]
                        ),
                        "Primary": parts[4],
                        "Replica": parts[5],
                        "Docs": parts[6],
                        "Deleted": parts[7],
                        "Size": parts[8] if len(parts) > 8 else parts[7],
                    }
                )

        if indices:
            table = Table(
                title=f"Elasticsearch Indices ({len(indices)} found)",
                show_header=True,
                header_style="bold cyan",
            )
            table.add_column("Health", style="bold")
            table.add_column("Status", style="cyan")
            table.add_column("Index", style="yellow", width=20)
            table.add_column("UUID", style="dim")
            table.add_column("Primary", justify="right")
            table.add_column("Replica", justify="right")
            table.add_column("Docs", justify="right", style="green")
            table.add_column("Deleted", justify="right", style="red")
            table.add_column("Size", justify="right", style="blue")

            for index in indices:
                health_style = (
                    "green"
                    if index["Health"] == "green"
                    else "yellow" if index["Health"] == "yellow" else "red"
                )
                table.add_row(
                    f"[{health_style}]{index['Health']}[/{health_style}]",
                    index["Status"],
                    index["Index"],
                    index["UUID"],
                    index["Primary"],
                    index["Replica"],
                    index["Docs"],
                    index["Deleted"],
                    index["Size"],
                )

            self.console.print(table)
        else:
            self.console.print(
                Panel(
                    clean_response, title="Elasticsearch Response", border_style="blue"
                )
            )

    def _format_get_index(self, response: str) -> None:
        """Format index details."""
        try:
            # Try to parse as JSON
            data = json.loads(response)

            # Create a table for index details
            table = Table(
                title="Index Details", show_header=True, header_style="bold cyan"
            )
            table.add_column("Property", style="cyan", width=30)
            table.add_column("Value", style="white")

            for index_name, index_data in data.items():
                table.add_row("[bold]Index Name[/bold]", index_name)

                # Add settings
                if "settings" in index_data:
                    settings = index_data["settings"]
                    if "index" in settings:
                        index_settings = settings["index"]
                        for key, value in index_settings.items():
                            table.add_row(f"Setting: {key}", str(value))

                # Add mappings info
                if "mappings" in index_data:
                    mappings = index_data["mappings"]
                    if "properties" in mappings:
                        field_count = len(mappings["properties"])
                        table.add_row("Field Count", str(field_count))

                        # Show first few fields
                        for i, (field_name, field_info) in enumerate(
                            mappings["properties"].items()
                        ):
                            if i < 5:  # Show first 5 fields
                                field_type = field_info.get("type", "unknown")
                                table.add_row(f"Field: {field_name}", field_type)
                            elif i == 5:
                                table.add_row(
                                    "...", f"and {field_count - 5} more fields"
                                )
                                break

            self.console.print(table)

        except json.JSONDecodeError:
            self._format_default(response)

    def _format_search_results(self, response: str) -> None:
        """Format search results."""
        try:
            data = json.loads(response)

            if "hits" in data and "hits" in data["hits"]:
                hits = data["hits"]["hits"]
                total = data["hits"]["total"]

                # Summary panel
                total_value = total["value"] if isinstance(total, dict) else total
                self.console.print(
                    Panel(
                        f"Found {total_value} documents in {data.get('took', 0)}ms",
                        title="Search Results Summary",
                        border_style="green",
                    )
                )

                if hits:
                    # Create table for search results
                    table = Table(
                        title=f"Top {len(hits)} Results",
                        show_header=True,
                        header_style="bold cyan",
                    )
                    table.add_column("Score", justify="right", style="yellow")
                    table.add_column("Index", style="cyan")
                    table.add_column("ID", style="green")
                    table.add_column("Source", style="white", width=50)

                    for hit in hits:
                        source_preview = (
                            json.dumps(hit.get("_source", {}))[:100] + "..."
                            if len(json.dumps(hit.get("_source", {}))) > 100
                            else json.dumps(hit.get("_source", {}))
                        )

                        table.add_row(
                            f"{hit.get('_score', 0):.3f}",
                            hit.get("_index", ""),
                            hit.get("_id", ""),
                            source_preview,
                        )

                    self.console.print(table)
                else:
                    self.console.print("[yellow]No results found[/yellow]")
            else:
                self._format_default(response)

        except json.JSONDecodeError:
            self._format_default(response)

    def _format_default(self, response: str) -> None:
        """Default formatting - just display in a panel."""
        clean_response = self._clean_response_text(response)

        # Try to parse as JSON for pretty printing
        try:
            data = json.loads(clean_response)
            formatted_json = json.dumps(data, indent=2)
            self.console.print(
                Panel(formatted_json, title="Tool Response", border_style="blue")
            )
        except json.JSONDecodeError:
            # Display as plain text
            self.console.print(
                Panel(clean_response, title="Tool Response", border_style="blue")
            )

    def _clean_response_text(self, text: str) -> str:
        """Clean response text by removing JSON encoding artifacts."""
        if not text:
            return ""

        clean_text = text.strip()

        # Remove outer quotes if JSON-encoded
        if clean_text.startswith('"') and clean_text.endswith('"'):
            try:
                clean_text = json.loads(clean_text)
            except json.JSONDecodeError:
                # If JSON parsing fails, just remove outer quotes
                clean_text = clean_text[1:-1]

        return clean_text
