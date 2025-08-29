# Installation

## Requirements

- Python 3.10 or higher
- Docker (for containerized deployment)
- Git

## Install from PyPI

```bash
pip install mcp-platform
```

## Installation Methods

### Option 1: Install from PyPI (Recommended)

The simplest way to install MCP Server Templates is directly from PyPI:

```bash
# Install the latest stable version
pip install mcp-platform

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
git clone https://github.com/Data-Everything/MCP-Platform
cd MCP-Platform

# Install in development mode
pip install -e .

## Verify Installation

```bash
mcpp --version
mcpp list
```

You should see the available templates listed.
