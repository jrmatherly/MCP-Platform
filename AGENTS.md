# AI Agent Instructions for MCP Platform

**AI agents and development tools working on this codebase should follow these guidelines to maintain consistency, quality, and project alignment.**

## Project Overview

**MCP Platform** is a production-ready deployment system for Model Context Protocol (MCP) servers. It provides a unified architecture for deploying, configuring, and managing MCP server templates with extensive configuration support and multiple deployment backends.

### Core Architecture
- **CLI Layer**: Rich interface with Typer-based CLI (`mcp_platform/cli/`)
- **Management Layer**: DeploymentManager and TemplateManager orchestration (`mcp_platform/core/`)
- **Backend Layer**: Pluggable deployment services - Docker, Kubernetes, Mock (`mcp_platform/backends/`)
- **Gateway Layer**: FastAPI-based unified gateway with auth, load balancing (`mcp_platform/gateway/`)
- **Template Layer**: Dynamic template discovery and configuration (`mcp_platform/template/`)
- **Discovery Layer**: Dynamic template detection and tool management (`mcp_platform/tools/`)

## Development Standards

### Code Quality Requirements
- **Python Version**: 3.10+ (supports 3.10, 3.11, 3.12, 3.13)
- **Type Hints**: Required for all public functions and classes
- **Documentation**: Comprehensive docstrings following Google style
- **Testing**: 80%+ code coverage with comprehensive unit and integration tests
- **Error Handling**: Use custom exception classes from `mcp_platform.core.exceptions`

### Code Style and Formatting
```bash
# Required tools (configured in pyproject.toml [tool.uv.dev-dependencies])
black mcp_platform/ tests/           # Code formatting (line length: 90)
isort mcp_platform/ tests/           # Import sorting (profile: black)
flake8 mcp_platform/ tests/          # Linting (max-line-length: 90)
bandit -r mcp_platform/              # Security scanning
mypy mcp_platform/                   # Type checking
```

### Project Structure Patterns
```
mcp_platform/
├── __init__.py                      # Main exports and version
├── backends/                        # Deployment backends (docker, kubernetes, mock)
├── cli/                            # CLI interface (typer-based)
├── client/                         # MCP client functionality
├── core/                           # Core managers and processors
│   ├── deployment_manager.py       # Central deployment orchestration
│   ├── template_manager.py         # Template operations
│   ├── exceptions.py               # Custom exception classes
│   └── config_processor.py         # Configuration handling
├── gateway/                        # FastAPI gateway server
├── template/                       # Template utilities and discovery
├── tools/                          # Tool management and probes
└── utils/                          # Shared utilities
```

## Development Workflow

### Setup and Installation
```bash
# Development environment setup with uv
make install          # Install dependencies with uv sync
make install-dev      # Install in development mode with uv
make dev-setup        # Complete development setup using uv

# Verify setup
python tests/runner.py --unit
make lint
```

### Testing Strategy
```bash
# Test execution patterns
make test-quick       # Fast validation tests
make test-unit        # Unit tests (no external dependencies)
make test-integration # Integration tests (requires Docker)
make test-all         # Complete test suite

# Coverage requirements
pytest tests/ --cov=mcp_platform --cov-fail-under=80
```

### Test Organization
- **Unit Tests**: `tests/test_unit/` - Fast, isolated tests
- **Integration Tests**: `tests/test_integration/` - External dependencies
- **Template Tests**: Template-specific validation
- **Markers**: Use pytest markers (`@pytest.mark.unit`, `@pytest.mark.docker`, etc.)

### Quality Gates
```bash
# Pre-commit requirements
make format           # Black + isort formatting
make lint            # flake8 + bandit security
make type-check      # mypy type validation
make test-all        # Full test suite
```

## Architecture Patterns

### Backend Abstraction Pattern
```python
# Use backend abstraction for deployment operations
from mcp_platform.backends import get_backend

backend = get_backend("docker")  # or "kubernetes", "mock"
result = backend.deploy(template_id, config)
```

### Template Management Pattern
```python
# Centralized template operations
from mcp_platform.core import TemplateManager

manager = TemplateManager(backend_type="docker")
templates = manager.list_templates()
result = manager.validate_template(template_id)
```

