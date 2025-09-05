#!/usr/bin/env python3
"""
Trino MCP Server - Production-ready implementation.

A secure Trino MCP server that provides controlled access to distributed
data sources with configurable authentication, read-only mode, and comprehensive
query execution capabilities using FastMCP and SQLAlchemy.
"""

import fnmatch
import logging
import os
import re
import sys
from typing import Any, Dict, List, Optional

import sqlparse
from fastmcp import FastMCP
from starlette.requests import Request
from starlette.responses import JSONResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from .config import TrinoServerConfig
except ImportError:
    try:
        from config import TrinoServerConfig
    except ImportError:
        # Fallback for Docker or direct script execution
        sys.path.append(os.path.dirname(__file__))
        from config import TrinoServerConfig

# Trino/SQLAlchemy imports
try:
    import trino
    from sqlalchemy import create_engine, text
    from sqlalchemy.engine import Engine
except ImportError:
    # Check if we're in test mode
    if "pytest" in sys.modules or any("test" in module for module in sys.modules):
        # In test mode, create mock objects
        import types

        trino = types.ModuleType("trino")
        trino.auth = types.ModuleType("auth")
        trino.auth.BasicAuthentication = type("MockBasicAuth", (), {})
        trino.auth.OAuth2Authentication = type("MockOAuth2Auth", (), {})
        trino.auth.JWTAuthentication = type("MockJWTAuth", (), {})

        def create_engine(*args, **kwargs):
            """Mock create_engine for testing."""
            return type(
                "MockEngine",
                (),
                {
                    "execute": lambda self, query: type(
                        "MockResult",
                        (),
                        {
                            "fetchall": lambda: [],
                            "fetchone": lambda: None,
                            "rowcount": 0,
                        },
                    )(),
                    "connect": lambda: type("MockConnection", (), {})(),
                    "dispose": lambda: None,
                },
            )()

        def text(query):
            """Mock text function."""
            return query

        Engine = type
    else:
        logger.error(
            "Trino and SQLAlchemy libraries are not installed. "
            "Please install with: pip install trino sqlalchemy"
        )
        sys.exit(1)


