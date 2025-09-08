# MCP Platform

[![Version](https://img.shields.io/pypi/v/mcp-platform.svg)](https://pypi.org/project/mcp-platform/)
[![Python Versions](https://img.shields.io/pypi/pyversions/mcp-platform.svg)](https://pypi.org/project/mcp-platform/)
[![License](https://img.shields.io/badge/License-Elastic%202.0-blue.svg)](LICENSE)
[![Discord](https://img.shields.io/discord/XXXXX?color=7289da&logo=discord&logoColor=white)](https://discord.gg/55Cfxe9gnr)

[![Trust Score](https://archestra.ai/mcp-catalog/api/badge/quality/Data-Everything/MCP-Platform)](https://archestra.ai/mcp-catalog/data-everything__mcp-platform)

<div align="center">

**[📚 Documentation](https://data-everything.github.io/MCP-Platform/)** • **[💬 Discord Community](https://discord.gg/55Cfxe9gnr)** • **[🚀 Quick Start](#-quick-start)**

</div>

> **The definitive platform for deploying Model Context Protocol (MCP) servers in production.**

Zero-configuration deployment of production-ready MCP servers with Docker containers, comprehensive CLI tools, intelligent caching, and enterprise-grade management features. Focus on AI integration, not infrastructure setup.

---

## 🚀 Quick Start

```bash
# Install MCP Platform using uv
uv add mcp-platform

# Or install globally
uv tool install mcp-platform

# List available templates
mcpp list

# Deploy instantly
mcpp deploy demo

# View deployment
mcpp logs demo
```

**That's it!** Your MCP server is running at `http://localhost:8080`

---

## ⚡ Why MCP Platform?

| Traditional MCP Setup | With MCP Platform |
|----------------------|-------------------|
| ❌ Complex configuration | ✅ One-command deployment |
| ❌ Docker expertise required | ✅ Zero configuration needed |
| ❌ Manual tool discovery | ✅ Automatic detection |
| ❌ Environment setup headaches | ✅ Pre-built containers |

**Perfect for:** AI developers, data scientists, DevOps teams building with MCP.

---

## 🌟 Key Features

### 🖱️ **One-Click Deployment**
Deploy MCP servers instantly with pre-built templates—no Docker knowledge required.

### 🌐 **Enterprise Gateway**
Production-ready load balancer with authentication, database persistence, and advanced routing. [See gateway documentation](mcp_platform/gateway/README.md) for enterprise deployment details.

### 🔍 **Smart Tool Discovery**
Automatically finds and showcases every tool your server offers.

### 🧠 **Intelligent Caching**
6-hour template caching with automatic invalidation for lightning-fast operations.

### 💻 **Powerful CLI**
Comprehensive command-line interface for deployment, management, and tool execution.

### 🛠️ **Flexible Configuration**
Configure via JSON, YAML, environment variables, CLI options, or override parameters.

### 📦 **Growing Template Library**
Ready-to-use templates for common use cases: filesystem, databases, APIs, and more.

---

## 📚 Installation

### PyPI with uv (Recommended)
```bash
uv add mcp-platform
# Or install as a tool globally
uv tool install mcp-platform
```

### Docker
```bash
docker run --privileged -it mcp-platform/mcp-server-templates:latest deploy demo
```

### From Source
```bash
git clone https://github.com/jrmatherly/MCP-Platform.git
cd MCP-Platform
uv sync --all-extras
```

---

## 🎯 Common Use Cases

### Deploy with Custom Configuration
```bash
# Basic deployment
mcpp deploy filesystem --config allowed_dirs="/path/to/data"

# Advanced overrides
mcpp deploy demo --override metadata__version=2.0 --transport http
```

### Manage Deployments
```bash
# List all deployments
mcpp list --deployed

# Stop a deployment
mcpp stop demo

# View logs
mcpp logs demo --follow
```

### Template Development
```bash
# Create new template
mcpp create my-template

# Test locally
mcpp deploy my-template --backend mock
```

---

## 🏗️ Architecture

```
┌─────────────┐    ┌───────────────────┐    ┌─────────────────────┐
│  CLI Tool   │───▶│ DeploymentManager │───▶│ Backend (Docker)    │
│  (mcpp)     │    │                   │    │                     │
└─────────────┘    └───────────────────┘    └─────────────────────┘
       │                      │                        │
       ▼                      ▼                        ▼
┌─────────────┐    ┌───────────────────┐    ┌─────────────────────┐
│ Template    │    │ CacheManager      │    │ Container Instance  │
│ Discovery   │    │ (6hr TTL)         │    │                     │
└─────────────┘    └───────────────────┘    └─────────────────────┘
```

**Configuration Flow:** Template Defaults → Config File → CLI Options → Environment Variables

---

## 📦 Available Templates

| Template | Description | Transport | Use Case |
|----------|-------------|-----------|----------|
| **demo** | Hello world MCP server | HTTP, stdio | Testing & learning |
| **filesystem** | Secure file operations | stdio | File management |
| **gitlab** | GitLab API integration | stdio | CI/CD workflows |
| **github** | GitHub API integration | stdio | Development workflows |
| **zendesk** | Customer support tools | HTTP, stdio | Support automation |

[View all templates →](docs/templates/)

---

## 🛠️ Configuration Examples

### Basic Configuration
```bash
mcpp deploy filesystem --config allowed_dirs="/home/user/data"
```

### Advanced Configuration
```bash
mcpp deploy gitlab \
  --config gitlab_token="$GITLAB_TOKEN" \
  --config read_only_mode=true \
  --override metadata__version=1.2.0 \
  --transport stdio
```

### Configuration File
```json
{
  "allowed_dirs": "/home/user/projects",
  "log_level": "DEBUG",
  "security": {
    "read_only": false,
    "max_file_size": "100MB"
  }
}
```

```bash
mcpp deploy filesystem --config-file myconfig.json
```

---

## 🔧 Template Development

### Creating Templates

1. **Use the generator**:
   ```bash
   mcpp create my-template
   ```

2. **Define template.json**:
   ```json
   {
     "name": "My Template",
     "description": "Custom MCP server",
     "docker_image": "my-org/my-mcp-server",
     "transport": {
       "default": "stdio",
       "supported": ["stdio", "http"]
     },
     "config_schema": {
       "type": "object",
       "properties": {
         "api_key": {
           "type": "string",
           "env_mapping": "API_KEY",
           "sensitive": true
         }
       }
     }
   }
   ```

3. **Test and deploy**:
   ```bash
   mcpp deploy my-template --backend mock
   ```

[Full template development guide →](docs/templates/creating.md)

---

## 📖 Documentation

- **[Getting Started](GETTING_STARTED.md)** - Installation and first deployment
- **[Quick Start Guide](QUICKSTART.md)** - 2-minute deployment guide
- **[CLI Reference](docs/user-guide/cli-reference.md)** - Complete command documentation
- **[Template Guide](docs/templates/creating.md)** - Creating and configuring templates
- **[Gateway Documentation](mcp_platform/gateway/README.md)** - Enterprise gateway deployment
- **[Docker Setup Guide](docker/README.md)** - Production deployment with Docker Compose

---

## 🤝 Community

- **[Discord Server](https://discord.gg/55Cfxe9gnr)** - Get help and discuss features
- **[GitHub Issues](https://github.com/jrmatherly/MCP-Platform/issues)** - Report bugs and request features
- **[Discussions](https://github.com/jrmatherly/MCP-Platform/discussions)** - Share templates and use cases

---

## 📝 License

This project is licensed under the [Elastic License 2.0](LICENSE).

---

## 🙏 Acknowledgments

Built with ❤️ for the MCP community. Thanks to all contributors and template creators!
