# Database Support

The MCP Platform Gateway supports multiple database backends for flexible deployment scenarios. This document covers database configuration, supported databases, and installation instructions.

## Default Database (SQLite)

By default, the gateway uses SQLite with the `aiosqlite` driver, which is included automatically:

```bash
pip install mcp-platform
```

The default configuration uses a local SQLite database:
```
database_url: sqlite:///./gateway.db
```

SQLite is perfect for:
- Development and testing
- Single-node deployments
- Small to medium workloads
- Scenarios where external database setup is not desired

## Supported Database Backends

The gateway supports multiple database backends through optional dependency extras:

### PostgreSQL (Recommended for Production)

PostgreSQL is recommended for production deployments due to its robustness, performance, and advanced features.

**Installation:**
```bash
pip install mcp-platform[postgresql]
```

**Configuration:**
```yaml
database:
  url: postgresql://username:password@localhost:5432/mcp_platform
  pool_size: 10
  max_overflow: 20
```

**Features:**
- ACID compliance
- Advanced indexing and query optimization
- Excellent concurrent performance
- Rich ecosystem and tooling

### MySQL

MySQL/MariaDB support for environments that require MySQL compatibility.

**Installation:**
```bash
pip install mcp-platform[mysql]
```

**Configuration:**
```yaml
database:
  url: mysql://username:password@localhost:3306/mcp_platform
  pool_size: 10
  max_overflow: 20
```

### Oracle Database

Enterprise Oracle Database support for organizations using Oracle infrastructure.

**Installation:**
```bash
pip install mcp-platform[oracle]
```

**Configuration:**
```yaml
database:
  url: oracle://username:password@localhost:1521/XE
  pool_size: 5
  max_overflow: 10
```

**Note:** Oracle support requires Oracle Instant Client to be installed on the system.

### Microsoft SQL Server

SQL Server support for Microsoft-centric environments.

**Installation:**
```bash
pip install mcp-platform[mssql]
```

**Configuration:**
```yaml
database:
  url: mssql://username:password@localhost:1433/mcp_platform
  pool_size: 10
  max_overflow: 20
```

**Note:** Requires ODBC drivers to be installed on the system.

### All Database Support

To install support for all database backends:

```bash
pip install mcp-platform[all-databases]
```

## Database Configuration

### Basic Configuration

Configure the database connection in your gateway configuration file:

```yaml
database:
  url: "your-database-url-here"
  echo: false          # Set to true for SQL query logging
  pool_size: 10        # Connection pool size
  max_overflow: 20     # Maximum overflow connections
```

### Environment Variables

You can also configure the database using environment variables:

```bash
export MCP_DATABASE_URL="postgresql://user:pass@localhost:5432/mcp"
export MCP_DATABASE_POOL_SIZE=10
export MCP_DATABASE_MAX_OVERFLOW=20
export MCP_DATABASE_ECHO=false
```

### Connection Pool Settings

Adjust connection pool settings based on your workload:

- **pool_size**: Number of persistent connections to maintain
- **max_overflow**: Additional connections beyond pool_size
- **echo**: Enable SQL query logging (for debugging)

**Recommended settings by database:**

| Database | pool_size | max_overflow | Notes |
|----------|-----------|--------------|-------|
| SQLite | 1 | 0 | Single connection for SQLite |
| PostgreSQL | 10-20 | 20-30 | Scales well with connections |
| MySQL | 10-15 | 15-25 | Good concurrent performance |
| Oracle | 5-10 | 10-15 | Expensive connections |
| SQL Server | 10-15 | 15-25 | Similar to MySQL |

## Database Setup

### PostgreSQL Setup Example

1. Install PostgreSQL:
```bash
# Ubuntu/Debian
sudo apt-get install postgresql postgresql-contrib

# CentOS/RHEL
sudo yum install postgresql-server postgresql-contrib
```

2. Create database and user:
```sql
CREATE DATABASE mcp_platform;
CREATE USER mcp_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE mcp_platform TO mcp_user;
```

3. Install MCP Platform with PostgreSQL support:
```bash
pip install mcp-platform[postgresql]
```