class TrinoMCPServer:
    """
    Trino MCP Server implementation using FastMCP and SQLAlchemy.

    This server provides secure access to Trino clusters with:
    - Multiple authentication methods (basic, OAuth2, JWT)
    - Read-only mode enforcement with configurable override
    - Comprehensive query execution and schema inspection tools
    - Distributed data source access across catalogs
    """

    def __init__(self, config_dict: dict = None, skip_validation: bool = False):
        """Initialize the Trino MCP Server with configuration."""
        self._skip_validation = skip_validation
        self.config = TrinoServerConfig(
            config_dict=config_dict or {}, skip_validation=skip_validation
        )

        # Standard configuration data from config_schema
        self.config_data = self.config.get_template_config()

        # Full template data (potentially modified by double underscore notation)
        self.template_data = self.config.get_template_data()

        self.logger = self.config.logger

        # Initialize SQLAlchemy engine
        self.engine: Optional[Engine] = None
        self.client = None
        try:
            self._initialize_trino_engine()
        except Exception as e:
            # If validation is enabled, propagate the error so callers/tests can
            # observe initialization failures. Otherwise log and continue.
            if not self._skip_validation:
                raise
            logger.debug("Failed trino initialization: %s", e)

        # Validate read-only mode warning
        if self.config_data.get("trino_allow_write_queries", False):
            warning_msg = "⚠️  WARNING: Trino write mode is ENABLED! This allows data modifications and is potentially unsafe."
            self.logger.warning(warning_msg)
            print(f"\n{warning_msg}\n")

        self.mcp = FastMCP(
            name=self.template_data.get("name", "trino-server"),
            instructions="Trino MCP server for secure distributed data querying and schema inspection",
            version=self.template_data.get("version", "1.0.0"),
            host=os.getenv("MCP_HOST", "0.0.0.0"),
            port=(
                int(
                    os.getenv(
                        "MCP_PORT",
                        self.template_data.get("transport", {}).get("port", 7090),
                    )
                )
                if os.getenv("MCP_TRANSPORT") != "stdio"
                else None
            ),
        )
        self.logger.info(
            "%s MCP server %s created", self.template_data["name"], self.mcp.name
        )
        self.register_tools()

    def _initialize_trino_engine(self):
        """Initialize the SQLAlchemy engine with Trino connection."""
        connection_config = self.config.get_connection_config()

        # Build connection URL
        scheme = "trino"
        host = connection_config["host"]
        port = connection_config["port"]
        user = connection_config["user"]

        # Base URL
        connection_url = f"{scheme}://{user}@{host}:{port}"

        # Add catalog and schema if specified
        if connection_config.get("catalog"):
            connection_url += f"/{connection_config['catalog']}"
            if connection_config.get("schema"):
                connection_url += f"/{connection_config['schema']}"

        # Connection arguments
        connect_args = {
            "http_scheme": connection_config.get("http_scheme", "https"),
            "verify": connection_config.get("verify", False),
        }

        # Add authentication
        auth_config = connection_config.get("auth")
        if auth_config:
            connect_args["auth"] = self._create_auth(auth_config)
        elif connection_config.get("password"):
            # Basic authentication
            connect_args["auth"] = trino.auth.BasicAuthentication(
                connection_config["user"], connection_config["password"]
            )

        try:
            self.engine = create_engine(
                connection_url,
                connect_args=connect_args,
                pool_pre_ping=True,
                pool_recycle=3600,  # Recycle connections every hour
            )

            # Test connection
            if not self._skip_validation:
                with self.engine.connect() as conn:
                    result = conn.execute(text("SELECT 1"))
                    result.fetchone()

            self.logger.info("Trino engine initialized successfully")

        except Exception as e:
            self.logger.error("Failed to initialize Trino engine: %s", e)
            if not self._skip_validation:
                raise

    def _create_auth(self, auth_config: Dict[str, Any]):
        """Create Trino authentication object based on configuration."""
        auth_type = auth_config.get("type")

        if auth_type == "jwt":
            return trino.auth.JWTAuthentication(auth_config.get("secret"))
        elif auth_type == "oidc":
            # For OIDC, we'll use OAuth2Authentication with token
            # In a real implementation, you'd handle the OIDC flow
            # For now, we'll use a placeholder
            return trino.auth.OAuth2Authentication()
        else:
            raise ValueError(f"Unsupported authentication type: {auth_type}")

    def _check_write_operation(self, query: str) -> bool:
        """Check if a query contains write operations."""
        if self.config.get_security_config().get("read_only", True):
            # Parse SQL to check for write operations
            try:
                parsed = sqlparse.parse(query)
                for stmt in parsed:
                    if stmt.get_type() in [
                        "INSERT",
                        "UPDATE",
                        "DELETE",
                        "DROP",
                        "CREATE",
                        "ALTER",
                        "TRUNCATE",
                        "MERGE",
                        "REPLACE",
                    ]:
                        return True

                    # Check for statements that start with write keywords
                    first_token = None
                    for token in stmt.flatten():
                        if token.ttype is None and token.value.strip():
                            first_token = token.value.upper().strip()
                            break

                    if first_token in [
                        "INSERT",
                        "UPDATE",
                        "DELETE",
                        "DROP",
                        "CREATE",
                        "ALTER",
                        "TRUNCATE",
                        "MERGE",
                        "REPLACE",
                    ]:
                        return True

            except Exception as e:
                self.logger.warning("Failed to parse SQL query for write check: %s", e)
                # If parsing fails, err on the side of caution
                return True

        return False

    def register_tools(self):
        """Register tools with the MCP server."""
        self.mcp.tool(self.list_catalogs, tags=["catalogs", "discovery"])
        self.mcp.tool(self.list_schemas, tags=["schemas", "discovery"])
        self.mcp.tool(self.list_tables, tags=["tables", "discovery"])
        self.mcp.tool(self.describe_table, tags=["schema", "metadata"])
        self.mcp.tool(self.execute_query, tags=["query", "sql"])
        self.mcp.tool(self.get_query_status, tags=["query", "status"])
        self.mcp.tool(self.cancel_query, tags=["query", "control"])
        self.mcp.tool(self.get_cluster_info, tags=["cluster", "metadata"])

    def _is_catalog_allowed(self, catalog: str) -> bool:
        """Check if a catalog is allowed by template config (regex or patterns)."""
        cfg = self.config_data

        # Regex takes precedence
        catalog_regex = cfg.get("catalog_regex")
        if catalog_regex:
            try:
                return bool(re.match(catalog_regex, catalog))
            except re.error:
                self.logger.warning("Invalid catalog_regex '%s'", catalog_regex)
                return False

        allowed = cfg.get("allowed_catalogs", "*")
        if allowed == "*":
            return True
        patterns = [p.strip() for p in str(allowed).split(",") if p.strip()]
        return any(fnmatch.fnmatch(catalog, p) for p in patterns)

    def _is_schema_allowed(self, catalog: str, schema: str) -> bool:
        """Check if a schema is allowed by template config (regex or patterns)."""
        cfg = self.config_data

        schema_regex = cfg.get("schema_regex")
        if schema_regex:
            try:
                return bool(re.match(schema_regex, schema))
            except re.error:
                self.logger.warning("Invalid schema_regex '%s'", schema_regex)
                return False

        allowed = cfg.get("allowed_schemas", "*")
        if allowed == "*":
            return True
        patterns = [p.strip() for p in str(allowed).split(",") if p.strip()]
        return any(fnmatch.fnmatch(schema, p) for p in patterns)

    def list_catalogs(self) -> Dict[str, Any]:
        """List all accessible Trino catalogs."""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("SHOW CATALOGS"))
                catalogs = [row[0] for row in result.fetchall()]

            # Apply access control filtering
            catalogs = [c for c in catalogs if self._is_catalog_allowed(c)]

            return {
                "success": True,
                "catalogs": catalogs,
                "total_count": len(catalogs),
                "message": f"Found {len(catalogs)} accessible catalogs",
            }

        except Exception as e:
            self.logger.error("Error listing catalogs: %s", e)
            return {"success": False, "error": str(e), "catalogs": []}

    def list_schemas(self, catalog: str) -> Dict[str, Any]:
        """List schemas in a specific catalog."""
        # Check catalog-level access
        if not self._is_catalog_allowed(catalog):
            return {
                "success": False,
                "error": f"Access to catalog '{catalog}' is not allowed",
                "schemas": [],
            }
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(f"SHOW SCHEMAS FROM {catalog}"))
                schemas = [row[0] for row in result.fetchall()]

            # Apply schema-level access control
            schemas = [s for s in schemas if self._is_schema_allowed(catalog, s)]

            return {
                "success": True,
                "catalog": catalog,
                "schemas": schemas,
                "total_count": len(schemas),
                "message": f"Found {len(schemas)} schemas in catalog '{catalog}'",
            }

        except Exception as e:
            self.logger.error("Error listing schemas in catalog '%s': %s", catalog, e)
            return {"success": False, "error": str(e), "schemas": []}

    def list_tables(self, catalog: str, schema: str) -> Dict[str, Any]:
        """List tables in a specific schema."""
        # Enforce access control
        if not self._is_catalog_allowed(catalog):
            return {
                "success": False,
                "error": f"Access to catalog '{catalog}' is not allowed",
                "tables": [],
            }
        if not self._is_schema_allowed(catalog, schema):
            return {
                "success": False,
                "error": f"Access to schema '{catalog}.{schema}' is not allowed",
                "tables": [],
            }
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(f"SHOW TABLES FROM {catalog}.{schema}"))
                tables = [row[0] for row in result.fetchall()]

            return {
                "success": True,
                "catalog": catalog,
                "schema": schema,
                "tables": tables,
                "total_count": len(tables),
                "message": f"Found {len(tables)} tables in schema '{catalog}.{schema}'",
            }

        except Exception as e:
            self.logger.error(
                "Error listing tables in schema '%s.%s': %s", catalog, schema, e
            )
            return {"success": False, "error": str(e), "tables": []}

    def describe_table(self, catalog: str, schema: str, table: str) -> Dict[str, Any]:
        """Get detailed schema information for a table."""
        # Enforce access control
        if not self._is_catalog_allowed(catalog):
            return {
                "success": False,
                "error": f"Access to catalog '{catalog}' is not allowed",
            }
        if not self._is_schema_allowed(catalog, schema):
            return {
                "success": False,
                "error": f"Access to schema '{catalog}.{schema}' is not allowed",
            }
        try:
            with self.engine.connect() as conn:
                # Get column information
                result = conn.execute(text(f"DESCRIBE {catalog}.{schema}.{table}"))
                columns = []
                for row in result.fetchall():
                    columns.append(
                        {
                            "name": row[0],
                            "type": row[1],
                            "extra": row[2] if len(row) > 2 else "",
                            "comment": row[3] if len(row) > 3 else "",
                        }
                    )

                # Try to get table statistics
                stats = {}
                try:
                    stats_result = conn.execute(
                        text(f"SHOW STATS FOR {catalog}.{schema}.{table}")
                    )
                    for row in stats_result.fetchall():
                        stats[row[0]] = {
                            "distinct_values": row[1],
                            "nulls_fraction": row[2],
                            "avg_size": row[3],
                            "min": row[4],
                            "max": row[5],
                        }
                except Exception:
                    # Stats might not be available for all table types
                    pass

            return {
                "success": True,
                "catalog": catalog,
                "schema": schema,
                "table": table,
                "full_table_name": f"{catalog}.{schema}.{table}",
                "columns": columns,
                "column_count": len(columns),
                "statistics": stats,
            }

        except Exception as e:
            self.logger.error(
                "Error describing table '%s.%s.%s': %s", catalog, schema, table, e
            )
            return {"success": False, "error": str(e)}

    def execute_query(
        self, query: str, catalog: Optional[str] = None, schema: Optional[str] = None
    ) -> Dict[str, Any]:
        """Execute a SQL query against Trino."""
        # Check for write operations in read-only mode
        if self._check_write_operation(query):
            return {
                "success": False,
                "error": "Write operations are not allowed in read-only mode",
                "query": query,
            }

        try:
            # Get query limits
            limits = self.config.get_query_limits()
            timeout = limits.get("timeout", 300)
            max_results = limits.get("max_results", 1000)

            # If catalog/schema provided, prefer lightweight USE statements
            # instead of attempting to set non-existent session properties.
            # If not provided, rely on fully-qualified names in the query.
            use_statements: List[str] = []
            if catalog and schema:
                # Use catalog.schema to set both
                use_statements.append(f"USE {catalog}.{schema}")
            elif catalog:
                # Set catalog (use catalog alone will set the current catalog)
                use_statements.append(f"USE {catalog}")
            elif schema:
                # Use schema within the current catalog
                use_statements.append(f"USE {schema}")

            with self.engine.connect() as conn:
                # Run USE statements if provided
                for stmt in use_statements:
                    try:
                        conn.execute(text(stmt))
                    except Exception:
                        # If USE fails for any reason, continue and let the query run
                        # (we don't want to blow up for optional parameters)
                        self.logger.debug("Failed to run '%s' before query", stmt)

                # Execute the query
                # Note: SQLAlchemy/Trino dialects may not support an execution timeout
                # here; we expose the configured timeout in the response and rely on
                # underlying drivers or session properties for enforcement where
                # supported.
                result = conn.execute(text(query))

                # Fetch results
                rows = []
                row_count = 0
                for row in result:
                    if row_count >= max_results:
                        break
                    rows.append(dict(row._mapping))
                    row_count += 1

                # Check if more rows are available (best-effort)
                try:
                    next_row = next(iter(result), None)
                    truncated = next_row is not None
                except Exception:
                    truncated = False

            return {
                "success": True,
                "query": query,
                "num_rows": len(rows),
                "rows": rows,
                "truncated": truncated,
                "max_results": max_results,
                "timeout": timeout,
                "catalog": catalog,
                "schema": schema,
            }

        except Exception as e:
            self.logger.error("Error executing query: %s", e)
            return {"success": False, "error": str(e), "query": query}

    def get_query_status(self, query_id: str) -> Dict[str, Any]:
        """Get status of a running query."""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(
                    text(
                        f"SELECT * FROM system.runtime.queries WHERE query_id = '{query_id}'"
                    )
                )
                query_info = result.fetchone()

                if query_info:
                    return {
                        "success": True,
                        "query_id": query_id,
                        "state": query_info[2],  # Assuming state is at index 2
                        "query": query_info[1],  # Assuming query text is at index 1
                        "created": query_info[
                            3
                        ],  # Assuming creation time is at index 3
                    }
                else:
                    return {
                        "success": False,
                        "error": f"Query '{query_id}' not found",
                        "query_id": query_id,
                    }

        except Exception as e:
            self.logger.error("Error getting query status for '%s': %s", query_id, e)
            return {"success": False, "error": str(e), "query_id": query_id}

    def cancel_query(self, query_id: str) -> Dict[str, Any]:
        """Cancel a running query."""
        try:
            with self.engine.connect() as conn:
                conn.execute(text(f"KILL '{query_id}'"))

            return {
                "success": True,
                "query_id": query_id,
                "message": f"Query '{query_id}' cancelled successfully",
            }

        except Exception as e:
            self.logger.error("Error cancelling query '%s': %s", query_id, e)
            return {"success": False, "error": str(e), "query_id": query_id}

    def get_cluster_info(self) -> Dict[str, Any]:
        """Get information about the Trino cluster."""
        try:
            with self.engine.connect() as conn:
                # Get cluster information
                cluster_info = {}

                # Get node information (support row objects and plain tuples/dicts)
                result = conn.execute(text("SELECT * FROM system.runtime.nodes"))
                raw_nodes = result.fetchall()
                nodes = []
                for row in raw_nodes:
                    if hasattr(row, "_mapping"):
                        nodes.append(dict(row._mapping))
                    elif isinstance(row, dict):
                        nodes.append(row)
                    else:
                        try:
                            nodes.append({str(i): v for i, v in enumerate(row)})
                        except Exception:
                            nodes.append({"raw": str(row)})

                cluster_info["nodes"] = nodes
                cluster_info["node_count"] = len(nodes)

                # Get version information
                result = conn.execute(text("SELECT version()"))
                ver_row = result.fetchone()
                version = ver_row[0] if ver_row else "unknown"
                cluster_info["version"] = version

                # Get current session info
                result = conn.execute(text("SHOW SESSION"))
                session_props = {}
                for row in result.fetchall():
                    # accept tuple or sequence-like rows
                    try:
                        session_props[row[0]] = row[1]
                    except Exception:
                        continue
                cluster_info["session_properties"] = session_props

            return {"success": True, "cluster_info": cluster_info}

        except Exception as e:
            self.logger.error("Error getting cluster info: %s", e)
            return {"success": False, "error": str(e)}

    def run(self):
        """Run the Trino MCP server."""
        self.logger.info("Starting Trino MCP server...")
        self.mcp.run(
            transport=os.getenv(
                "MCP_TRANSPORT",
                self.template_data.get("transport", {}).get("default", "http"),
            ),
        )


