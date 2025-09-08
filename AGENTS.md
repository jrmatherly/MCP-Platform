# AGENTS.md
This file provides guidance to AI coding assistants working in this repository.

**Note:** CLAUDE.md, .clinerules, .cursorrules, .windsurfrules, .replit.md, GEMINI.md, .github/copilot-instructions.md, and .idx/airules.md are symlinks to AGENTS.md in this project.

# MCP Platform

**MCP Platform** is a production-ready Python deployment system for Model Context Protocol (MCP) servers. It provides comprehensive infrastructure for deploying, configuring, and managing MCP server templates with multiple deployment backends (Docker, Kubernetes, Mock).

## Build & Commands

### Core Development Commands

**Installation & Setup:**
```bash
make install          # Install dependencies with uv sync
make install-dev      # Install in development mode with uv
make dev-setup        # Complete development environment setup
make uv-setup         # Install uv package manager
```

**Testing Commands:**
```bash
make test-quick       # Fast validation tests
make test-unit        # Unit tests (no external dependencies)
make test-integration # Integration tests (requires Docker)
make test-all         # Complete test suite
make test-template TEMPLATE=demo  # Test specific template
make test-templates   # Test all templates
```

**Code Quality (Ruff-based):**
```bash
make lint            # Run Ruff linting
make format          # Format code with Ruff
make lint-fix        # Auto-fix linting issues
make type-check      # Run mypy type checking
```

**CI/CD Simulation:**
```bash
make ci-quick        # Quick validation (linting + unit tests)
make ci-full         # Complete CI pipeline simulation
make pre-release     # Pre-release validation
```

**Docker & Deployment:**
```bash
make docker-build          # Build all containers
make docker-up             # Start production stack
make docker-up-dev         # Start development mode
make docker-up-monitoring  # Start with monitoring
make docker-down           # Stop all services
make docker-logs           # Follow logs
make docker-clean          # Clean resources
```

**Documentation & Build:**
```bash
make docs            # Build documentation
make docs-serve      # Serve documentation locally
make build           # Build package
make clean           # Clean build artifacts
```

### CLI Commands (mcpp/mcp-platform)
```bash
# Template management
mcpp list                           # List available templates
mcpp deploy demo                    # Deploy demo template
mcpp deploy filesystem --config allowed_dirs="/path/to/data"

# Deployment management
mcpp list --deployed               # List deployments
mcpp stop demo                     # Stop deployment
mcpp logs demo --follow           # View logs

# Template development
mcpp create my-template            # Create new template
mcpp deploy my-template --backend mock  # Test with mock backend
```

### Centralized Docker Deployment

**Docker Compose Setup (Root Level):**
```bash
# Copy and configure environment
cp .env.example .env
# Edit .env with your configuration

# Build and deploy with profiles
docker compose build                           # Build all containers
docker compose --profile production up -d     # Full production stack
docker compose --profile gateway up -d        # Gateway only
docker compose --profile monitoring up -d     # With monitoring
docker compose --profile templates up -d      # Template examples

# Or use automation script
./scripts/docker-compose-up.sh production     # Automated deployment with validation
```

**Available Profiles:**
- `platform`: Core MCP Platform CLI container
- `gateway`: Production gateway (postgres + redis + gateway + nginx)
- `monitoring`: Prometheus + Grafana observability
- `production`: Full stack (gateway + monitoring)
- `templates`: Example deployments (demo + filesystem)
- `all`: Complete deployment (all services)

### Script Command Consistency
**Important**: The project has migrated from npm to Python/uv tooling. All commands are now make-based or mcpp CLI commands, not npm scripts.

## Code Style

### Formatting & Linting (Ruff-based - UPDATED)
- **Line Length**: 90 characters
- **Target Python Version**: 3.10+
- **Formatting**: Ruff format (replaces Black)
- **Import Sorting**: Ruff (replaces isort)
- **Linting**: Ruff with comprehensive rules (replaces flake8)
- **Security**: Bandit for security scanning
- **Type Checking**: mypy with strict configuration

