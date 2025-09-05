"""
Trino MCP Server Template.

A production-ready Trino MCP server that provides secure access to distributed
data sources with configurable authentication, read-only mode, and comprehensive
query execution capabilities using FastMCP and SQLAlchemy.
"""

from .server import TrinoMCPServer, create_server

__all__ = ["TrinoMCPServer", "create_server"]