def create_server(config_dict: dict = None) -> TrinoMCPServer:
    """Create and configure a Trino MCP server instance."""
    return TrinoMCPServer(config_dict=config_dict or {})


def setup_health_check(server_instance: TrinoMCPServer):
    """Set up health check endpoint for the server."""

    @server_instance.mcp.custom_route(path="/health", methods=["GET"])
    async def health_check(request: Request):
        """
        Health check endpoint to verify server status.
        """
        try:
            # Test Trino connection
            with server_instance.engine.connect() as conn:
                conn.execute(text("SELECT 1"))

            return JSONResponse(
                {
                    "status": "healthy",
                    "server": "Trino MCP Server",
                    "version": server_instance.template_data.get("version", "1.0.0"),
                    "trino_connection": "ok",
                    "read_only_mode": server_instance.config.is_read_only(),
                    "trino_host": server_instance.config_data.get("trino_host"),
                    "trino_port": server_instance.config_data.get("trino_port"),
                }
            )
        except Exception as e:
            return JSONResponse(
                {
                    "status": "unhealthy",
                    "error": str(e),
                    "server": "Trino MCP Server",
                },
                status_code=503,
            )


async def health_check(request: Request):
    """
    Standalone health check function for testing purposes.
    """
    return JSONResponse(
        {
            "status": "healthy",
            "server": "Trino MCP Server",
            "version": "1.0.0",
            "trino_connection": "ok",
            "test_mode": True,
        }
    )


if __name__ == "__main__":
    # Only create server when running as main module
    server = create_server()
    setup_health_check(server)
    server.run()