### Error Handling Pattern
```python
# Use specific exception types
from mcp_platform.core.exceptions import (
    TemplateNotFoundError,
    DeploymentError,
    InvalidConfigurationError
)

try:
    template = manager.get_template(template_id)
except TemplateNotFoundError:
    logger.error(f"Template {template_id} not found")
    raise
```

### Configuration Processing Pattern
```python
# Process configurations with validation
from mcp_platform.core.config_processor import ConfigProcessor

processor = ConfigProcessor(template_config)
processed_config = processor.process_config(user_config)
```

## API Design Principles

### Function and Class Design
```python
def deploy_template(
    template_id: str,
    config: Dict[str, Any],
    backend_type: str = "docker",
    options: Optional[DeploymentOptions] = None
) -> DeploymentResult:
    """Deploy an MCP template with specified configuration.
    
    Args:
        template_id: Unique identifier for the template
        config: Template-specific configuration parameters
        backend_type: Deployment backend (docker, kubernetes, mock)
        options: Optional deployment options
        
    Returns:
        DeploymentResult with success status and deployment details
        
    Raises:
        TemplateNotFoundError: If template doesn't exist
        DeploymentError: If deployment fails
        InvalidConfigurationError: If config is invalid
    """
```

### Import Patterns
```python
# Standard library imports
import logging
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

# Third-party imports
import aiohttp
from rich.console import Console
from fastapi import FastAPI

# Local imports
from mcp_platform.core import DeploymentManager, TemplateManager
from mcp_platform.backends import get_backend
from mcp_platform.core.exceptions import MCPException
```

## Template Development

### Template Structure Requirements
```
templates/template-name/
├── template.json          # Schema and configuration
├── Dockerfile            # Container definition
├── src/                  # Source code
├── tests/               # Template-specific tests
├── README.md            # Documentation
└── examples/            # Usage examples
```

### Template Configuration Schema
```json
{
  "id": "template-name",
  "name": "Human-readable Template Name",
  "description": "Template functionality description",
  "version": "1.0.0",
  "author": "Author Name",
  "mcp_version": "0.4.0",
  "image": "dataeverything/mcp-template-name",
  "config_schema": {},
  "example_config": {}
}
```

## Testing Patterns

### Unit Test Example
```python
import pytest
from unittest.mock import Mock, patch

from mcp_platform.core.deployment_manager import DeploymentManager
from mcp_platform.core.exceptions import DeploymentError

class TestDeploymentManager:
    @pytest.fixture
    def manager(self):
        return DeploymentManager(backend_type="mock")
    
    @pytest.mark.unit
    def test_deploy_success(self, manager):
        result = manager.deploy("demo", {})
        assert result.success is True
        assert result.template == "demo"
    
    @pytest.mark.unit  
    def test_deploy_invalid_template_raises_error(self, manager):
        with pytest.raises(TemplateNotFoundError):
            manager.deploy("nonexistent", {})
```

### Integration Test Example
```python
@pytest.mark.integration
@pytest.mark.docker
def test_docker_deployment_lifecycle():
    """Test complete Docker deployment lifecycle."""
    manager = DeploymentManager(backend_type="docker")
    
    # Deploy
    result = manager.deploy("demo", {"port": 8080})
    assert result.success is True
    
    # Verify running
    status = manager.get_deployment_status(result.deployment_id)
    assert status.is_running is True
    
    # Cleanup
    manager.undeploy(result.deployment_id)
```

## Gateway Development

### FastAPI Pattern
```python
from fastapi import FastAPI, HTTPException, Depends
from mcp_platform.gateway.auth import get_current_user
from mcp_platform.gateway.models import DeploymentRequest

app = FastAPI()

@app.post("/deploy")
async def deploy_template(
    request: DeploymentRequest,
    user = Depends(get_current_user)
):
    try:
        result = await deployment_manager.deploy(
            request.template_id, 
            request.config
        )
        return result
    except TemplateNotFoundError:
        raise HTTPException(status_code=404, detail="Template not found")
```

## CLI Development

