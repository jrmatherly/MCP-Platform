# Installation

## Requirements

- Python 3.10 or higher
- [uv](https://docs.astral.sh/uv/) (recommended) or pip for package management
- Docker (for containerized deployment)
- Git

## Install with uv (Recommended)

```bash
# Install as a project dependency
uv add mcp-platform

# Or install as a global tool
uv tool install mcp-platform
```

## Installation Methods

### Option 1: Install with uv (Recommended)

The fastest and most reliable way to install MCP Platform is using uv:

```bash
# Install the latest stable version as a global tool
uv tool install mcp-platform

# Or add to your project
uv add mcp-platform

# Verify installation
mcpp --version
```

**Benefits:**
- ✅ Latest stable release
- ✅ Automatic dependency management
- ✅ Works across all platforms
- ✅ No need to clone the repository

### Option 2: From Source (Development)

For development or to get the latest features:

```bash
# Clone the repository
git clone https://github.com/jrmatherly/MCP-Platform
cd MCP-Platform

# Install dependencies and project
uv sync

## Verify Installation

```bash
mcpp --version
mcpp list
```

You should see the available templates listed.
