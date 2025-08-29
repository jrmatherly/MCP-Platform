# Troubleshooting Guide

**Common issues and solutions for MCP Template Platform deployments and development.**

## Quick Diagnostics

### Check System Status

```bash
# Verify MCP Template Platform installation
mcpp --version

# Check Docker status
docker --version
docker info

# List all deployments
mcpp list

# Check deployment health
mcpp status
```

### Basic Health Check

```bash
# Test a simple deployment
mcpp deploy demo --config debug=true

# Verify tools are discovered
mcpp> tools demo

# Check logs for errors
mcpp logs demo --tail 50
```

## Common Issues

### Installation Problems

#### 1. Python Package Installation Fails

**Symptoms:**
```
ERROR: Could not build wheels for mcp-platform
```

**Solutions:**
```bash
# Update pip and build tools
pip install --upgrade pip setuptools wheel

# Install with verbose output
pip install -v mcp-platform

# Use conda if pip fails
conda install -c conda-forge mcp-platform
```

#### 2. Docker Connection Issues

**Symptoms:**
```
ERROR: Cannot connect to Docker daemon
```

**Solutions:**
```bash
# Start Docker service
sudo systemctl start docker

# Add user to docker group
sudo usermod -aG docker $USER
newgrp docker

# Verify Docker works
docker run hello-world
```

### Deployment Issues

#### 1. Template Not Found

**Symptoms:**
```
ERROR: Template 'my-template' not found
```

**Solutions:**
```bash
# List available templates
mcpp list

# Check templates directory
ls -la templates/

# Validate template structure
mcpp create --help

# Create missing template
mcpp create my-template
```

#### 2. Container Fails to Start

**Symptoms:**
```
ERROR: Container exited with code 1
```

**Diagnostics:**
```bash
# Check container logs
mcpp logs deployment-name

# Inspect container
docker logs mcp-deployment-name

# Check image exists
docker images | grep mcp

# Test image directly
docker run -it mcp/template:latest /bin/bash
```

**Solutions:**
```bash
# Force image pull
mcpp deploy template --force-pull

# Check configuration
mcpp config template

# Use debug mode
mcpp deploy template --config debug=true
```

#### 3. Port Conflicts

**Symptoms:**
```
ERROR: Port 8080 already in use
```

**Solutions:**
```bash
# Find what's using the port
sudo netstat -tulpn | grep 8080

# Use different port
mcpp deploy template --port 8081

# Stop conflicting service
sudo systemctl stop service-on-port-8080
```

### Tool Discovery Issues

#### 1. No Tools Discovered

**Symptoms:**
```
No tools found in deployment
```

**Diagnostics:**
```bash
# Test MCP protocol directly
mcpp> tools --image template:latest

# Check container logs
mcpp logs deployment --filter "tool\|mcp"

# Verify MCP server is running
docker exec -it mcp-deployment python -c "import sys; print(sys.version)"
```

**Solutions:**
```bash
# Update to latest image
mcpp deploy template --force-pull

# Check template configuration
mcpp config template

# Test with stdio transport
mcpp connect template --transport stdio
```

#### 2. Partial Tool Discovery

**Symptoms:**
```
Only 3 of 10 tools discovered
```

**Solutions:**
```bash
# Increase discovery timeout
mcpp> tools --image template

# Check for tool initialization errors
mcpp logs deployment --filter "error\|exception"

# Restart deployment
mcpp deploy template --force-recreate
```

### Configuration Issues

#### 1. Environment Variables Not Set

**Symptoms:**
```
Missing required configuration: API_KEY
```

**Solutions:**
```bash
# Check current configuration
mcpp config template

# Set environment variable
export MCP_API_KEY="your-key-here"

# Use config file
echo '{"api_key": "your-key"}' > config.json
mcpp deploy template --config-file config.json

# Pass inline configuration
mcpp deploy template --config api_key=your-key
```

#### 2. Configuration Validation Fails

**Symptoms:**
```
ERROR: Invalid configuration schema
```

**Solutions:**
```bash
# Validate configuration file
python -m json.tool config.json

# Check template schema
mcpp config template --show-schema

# Use minimal configuration
mcpp deploy template --config debug=true
```

### Performance Issues

#### 1. Slow Tool Discovery

**Symptoms:**
- Discovery takes >30 seconds
- Timeouts during tool enumeration

**Solutions:**
```bash
# Increase timeouts
mcpp> tools --image template

# Use HTTP transport instead of stdio
mcpp deploy template --transport http

# Check container resources
docker stats mcp-deployment
```

#### 2. High Memory Usage

**Symptoms:**
- Container using excessive memory
- Out of memory errors

**Solutions:**
```bash
# Set memory limits
mcpp deploy template --memory 512m

# Check for memory leaks
mcpp logs deployment --filter "memory\|oom"

# Monitor resource usage
mcpp status deployment --watch
```