**Key Style Rules:**
```python
# Import organization (enforced by Ruff)
# 1. Standard library imports
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

# 2. Third-party imports
import aiohttp
from rich.console import Console
from fastapi import FastAPI

# 3. Local imports
from mcp_platform.core import DeploymentManager, TemplateManager
from mcp_platform.backends import get_backend
from mcp_platform.core.exceptions import MCPException
```

### Naming Conventions
- **Functions/Variables**: `snake_case`
- **Classes**: `PascalCase`
- **Constants**: `UPPER_SNAKE_CASE`
- **Private attributes**: `_leading_underscore`
- **Template IDs**: `kebab-case` (e.g., "big-query", "open-elastic-search")

### Type Usage Patterns
- **Required**: Type hints for all public functions and classes
- **Optional parameters**: Use `Optional[Type]` explicitly
- **Return types**: Always specify, use `-> None` for procedures
- **Complex types**: Use `typing` module imports

### Error Handling Patterns
```python
# Use specific custom exceptions
from mcp_platform.core.exceptions import (
    TemplateNotFoundError,
    DeploymentError,
    InvalidConfigurationError
)

# Structured logging with context
logger = logging.getLogger(__name__)
logger.info(
    "Operation completed",
    extra={
        "operation": "deploy",
        "template_id": template_id,
        "success": result.success
    }
)
```

## Testing

### Framework & Tools
- **Framework**: pytest with comprehensive markers
- **Coverage Tool**: pytest-cov with 80% target, 50% minimum (CI enforced)
- **Markers**: `@pytest.mark.unit`, `@pytest.mark.integration`, `@pytest.mark.docker`, `@pytest.mark.kubernetes`

### Test File Patterns
- **Unit Tests**: `tests/test_unit/test_*.py`
- **Integration Tests**: `tests/test_integration/test_*.py`
- **Template Tests**: `templates/*/tests/test_*.py`

### Testing Conventions
```python
import pytest
from unittest.mock import Mock, patch

class TestDeploymentManager:
    @pytest.fixture
    def manager(self):
        return DeploymentManager(backend_type="mock")
    
    @pytest.mark.unit
    def test_deploy_success(self, manager):
        result = manager.deploy("demo", {})
        assert result.success is True
        assert result.template == "demo"
```

### Testing Philosophy
**When tests fail, fix the code, not the test.**

Key principles:
- **Tests should be meaningful** - Test actual functionality, not just side effects
- **Comprehensive coverage** - Unit tests for logic, integration tests for workflows
- **Proper isolation** - Use mock backend for unit tests, real backends for integration
- **Edge case testing** - Test error conditions and boundary cases
- **Template validation** - Each template must have its own test suite

## Security

### Input Validation
```python
from pydantic import BaseModel, validator

class DeploymentConfig(BaseModel):
    template_id: str
    config: Dict[str, Any]
    
    @validator('template_id')
    def validate_template_id(cls, v):
        if not v or not v.replace('-', '').replace('_', '').isalnum():
            raise ValueError('Template ID must be alphanumeric with hyphens/underscores')
        return v
```

### Environment Variable Security
- **Reserved Variables**: `MCP_TEMPLATE_ID`, `MCP_TEMPLATE_NAME`, `MCP_TEMPLATE_VERSION`, `MCP_IMAGE_NAME`, `MCP_CONTAINER_NAME`, `MCP_DEPLOYMENT_ID`
- **Variable Substitution**: `${DATABASE_URL}`, `${PORT:-8080}`
- **Configuration Validation**: All user inputs validated through Pydantic models

### Container Security
- **Isolation**: Each deployment runs in isolated containers
- **Volume Mounting**: Secure file system access patterns
- **Network Security**: Controlled port exposure and networking

## Directory Structure & File Organization

