# Quick Start

Get started with MCP Templates in minutes.

## 1. List Available Templates

```bash
mcpp list
```

## 2. Deploy a Template

```bash
# Deploy the demo template
mcpp deploy demo

# Deploy with custom configuration
mcpp deploy filesystem --port 8080
```

## 3. Test Your Deployment

```bash
# Check if the server is running
curl http://localhost:8080/health

# View server logs
mcpp logs demo
```

## 4. Clean Up

```bash
# Stop the server
mcpp stop demo

# Remove the deployment
mcpp remove demo
```

## Next Steps

- Check out the [Templates Overview](../server-templates/index.md) to see what's available
- Learn about [Configuration](configuration.md) options
- Read the [Deployment Guide](../guides/deployment.md) for advanced usage