### Network Issues

#### 1. Connection Refused

**Symptoms:**
```
Connection refused to localhost:8080
```

**Solutions:**
```bash
# Check if port is mapped
docker port mcp-deployment

# Verify container is running
mcpp status deployment

# Test network connectivity
docker exec mcp-deployment curl http://localhost:8080/health

# Use stdio transport instead
mcpp connect deployment --transport stdio
```

#### 2. DNS Resolution Issues

**Symptoms:**
```
Could not resolve hostname
```

**Solutions:**
```bash
# Use IP address instead of hostname
mcpp deploy template --config host=127.0.0.1

# Check Docker DNS
docker exec mcp-deployment nslookup google.com

# Restart Docker daemon
sudo systemctl restart docker
```

## Development Issues

### Template Development

#### 1. Template Validation Fails

**Symptoms:**
```
ERROR: Invalid template.json format
```

**Solutions:**
```bash
# Validate JSON syntax
python -m json.tool templates/my-template/template.json

# Check required fields
mcpp create --help

# Use template wizard
mcpp create my-template
```

#### 2. Docker Build Fails

**Symptoms:**
```
ERROR: Build failed for template
```

**Solutions:**
```bash
# Build manually to see errors
cd templates/my-template
docker build -t my-template .

# Check Dockerfile syntax
docker build --no-cache -t my-template .

# Use smaller base image
# Change FROM python:3.11 to FROM python:3.11-slim
```

### Testing Issues

#### 1. Tests Not Running

**Symptoms:**
```
No tests found for template
```

**Solutions:**
```bash
# Check test directory exists
ls -la templates/my-template/tests/

# Create test structure
mkdir -p templates/my-template/tests
touch templates/my-template/tests/test_server.py

# Run tests manually
cd templates/my-template
python -m pytest tests/
```

## Advanced Diagnostics

### Debug Mode

Enable comprehensive debugging:

```bash
# Set debug environment
export MCP_LOG_LEVEL=DEBUG
export MCP_DEBUG=true

# Deploy with debug configuration
mcpp deploy template --config debug=true log_level=DEBUG

# Monitor debug logs
mcpp logs deployment --follow --filter "DEBUG"
```

### Container Inspection

Deep dive into container issues:

```bash
# Get container information
docker inspect mcp-deployment

# Access container shell
docker exec -it mcp-deployment /bin/bash

# Check process tree
docker exec mcp-deployment ps aux

# Monitor container stats
docker stats mcp-deployment --no-stream
```

### MCP Protocol Debugging

Test MCP protocol directly:

```bash
# Test stdio communication
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | \
docker exec -i mcp-deployment python server.py

# Test HTTP endpoint
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'

# Monitor MCP messages
mcpp connect deployment --debug
```

## Getting Help

### Self-Service Resources

1. **Check Documentation**
   - [CLI Reference](../cli/index.md)
   - [Template Creation Guide](creating-templates.md)
   - [Tool Discovery Documentation](../tool-discovery.md)

2. **Search Common Issues**
   ```bash
   # Search logs for error patterns
   mcpp logs deployment | grep -i error

   # Check GitHub issues
   # Visit: https://github.com/data-everything/MCP-Platform/issues
   ```

3. **Community Resources**
   - GitHub Discussions
   - Discord Community
   - Stack Overflow (tag: mcp-platform)

### Professional Support

For production environments:

- **Enterprise Support**: Contact support@dataeverything.ai
- **Custom Templates**: Professional template development services
- **Training**: Team training and workshops available

### Reporting Issues

When reporting issues, include:

1. **System Information**
   ```bash
   mcpp --version
   docker --version
   python --version
   uname -a
   ```

2. **Error Details**
   ```bash
   # Full error logs
   mcpp logs deployment --since 1h

   # Configuration
   mcpp config deployment

   # Status information
   mcpp status deployment --detailed
   ```

3. **Steps to Reproduce**
   - Exact commands used
   - Template configuration
   - Expected vs actual behavior

## Prevention Best Practices

### Regular Maintenance

```bash
# Update MCP Template Platform
pip install --upgrade mcp-platform

# Clean up old containers
docker system prune -f

# Check deployment health
mcpp status --health-only
```

### Monitoring Setup

```bash
# Set up health checks
mcpp status --watch --refresh 60 > health.log &

# Monitor resource usage
docker stats --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}" \
  $(docker ps --filter "name=mcp-" --format "{{.Names}}")
```

### Configuration Management

```bash
# Backup configurations
mkdir -p ~/.mcp/backups
cp -r ~/.mcp/config ~/.mcp/backups/config-$(date +%Y%m%d)

# Version control templates
cd templates/
git init
git add .
git commit -m "Initial template configuration"
```

By following this troubleshooting guide, most common issues can be resolved quickly. For complex problems, don't hesitate to seek community or professional support.
