# Makefile for MCP Platform

.PHONY: help install test test-unit test-integration test-all test-quick clean lint format

# Default target
help:
	@echo "MCP Platform Development Commands"
	@echo "================================="
	@echo ""
	@echo "Setup:"
	@echo "  install       Install development dependencies"
	@echo "  install-dev   Install in development mode"
	@echo ""
	@echo "Testing:"
	@echo "  test-quick    Run quick validation tests"
	@echo "  test-unit     Run unit tests (fast, no Docker)"
	@echo "  test-integration  Run integration tests (requires Docker)"
	@echo "  test-all      Run all tests"
	@echo "  test          Alias for test-all"
	@echo "  test-template Run tests for a specific template (usage: make test-template TEMPLATE=file-server)"
	@echo "  test-templates Run tests for all templates"
	@echo ""
	@echo "Code Quality:"
	@echo "  lint          Run code linting"
	@echo "  format        Format code"
	@echo "  type-check    Run type checking"
	@echo ""
	@echo "Deployment:"
	@echo "  build         Build package"
	@echo "  clean         Clean build artifacts"
	@echo ""
	@echo "Local Development:"
	@echo "  deploy-test   Deploy a test template locally"
	@echo "  cleanup-test  Cleanup test deployments"

# Installation
install:
	uv sync

install-dev:
	uv sync --extra dev
	uv pip install -e .

# Testing
test-quick:
	@echo "🔬 Running quick validation tests..."
	uv run python tests/runner.py --unit

test-unit:
	@echo "🧪 Running unit tests..."
	uv run python tests/runner.py --unit

test-integration:
	@echo "🐳 Running integration tests..."
	uv run python tests/runner.py --integration

test-all:
	@echo "🚀 Running all tests..."
	uv run python tests/runner.py --all

test:
	uv run pytest tests

# Template-specific testing
test-template:
	@if [ -z "$(TEMPLATE)" ]; then \
		echo "❌ Please specify a template: make test-template TEMPLATE=file-server"; \
		exit 1; \
	fi; \
	if [ -d "templates/$(TEMPLATE)/tests" ]; then \
		echo "🧪 Running tests for template: $(TEMPLATE)"; \
		cd templates/$(TEMPLATE) && uv run pytest tests/ -v; \
	else \
		echo "❌ No tests found for template: $(TEMPLATE)"; \
		exit 1; \
	fi

test-templates:
	@echo "🧪 Running tests for all templates..."
	@for template in templates/*/; do \
		template_name=$$(basename "$$template"); \
		if [ -d "$$template/tests" ]; then \
			echo "Testing $$template_name..."; \
			cd "$$template" && uv run pytest tests/ -v --tb=short || exit 1; \
			cd - > /dev/null; \
		else \
			echo "⚠️  No tests found for $$template_name"; \
		fi \
	done; \
	echo "✅ All template tests completed!"

# Code quality
lint:
	@echo "🔍 Running code linting with Ruff..."
	uv run ruff check mcp_platform/ tests/
	uv run ruff format --check mcp_platform/ tests/

format:
	@echo "🎨 Formatting code with Ruff..."
	uv run ruff format mcp_platform/ tests/
	uv run ruff check --fix mcp_platform/ tests/

lint-fix:
	@echo "🔧 Auto-fixing linting issues..."
	uv run ruff check --fix mcp_platform/ tests/

type-check:
	@echo "🔬 Running type checking..."
	uv run mypy mcp_platform/ --ignore-missing-imports

# Package building
build:
	@echo "📦 Building package..."
	uv build

clean:
	@echo "🧹 Cleaning build artifacts..."
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf __pycache__/
	find . -name "*.pyc" -delete
	find . -name "*.pyo" -delete
	find . -name "__pycache__" -type d -exec rm -rf {} +

# Local development helpers
deploy-test:
	@echo "🚀 Deploying test template..."
	uv run python -m mcp_platform deploy file-server

cleanup-test:
	@echo "🧹 Cleaning up test deployments..."
	uv run python -m mcp_platform cleanup --all

list-templates:
	@echo "📋 Available templates:"
	uv run python -m mcp_platform list

# CI/CD simulation
ci-quick:
	@echo "⚡ Simulating CI quick tests..."
	make test-quick
	make lint

ci-full:
	@echo "🏗️ Simulating full CI pipeline..."
	uv sync --all-extras
	make test-quick
	make test-unit
	make lint
	make type-check
	make test-integration
	make build

# UV-specific commands
uv-setup:
	@echo "📦 Installing uv package manager..."
	curl -LsSf https://astral.sh/uv/install.sh | sh
	@echo "✅ uv installed successfully!"
	@echo "💡 You may need to restart your shell or run: source $$HOME/.cargo/env"

uv-lock:
	@echo "🔒 Updating uv.lock file..."
	uv lock

uv-upgrade:
	@echo "⬆️ Upgrading all dependencies..."
	uv lock --upgrade

# Development workflow
dev-setup:
	@echo "🔧 Setting up development environment with uv..."
	uv venv
	uv sync --all-extras
	@echo "✅ Development environment setup complete!"
	@echo "💡 Tip: Run 'source .venv/bin/activate' to activate the virtual environment"

dev-test: test-quick lint
	@echo "✅ Development tests passed!"

# Coverage reporting
coverage:
	@echo "📊 Generating coverage report..."
	uv run pytest tests/test_deployment_units.py -m unit --cov=mcp_platform --cov-report=html --cov-report=term
	@echo "📋 Coverage report generated in htmlcov/"

# Documentation
docs:
	@echo "📚 Building documentation..."
	uv run python scripts/build_docs.py

docs-serve:
	@echo "🌐 Serving documentation locally..."
	uv run mkdocs serve

docs-clean:
	@echo "🧹 Cleaning documentation build..."
	rm -rf site/
	find docs/templates/ -mindepth 1 -maxdepth 1 -type d ! -name ".pages" -exec rm -rf {} +

# Docker helpers
docker-check:
	@echo "🐳 Checking Docker availability..."
	docker --version
	docker ps

# Docker Compose helpers  
docker-build:
	@echo "🔨 Building Docker containers..."
	docker compose build

docker-up:
	@echo "🚀 Starting MCP Platform with Docker Compose..."
	./scripts/docker-compose-up.sh production

docker-up-dev:
	@echo "🛠️ Starting MCP Platform in development mode..."
	./scripts/docker-compose-up.sh dev

docker-up-monitoring:
	@echo "📊 Starting MCP Platform with monitoring..."
	./scripts/docker-compose-up.sh monitoring

docker-down:
	@echo "⏹️ Stopping MCP Platform services..."
	docker compose down

docker-logs:
	@echo "📋 Showing Docker Compose logs..."
	docker compose logs -f

docker-clean:
	@echo "🧹 Cleaning Docker resources..."
	docker compose down -v --remove-orphans
	docker system prune -f

# Template development
validate-templates:
	@echo "✅ Validating all templates..."
	uv run python -c "from mcp_platform import TemplateDiscovery; import sys; d = TemplateDiscovery(); t = d.discover_templates(); print(f'Found {len(t)} templates: {list(t.keys())}') if t else sys.exit(1)"

# Release helpers
pre-release: ci-full
	@echo "🚀 Pre-release checks complete!"

version:
	@echo "📊 Package version:"
	uv run python -c "import mcp_platform; print(getattr(mcp_platform, '__version__', 'unknown'))"