### Typer Pattern
```python
import typer
from rich.console import Console

app = typer.Typer()
console = Console()

@app.command()
def deploy(
    template_id: str = typer.Argument(..., help="Template to deploy"),
    config_file: Optional[str] = typer.Option(None, help="Configuration file"),
    backend: str = typer.Option("docker", help="Deployment backend")
):
    """Deploy an MCP template."""
    try:
        manager = DeploymentManager(backend_type=backend)
        result = manager.deploy(template_id, config or {})
        
        if result.success:
            console.print(f"✅ Successfully deployed {template_id}", style="green")
        else:
            console.print(f"❌ Deployment failed: {result.error}", style="red")
            
    except Exception as e:
        console.print(f"❌ Error: {e}", style="red")
        raise typer.Exit(1)
```

## Configuration Management

### Environment Variables
```python
# Reserved environment variables (see config_processor.py)
RESERVED_ENV_VARS = {
    'MCP_TEMPLATE_ID', 'MCP_TEMPLATE_NAME', 'MCP_TEMPLATE_VERSION',
    'MCP_IMAGE_NAME', 'MCP_CONTAINER_NAME', 'MCP_DEPLOYMENT_ID'
}

# Configuration processing
config = {
    "database_url": "${DATABASE_URL}",
    "api_key": "${API_KEY}",
    "port": "${PORT:-8080}"
}
```

### Template Override Pattern
```python
# Double underscore notation for nested overrides
config_overrides = {
    "database__host": "localhost",      # database.host = "localhost"
    "auth__providers__oauth__enabled": True  # auth.providers.oauth.enabled = True
}
```

## Performance and Resource Management

### Async Patterns
```python
import asyncio
import aiohttp
from contextlib import asynccontextmanager

@asynccontextmanager
async def http_client():
    """Managed HTTP client context."""
    async with aiohttp.ClientSession() as session:
        yield session

async def deploy_multiple_templates(templates: List[str]):
    """Deploy multiple templates concurrently."""
    tasks = [deploy_template_async(template) for template in templates]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return results
```

### Resource Management
```python
from contextlib import contextmanager

@contextmanager
def deployment_context(deployment_id: str):
    """Ensure proper cleanup of deployment resources."""
    try:
        yield deployment_id
    finally:
        # Cleanup logic
        cleanup_deployment(deployment_id)
```

## Security Considerations

### Input Validation
```python
from pydantic import BaseModel, validator

class DeploymentConfig(BaseModel):
    template_id: str
    config: Dict[str, Any]
    
    @validator('template_id')
    def validate_template_id(cls, v):
        if not v or not v.isalnum():
            raise ValueError('Template ID must be alphanumeric')
        return v
```

### Authentication Pattern
```python
from mcp_platform.gateway.auth import verify_token

async def protected_endpoint(
    authorization: str = Header(...),
    user_info = Depends(verify_token)
):
    # Protected endpoint logic
    pass
```

## Troubleshooting and Debugging

### Logging Pattern
```python
import logging

# Use structured logging
logger = logging.getLogger(__name__)

def deploy_template(template_id: str, config: Dict[str, Any]):
    logger.info(
        "Starting deployment", 
        extra={
            "template_id": template_id,
            "config_keys": list(config.keys()),
            "operation": "deploy"
        }
    )
    
    try:
        result = perform_deployment(template_id, config)
        logger.info(
            "Deployment completed", 
            extra={
                "template_id": template_id,
                "success": result.success,
                "deployment_id": result.deployment_id
            }
        )
        return result
        
    except Exception as e:
        logger.error(
            "Deployment failed",
            extra={
                "template_id": template_id,
                "error": str(e),
                "error_type": type(e).__name__
            },
            exc_info=True
        )
        raise
```

### Error Handling Best Practices
```python
def handle_deployment_error(e: Exception, template_id: str) -> DeploymentResult:
    """Standardized error handling for deployment operations."""
    if isinstance(e, TemplateNotFoundError):
        return DeploymentResult(
            success=False,
            error=f"Template '{template_id}' not found",
            error_type="template_not_found"
        )
    elif isinstance(e, InvalidConfigurationError):
        return DeploymentResult(
            success=False,
            error=f"Invalid configuration: {e}",
            error_type="invalid_config"
        )
    else:
        logger.exception("Unexpected deployment error")
        return DeploymentResult(
            success=False,
            error="Internal deployment error",
            error_type="internal_error"
        )
```