4. Configure the gateway:
```yaml
database:
  url: postgresql://mcp_user:secure_password@localhost:5432/mcp_platform
  pool_size: 15
  max_overflow: 25
```

### Docker Database Setup

For development, you can use Docker to quickly set up databases:

**PostgreSQL:**
```bash
docker run --name mcp-postgres \
  -e POSTGRES_DB=mcp_platform \
  -e POSTGRES_USER=mcp_user \
  -e POSTGRES_PASSWORD=secure_password \
  -p 5432:5432 \
  -d postgres:17-alpine
```

**MySQL:**
```bash
docker run --name mcp-mysql \
  -e MYSQL_DATABASE=mcp_platform \
  -e MYSQL_USER=mcp_user \
  -e MYSQL_PASSWORD=secure_password \
  -e MYSQL_ROOT_PASSWORD=root_password \
  -p 3306:3306 \
  -d mysql:8.0
```

## Migration and Schema Management

The gateway automatically creates and manages database schemas using SQLModel/SQLAlchemy. When you start the gateway:

1. Database tables are automatically created if they don't exist
2. The schema is kept in sync with the application models
3. No manual migration scripts are needed for basic operation

For production deployments, consider:
- Taking database backups before updates
- Testing schema changes in staging environments
- Monitoring database performance and logs

## Performance Considerations

### SQLite
- **Pros**: Zero configuration, excellent for development
- **Cons**: Limited concurrent writes, not suitable for high-traffic production
- **Best for**: Development, testing, small deployments

### PostgreSQL
- **Pros**: Excellent performance, ACID compliance, advanced features
- **Cons**: Requires database server setup
- **Best for**: Production deployments, high concurrency

### MySQL
- **Pros**: Wide adoption, good performance, familiar to many teams
- **Cons**: Some advanced features lag behind PostgreSQL
- **Best for**: Existing MySQL environments

### Oracle
- **Pros**: Enterprise features, excellent for large-scale deployments
- **Cons**: Expensive, complex setup
- **Best for**: Enterprise environments already using Oracle

### SQL Server
- **Pros**: Integration with Microsoft ecosystem, enterprise features
- **Cons**: Windows-centric, licensing costs
- **Best for**: Microsoft-centric environments

## Troubleshooting

### Driver Import Errors

If you see import errors like "Import 'asyncpg' could not be resolved":

1. Install the correct database extra:
   ```bash
   pip install mcp-platform[postgresql]  # for PostgreSQL
   pip install mcp-platform[mysql]       # for MySQL
   pip install mcp-platform[oracle]      # for Oracle
   pip install mcp-platform[mssql]       # for SQL Server
   ```

2. Verify the installation:
   ```bash
   python -c "import asyncpg; print('PostgreSQL driver installed')"
   ```

### Connection Issues

1. Verify database server is running
2. Check network connectivity and firewall settings
3. Verify credentials and database permissions
4. Check connection pool settings

### Performance Issues

1. Monitor connection pool utilization
2. Adjust pool_size and max_overflow settings
3. Enable query logging with `echo: true` to identify slow queries
4. Consider database-specific performance tuning

## Security Considerations

1. **Use environment variables** for database credentials
2. **Enable SSL/TLS** for database connections in production
3. **Restrict database user permissions** to only what's needed
4. **Use connection pooling** to prevent connection exhaustion attacks
5. **Monitor database logs** for suspicious activity
6. **Regular database backups** and recovery testing

## Examples

### Development with SQLite
```bash
pip install mcp-platform
# Uses SQLite by default - no additional setup needed
```

### Production with PostgreSQL
```bash
pip install mcp-platform[postgresql]
export MCP_DATABASE_URL="postgresql://user:pass@db.example.com:5432/mcp"
mcp-gateway run
```

### Docker Compose Example
```yaml
version: '3.8'
services:
  gateway:
    image: mcp-platform:latest
    environment:
      - MCP_DATABASE_URL=postgresql://mcp:password@postgres:5432/mcp
    depends_on:
      - postgres

  postgres:
    image: postgres:17-alpine
    environment:
      - POSTGRES_DB=mcp
      - POSTGRES_USER=mcp
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```
