-- MCP Platform Gateway Database Initialization Script
-- This script runs automatically when PostgreSQL container starts for the first time

-- Create database (already created by POSTGRES_DB env var)
-- CREATE DATABASE mcp_gateway;

-- Create extensions if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- Grant permissions to the user
GRANT ALL PRIVILEGES ON DATABASE mcp_gateway TO mcpuser;

-- Optional: Create additional schemas for organization
-- CREATE SCHEMA IF NOT EXISTS auth;
-- CREATE SCHEMA IF NOT EXISTS registry;
-- CREATE SCHEMA IF NOT EXISTS metrics;

-- Set default search path
-- ALTER USER mcpuser SET search_path = public, auth, registry, metrics;

-- Log completion
\echo 'MCP Gateway database initialization completed'