-- Initialize PostgreSQL database for MCP Platform Gateway
-- This script runs during container initialization

-- Create additional databases if needed
-- CREATE DATABASE mcp_gateway_test;

-- Create additional users if needed
-- CREATE USER mcp_readonly WITH PASSWORD 'readonly_password';
-- GRANT CONNECT ON DATABASE mcp_gateway TO mcp_readonly;
-- GRANT USAGE ON SCHEMA public TO mcp_readonly;
-- GRANT SELECT ON ALL TABLES IN SCHEMA public TO mcp_readonly;
-- GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO mcp_readonly;

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE EXTENSION IF NOT EXISTS "pg_trgm";

CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- Grant comprehensive permissions to the user
GRANT ALL PRIVILEGES ON DATABASE mcp_gateway TO mcp_user;

-- Create initial schema (optional - can be handled by application migrations)
-- The gateway application will handle its own schema creation

-- Log completion
\echo 'MCP Platform Gateway database initialization completed';