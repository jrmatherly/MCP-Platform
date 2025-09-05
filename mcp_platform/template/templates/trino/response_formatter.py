#!/usr/bin/env python3
"""
Trino response formatter for the Trino template.

Provides a TrinoResponseFormatter class that knows how to parse and render
common Trino tool outputs (catalogs, schemas, tables, describe_table, query
results, status) using rich tables and panels.
"""

import json
import logging
from typing import Any, Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

logger = logging.getLogger(__name__)


class TrinoResponseFormatter:
    """Formatter for Trino tool responses."""

    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()

    def format_tool_response(self, tool_name: str, raw_response: str) -> None:
        """Entry point called by the generic ResponseFormatter.

        Args:
            tool_name: tool that produced the response
            raw_response: raw string payload (often JSON or newline-delimited)
        """
        try:
            if tool_name == "list_catalogs":
                self._format_list_catalogs(raw_response)
            elif tool_name == "list_schemas":
                self._format_list_schemas(raw_response)
            elif tool_name == "list_tables":
                self._format_list_tables(raw_response)
            elif tool_name == "describe_table":
                self._format_describe_table(raw_response)
            elif tool_name == "execute_query":
                self._format_execute_query(raw_response)
            elif tool_name in ("get_query_status", "cancel_query"):
                self._format_query_status(raw_response, tool_name)
            elif tool_name == "get_cluster_info":
                self._format_cluster_info(raw_response)
            else:
                self._format_default(raw_response)
        except Exception as e:
            logger.warning("Trino formatter failed for %s: %s", tool_name, e)
            self._format_default(raw_response)

    def _clean(self, text: str) -> str:
        if not text:
            return ""
        text = text.strip()
        # Remove outer JSON string quoting if present
        if text.startswith('"') and text.endswith('"'):
            try:
                text = json.loads(text)
            except Exception:
                text = text[1:-1]
        return text

    def _parse_json(self, text: str) -> Optional[Any]:
        try:
            return json.loads(text)
        except Exception:
            return None

    def _format_list_catalogs(self, response: str) -> None:
        text = self._clean(response)
        data = self._parse_json(text)

        # Accept either JSON with key 'catalogs' or a simple list/lines
        catalogs = []
        message = None
        if isinstance(data, dict) and "catalogs" in data:
            catalogs = data.get("catalogs") or []
            message = data.get("message")
        elif isinstance(data, list):
            catalogs = data
        else:
            # Fallback: split lines
            lines = [line.strip() for line in text.splitlines() if line.strip()]
            catalogs = lines

        if not catalogs:
            self.console.print("[yellow]No catalogs found[/yellow]")
            return

        # Simple column list
        table = Table(title=f"Trino Catalogs ({len(catalogs)})", show_header=True)
        table.add_column("#", style="cyan", width=4)
        table.add_column("Catalog", style="yellow")

        for i, c in enumerate(catalogs, 1):
            table.add_row(str(i), str(c))

        self.console.print(table)
        if message:
            self.console.print(Panel(message, title="Info", border_style="dim"))

    def _format_list_schemas(self, response: str) -> None:
        text = self._clean(response)
        data = self._parse_json(text)

        schemas = []
        if isinstance(data, dict) and "schemas" in data:
            schemas = data.get("schemas") or []
        elif isinstance(data, list):
            schemas = data
        else:
            schemas = [line.strip() for line in text.splitlines() if line.strip()]

        if not schemas:
            self.console.print("[yellow]No schemas found[/yellow]")
            return

        table = Table(title=f"Schemas ({len(schemas)})", show_header=True)
        table.add_column("#", style="cyan", width=4)
        table.add_column("Schema", style="green")

        for i, s in enumerate(schemas, 1):
            table.add_row(str(i), str(s))

        self.console.print(table)

    def _format_list_tables(self, response: str) -> None:
        text = self._clean(response)
        data = self._parse_json(text)

        tables = []
        # Accept list of table names or list of dicts like {"table":..., "schema":...}
        if isinstance(data, dict) and "tables" in data:
            tables = data.get("tables") or []
        elif isinstance(data, list):
            tables = data
        else:
            tables = [line.strip() for line in text.splitlines() if line.strip()]

        if not tables:
            self.console.print("[yellow]No tables found[/yellow]")
            return

        # Normalize to list of dicts
        rows = []
        for t in tables:
            if isinstance(t, dict):
                rows.append(t)
            else:
                # Try to split 'schema.table' or 'table' strings
                if "." in str(t):
                    schema, table_name = str(t).split(".", 1)
                    rows.append({"schema": schema, "table": table_name})
                else:
                    rows.append({"table": str(t)})

        table = Table(title=f"Tables ({len(rows)})", show_header=True)
        table.add_column("#", style="cyan", width=4)
        # Determine columns to show
        cols = [k for k in ("schema", "table") if any(k in r for r in rows)]
        for c in cols:
            table.add_column(c.title(), style="yellow")

        for i, r in enumerate(rows, 1):
            values = [str(r.get(c, "")) for c in cols]
            table.add_row(str(i), *values)

        self.console.print(table)

    def _format_describe_table(self, response: str) -> None:
        text = self._clean(response)
        data = self._parse_json(text)

        # Expect either a list of column dicts or a dict with 'columns' key
        columns = []
        if isinstance(data, dict) and "columns" in data:
            columns = data.get("columns") or []
        elif isinstance(data, list):
            columns = data
        else:
            # Try to parse lines like 'col_name | type | comment'
            lines = [line for line in text.splitlines() if line.strip()]
            for ln in lines:
                parts = [p.strip() for p in ln.split("|")]
                if len(parts) >= 2:
                    columns.append(
                        {
                            "column": parts[0],
                            "type": parts[1],
                            "comment": parts[2] if len(parts) > 2 else "",
                        }
                    )

        if not columns:
            self.console.print("[yellow]No schema information available[/yellow]")
            return

        tbl = Table(title=f"Table Schema ({len(columns)} columns)", show_header=True)
        tbl.add_column("#", style="cyan", width=4)
        tbl.add_column("Column", style="yellow")
        tbl.add_column("Type", style="green")
        tbl.add_column("Nullable", style="magenta", width=8)
        tbl.add_column("Comment", style="white", overflow="ellipsis")

        for i, col in enumerate(columns, 1):
            name = col.get("column") or col.get("name") or col.get("field") or ""
            ctype = col.get("type") or col.get("datatype") or ""
            nullable = str(col.get("nullable", ""))
            comment = col.get("comment", "")
            tbl.add_row(str(i), name, ctype, nullable, comment)

        self.console.print(tbl)

    def _format_execute_query(self, response: str) -> None:
        text = self._clean(response)
        data = self._parse_json(text)

        # Accept structures like {"rows": [...], "columns": [...] } or a plain list of dicts
        rows = None
        columns = None
        if isinstance(data, dict):
            if "rows" in data and isinstance(data["rows"], list):
                rows = data["rows"]
            elif "results" in data and isinstance(data["results"], list):
                rows = data["results"]
            elif "structuredContent" in data and isinstance(
                data["structuredContent"], dict
            ):
                sc = data["structuredContent"]
                if isinstance(sc.get("rows"), list):
                    rows = sc.get("rows")
                elif isinstance(sc.get("results"), list):
                    rows = sc.get("results")
            # Column metadata if provided
            if "columns" in data and isinstance(data["columns"], list):
                columns = data["columns"]

        elif isinstance(data, list):
            # List of records
            rows = data

        # Fallback: try to parse newline-delimited JSON
        if rows is None:
            rows = []
            for ln in text.splitlines():
                ln = ln.strip()
                if not ln:
                    continue
                parsed = self._parse_json(ln)
                if isinstance(parsed, dict):
                    rows.append(parsed)

        if not rows:
            # Show raw response
            self._format_default(response)
            return

        # If rows are list of lists with separate columns metadata, attempt to map
        if rows and isinstance(rows[0], list) and columns:
            # Map positional rows to dicts using columns names
            headers = [
                c.get("name") if isinstance(c, dict) else str(c) for c in columns
            ]
            mapped = []
            for r in rows:
                mapped.append(
                    {
                        headers[i]: r[i] if i < len(r) else None
                        for i in range(len(headers))
                    }
                )
            rows = mapped

        # If rows are list of lists and no columns, create numeric headers
        if rows and isinstance(rows[0], list) and not columns:
            headers = [f"col_{i}" for i in range(len(rows[0]))]
            mapped = [
                {headers[i]: r[i] if i < len(r) else None for i in range(len(headers))}
                for r in rows
            ]
            rows = mapped

        # Now rows should be list of dicts
        if isinstance(rows, list) and rows and isinstance(rows[0], dict):
            # Build table headers from union of keys (preserve order from first row)
            headers = list(rows[0].keys())
            tbl = Table(
                title=f"Query Results ({len(rows)} rows)",
                show_header=True,
                header_style="bold cyan",
            )
            for h in headers:
                tbl.add_column(h.replace("_", " ").title(), style="white")

            max_rows = 50
            for r in rows[:max_rows]:
                row_vals = [self._format_cell(r.get(h)) for h in headers]
                tbl.add_row(*row_vals)

            if len(rows) > max_rows:
                tbl.caption = f"Showing {max_rows} of {len(rows)} rows"

            self.console.print(tbl)
            return

        # Fallback
        self._format_default(response)

    def _format_query_status(self, response: str, tool_name: str) -> None:
        text = self._clean(response)
        data = self._parse_json(text)

        if isinstance(data, dict):
            # Show key/value pairs
            tbl = Table(title=f"{tool_name} Status", show_header=False)
            tbl.add_column("Property", style="cyan", width=30)
            tbl.add_column("Value", style="white")
            for k, v in data.items():
                tbl.add_row(str(k), str(v))
            self.console.print(tbl)
            return

        # Fallback to panel
        self.console.print(
            Panel(text, title=f"{tool_name} Output", border_style="blue")
        )

    def _format_cluster_info(self, response: str) -> None:
        text = self._clean(response)
        data = self._parse_json(text)
        if isinstance(data, dict):
            # Present cluster summary
            info = {
                k: v for k, v in data.items() if isinstance(v, (str, int, float, bool))
            }
            tbl = Table(title="Cluster Info", show_header=False)
            tbl.add_column("Property", style="cyan", width=30)
            tbl.add_column("Value", style="white")
            for k, v in info.items():
                tbl.add_row(str(k), str(v))
            self.console.print(tbl)
            return

        self.console.print(Panel(text, title="Cluster Info", border_style="blue"))

    def _format_default(self, response: str) -> None:
        text = self._clean(response)
        # Try pretty JSON
        parsed = self._parse_json(text)
        if parsed is not None:
            try:
                pretty = json.dumps(parsed, indent=2, ensure_ascii=False)
                self.console.print(
                    Panel(pretty, title="Tool Response", border_style="blue")
                )
                return
            except Exception:
                pass

        self.console.print(
            Panel(text or "", title="Tool Response", border_style="blue")
        )

    def _format_cell(self, val: Any) -> str:
        if val is None:
            return "[dim]—[/dim]"
        if isinstance(val, bool):
            return "[green]✓[/green]" if val else "[red]✗[/red]"
        if isinstance(val, (int, float)):
            return str(val)
        if isinstance(val, str):
            return val if len(val) < 80 else val[:77] + "..."
        try:
            return str(val)
        except Exception:
            return ""