### Project Architecture
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
│   └── templates/                  # Built-in templates (demo, gitlab, etc.)
├── tools/                          # Tool management and probes
└── utils/                          # Shared utilities
```

### Available Templates
- **demo**: Hello world MCP server for testing
- **filesystem**: Secure file operations
- **gitlab**: GitLab API integration
- **github**: GitHub API integration  
- **trino**: Trino database connectivity
- **bigquery**: Google BigQuery integration
- **zendesk**: Customer support tools
- **slack**: Slack API integration
- **open-elastic-search**: Elasticsearch integration

### Reports Directory
ALL project reports and documentation should be saved to the `reports/` directory:

```
mcp-platform/
├── reports/              # All project reports and documentation
│   └── *.md             # Various report types
├── temp/                # Temporary files and debugging
└── [other directories]
```

### Report Generation Guidelines
**Important**: ALL reports should be saved to the `reports/` directory with descriptive names:

**Implementation Reports:**
- Phase validation: `PHASE_X_VALIDATION_REPORT.md`
- Implementation summaries: `IMPLEMENTATION_SUMMARY_[FEATURE].md`
- Feature completion: `FEATURE_[NAME]_REPORT.md`

**Testing & Analysis Reports:**
- Test results: `TEST_RESULTS_[DATE].md`
- Coverage reports: `COVERAGE_REPORT_[DATE].md`
- Performance analysis: `PERFORMANCE_ANALYSIS_[SCENARIO].md`
- Security scans: `SECURITY_SCAN_[DATE].md`

### Temporary Files & Debugging
All temporary files, debugging scripts, and test artifacts should be organized in a `/temp` folder:

**Guidelines:**
- Never commit files from `/temp` directory
- Use `/temp` for all debugging and analysis scripts created during development
- Clean up `/temp` directory regularly or use automated cleanup
- Include `/temp/` in `.gitignore` to prevent accidental commits

## Configuration

### Environment Setup
- **Python Version**: 3.10+ (supports 3.10, 3.11, 3.12, 3.13)
- **Package Manager**: uv (modern Python package manager)
- **Build System**: Hatch with setuptools_scm for versioning

### Required Dependencies
**Core:**
- **rich**: Terminal UI and console output
- **typer**: CLI framework
- **fastapi**: Web framework for gateway
- **pydantic**: Data validation
- **aiohttp**: Async HTTP client

**Development:**
- **pytest**: Testing framework with plugins
- **ruff**: Linting and formatting
- **mypy**: Type checking
- **bandit**: Security scanning

### Configuration Management

#### Network Configuration (Updated September 2025)
**Important**: The project has migrated from 172.x network ranges to 10.x ranges to avoid corporate network conflicts.

**Current Network Strategy:**
- **MCP_SUBNET**: `10.100.0.0/16` (environment configuration)
- **Runtime Networks**: `10.100-10.104.x.x/24` (dynamic subnet selection)
- **Conflict Avoidance**: Automatically detects and avoids existing network overlaps
- **Corporate Compatibility**: Avoids common enterprise network ranges (10.0.x.x, 10.1.x.x, 172.16-31.x.x)

**Key Configuration Files:**
- `.env.example`: Contains `MCP_SUBNET=10.100.0.0/16`
- `docker-compose.yml`: Uses `${MCP_SUBNET:-10.100.0.0/16}` for network IPAM
- `docker.py`: Implements intelligent subnet selection with validation

**Network Validation:**
The Docker backend includes `_validate_network_configuration()` which:
- Validates MCP_SUBNET environment variable format
- Ensures private IP range usage
- Provides warnings for suboptimal configurations
- Logs validation issues for debugging

**Docker Daemon Configuration:**
- **Not required** for basic MCP Platform operation
- Optional `daemon.json` enhancements available for enterprise environments
- Complete configuration guide: `/reports/DOCKER_DAEMON_NETWORK_CONFIGURATION.md`

#### Template Configuration Patterns
```python
# Template override pattern (double underscore notation)
config_overrides = {
    "database__host": "localhost",      # database.host = "localhost"
    "auth__providers__oauth__enabled": True  # auth.providers.oauth.enabled = True
}