## Integration Points

### MCP Client Integration
```python
from mcp_platform.client import MCPClient

async def test_deployed_server(deployment_result: DeploymentResult):
    """Validate deployed MCP server functionality."""
    client = MCPClient(
        base_url=f"http://localhost:{deployment_result.port}",
        timeout=30
    )
    
    try:
        tools = await client.list_tools()
        logger.info(f"Server has {len(tools)} tools available")
        
        # Test tool execution
        if tools:
            result = await client.call_tool(tools[0]["name"], {})
            logger.info(f"Tool execution successful: {result}")
            
    finally:
        await client.close()
```

### Docker Integration Pattern
```python
from mcp_platform.backends.docker import DockerDeploymentService

def deploy_with_custom_volumes(template_id: str, config: Dict[str, Any]):
    """Deploy with custom volume mounting."""
    backend = DockerDeploymentService()
    
    # Add volume mounts to config
    config.setdefault("volumes", {})
    config["volumes"].update({
        "/host/data": "/container/data",
        "/host/logs": "/container/logs"
    })
    
    return backend.deploy(template_id, config)
```

## Continuous Integration

### GitHub Actions Integration
The project uses a comprehensive CI/CD pipeline with multiple stages:

1. **Quick Validation**: Basic imports and fast unit tests
2. **Code Quality**: Black, isort, flake8, bandit
3. **Unit Tests**: Fast, isolated tests
4. **Docker Tests**: Docker-specific functionality
5. **Kubernetes Tests**: K8s deployment validation
6. **Template Tests**: Individual template validation
7. **Integration Tests**: Full system integration
8. **Coverage Check**: Minimum 50% coverage requirement
9. **Multi-Python Tests**: Python 3.10, 3.11, 3.12 compatibility

### Local CI Simulation
```bash
# Simulate CI pipeline locally
make ci-quick          # Quick validation
make ci-full           # Complete CI simulation
make pre-release       # Pre-release validation
```

## Documentation Standards

### Code Documentation
```python
class TemplateManager:
    """
    Centralized template management operations.
    
    Provides unified interface for template discovery, validation, and metadata
    operations that can be shared between CLI and MCPClient implementations.
    
    Attributes:
        template_discovery: Template discovery service
        backend: Deployment backend instance
        cache_manager: Template metadata caching
        
    Example:
        >>> manager = TemplateManager(backend_type="docker")
        >>> templates = manager.list_templates()
        >>> result = manager.validate_template("demo")
    """
```

### API Documentation
- Use comprehensive docstrings with Args, Returns, Raises sections
- Include usage examples in docstrings
- Document exception conditions and error handling
- Provide type hints for all parameters and return values

## Migration and Compatibility

### Version Compatibility
- Maintain backward compatibility within major versions
- Use deprecation warnings for breaking changes
- Support multiple Python versions (3.10+)
- Follow semantic versioning principles

### Template Migration
```python
def migrate_template_config(old_config: Dict, version: str) -> Dict:
    """Migrate template configuration between versions."""
    if version == "1.0.0":
        # Migration logic for v1.0.0
        new_config = old_config.copy()
        if "old_field" in new_config:
            new_config["new_field"] = new_config.pop("old_field")
        return new_config
    return old_config
```

## Summary

When working on MCP Platform:

1. **Follow the established architecture patterns** - use backend abstraction, centralized managers
2. **Maintain high code quality** - formatting, linting, type hints, comprehensive tests
3. **Use proper error handling** - custom exceptions, structured logging, graceful degradation
4. **Test thoroughly** - unit tests, integration tests, template validation
5. **Document comprehensively** - docstrings, examples, architecture decisions
6. **Follow security best practices** - input validation, authentication, resource management
7. **Consider performance** - async patterns, resource cleanup, caching strategies

The codebase emphasizes production readiness, maintainability, and developer experience. Always consider the impact on deployment scenarios (Docker, Kubernetes) and template ecosystem when making changes.