# Environment variable substitution
config = {
    "database_url": "${DATABASE_URL}",
    "api_key": "${API_KEY}",
    "port": "${PORT:-8080}"
}
```

## Agent Delegation & Tool Execution

### ⚠️ MANDATORY: Always Delegate to Specialists & Execute in Parallel

**When specialized agents are available, you MUST use them instead of attempting tasks yourself.**

#### Architecture Analysis Specialists
- **system-architect**: For backend architecture and deployment patterns
- **performance-engineer**: For optimization and resource management
- **security-engineer**: For security analysis and vulnerability assessment
- **database-expert**: For data persistence and management patterns

#### Implementation Specialists
- **python-expert**: For Python-specific coding patterns and best practices
- **backend-architect**: For API design and service architecture
- **testing-expert**: For comprehensive testing strategies
- **refactoring-expert**: For code quality improvements

#### DevOps & Infrastructure
- **devops-expert**: For Docker, Kubernetes, and deployment strategies
- **docker-expert**: For container optimization and security
- **git-expert**: For version control and branching strategies

#### Key Principles
- **Agent Delegation**: Always check if a specialized agent exists for your task domain
- **Parallel Execution**: Send multiple Task tool calls in a single message for concurrent execution
- **Domain Expertise**: Use specialists for their deep knowledge of patterns and edge cases
- **Comprehensive Solutions**: Specialists provide more thorough, production-ready solutions

## Architecture Patterns

### Backend Abstraction Pattern
```python
from mcp_platform.backends import get_backend

backend = get_backend("docker")  # or "kubernetes", "mock"
result = backend.deploy(template_id, config)
```

### Template Management Pattern
```python
from mcp_platform.core import TemplateManager

manager = TemplateManager(backend_type="docker")
templates = manager.list_templates()
result = manager.validate_template(template_id)
```

### Configuration Processing Pattern
```python
from mcp_platform.core.config_processor import ConfigProcessor

processor = ConfigProcessor(template_config)
processed_config = processor.process_config(user_config)
```

### Async Resource Management
```python
from contextlib import asynccontextmanager
import aiohttp

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

## API Design Principles

### Function Documentation Standard
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

### CLI Pattern (Typer)
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

### FastAPI Pattern (Gateway)
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

## Migration Notes

### Recent Updates (Important for AI Agents)
The project has recently migrated from legacy tooling to modern alternatives:

**Package Management:**
- **OLD**: pip/pip-tools → **NEW**: uv
- **Commands**: All `pip install` → `uv sync`

**Code Quality:**
- **OLD**: black + isort + flake8 → **NEW**: ruff (unified tool)
- **Commands**: `make format` now uses `ruff format`, `make lint` uses `ruff check`

**Project Evolution:**
- **Previous**: "mcp-templates" → **Current**: "MCP Platform"
- **Architecture**: Enhanced with gateway layer, improved backend abstraction
- **Templates**: Expanded from basic examples to production-ready templates

## Summary

When working on MCP Platform:

1. **Follow modern Python practices** - Use uv, Ruff, type hints, and async patterns
2. **Use established architecture** - Backend abstraction, centralized managers, proper error handling
3. **Maintain production quality** - Comprehensive testing, security validation, performance considerations
4. **Leverage specialization** - Delegate to expert agents, use parallel execution for efficiency
5. **Document thoroughly** - Google-style docstrings, architecture decisions, usage examples
6. **Consider deployment scenarios** - Docker, Kubernetes compatibility, template ecosystem impact

The codebase emphasizes production readiness, modern Python practices, and developer experience. Always consider the impact on template deployments and the broader MCP ecosystem when making changes.