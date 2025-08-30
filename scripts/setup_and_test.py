#!/usr/bin/env python3
"""
Comprehensive setup and test script for the Enhanced MCP Gateway System.

This script handles:
1. Environment setup and dependency checking
2. Database initialization and migrations
3. Test execution with comprehensive coverage
4. Integration validation
5. Performance benchmarking

Usage:
    python scripts/setup_and_test.py --help
    python scripts/setup_and_test.py --setup-only
    python scripts/setup_and_test.py --test-only
    python scripts/setup_and_test.py --full
"""

import argparse
import asyncio
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from typing import Dict, List, Optional

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


class Colors:
    """ANSI color codes for terminal output."""

    HEADER = "\033[95m"
    OKBLUE = "\033[94m"
    OKCYAN = "\033[96m"
    OKGREEN = "\033[92m"
    WARNING = "\033[93m"
    FAIL = "\033[91m"
    ENDC = "\033[0m"
    BOLD = "\033[1m"
    UNDERLINE = "\033[4m"


class SetupAndTestManager:
    """Manages setup and testing for the MCP Gateway system."""

    def __init__(self, verbose: bool = False):
        """Initialize the setup and test manager."""
        self.verbose = verbose
        self.project_root = project_root
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def log(self, message: str, level: str = "INFO") -> None:
        """Log a message with appropriate formatting."""
        color_map = {
            "INFO": Colors.OKBLUE,
            "SUCCESS": Colors.OKGREEN,
            "WARNING": Colors.WARNING,
            "ERROR": Colors.FAIL,
            "HEADER": Colors.HEADER,
        }

        color = color_map.get(level, Colors.ENDC)
        timestamp = time.strftime("%H:%M:%S")
        print(f"{color}[{timestamp}] {level}: {message}{Colors.ENDC}")

    def run_command(
        self, cmd: List[str], description: str, cwd: Optional[Path] = None
    ) -> bool:
        """Run a command and return success status."""
        self.log(f"Running: {description}", "INFO")
        if self.verbose:
            self.log(f"Command: {' '.join(cmd)}", "INFO")

        try:
            result = subprocess.run(
                cmd,
                cwd=cwd or self.project_root,
                capture_output=not self.verbose,
                text=True,
                check=False,
            )

            if result.returncode == 0:
                self.log(f"✅ {description} completed successfully", "SUCCESS")
                return True
            else:
                error_msg = (
                    f"❌ {description} failed with exit code {result.returncode}"
                )
                if result.stderr:
                    error_msg += f"\nError: {result.stderr}"
                self.log(error_msg, "ERROR")
                self.errors.append(f"{description}: {error_msg}")
                return False

        except Exception as e:
            error_msg = f"❌ {description} failed with exception: {e}"
            self.log(error_msg, "ERROR")
            self.errors.append(f"{description}: {error_msg}")
            return False

    def check_python_version(self) -> bool:
        """Check if Python version is compatible."""
        self.log("Checking Python version", "HEADER")

        version = sys.version_info
        if version.major != 3 or version.minor < 8:
            self.log(
                f"❌ Python 3.8+ required, found {version.major}.{version.minor}",
                "ERROR",
            )
            return False

        self.log(
            f"✅ Python {version.major}.{version.minor}.{version.micro} is compatible",
            "SUCCESS",
        )
        return True

    def check_dependencies(self) -> bool:
        """Check if required dependencies are available."""
        self.log("Checking dependencies", "HEADER")

        required_packages = [
            "pydantic",
            "sqlmodel",
            "sqlalchemy",
            "fastapi",
            "passlib",
            "python-jose",
            "pytest",
            "pytest-cov",
            "pytest-asyncio",
        ]

        missing_packages = []

        for package in required_packages:
            try:
                __import__(package.replace("-", "_"))
                self.log(f"✅ {package} is available", "SUCCESS")
            except ImportError:
                self.log(f"❌ {package} is missing", "ERROR")
                missing_packages.append(package)

        if missing_packages:
            self.log(f"Missing packages: {', '.join(missing_packages)}", "WARNING")
            return False

        return True

    def install_dependencies(self) -> bool:
        """Install required dependencies."""
        self.log("Installing dependencies", "HEADER")

        # Install the package in development mode
        cmd = [sys.executable, "-m", "pip", "install", "-e", ".", "--upgrade"]
        if not self.run_command(cmd, "Install package in development mode"):
            return False

        # Install additional development dependencies
        dev_deps = [
            "fastapi[all]",
            "sqlmodel",
            "sqlalchemy[asyncio]",
            "python-jose[cryptography]",
            "passlib[bcrypt]",
            "python-multipart",
            "pytest",
            "pytest-cov",
            "pytest-asyncio",
            "pytest-mock",
            "aiohttp",
            "httpx",
        ]

        cmd = [sys.executable, "-m", "pip", "install"] + dev_deps + ["--upgrade"]
        return self.run_command(cmd, "Install development dependencies")

    async def setup_database(self) -> bool:
        """Set up the database for testing."""
        self.log("Setting up database", "HEADER")

        try:
            # Import after dependencies are installed
            from mcp_platform.gateway.auth import AuthManager
            from mcp_platform.gateway.database import DatabaseManager

            # Use temporary database for testing
            db_path = tempfile.mktemp(suffix=".db")
            db_url = f"sqlite:///{db_path}"

            self.log(f"Creating test database at {db_path}", "INFO")

            # Initialize database
            db_manager = DatabaseManager(database_url=db_url)
            await db_manager.initialize()

            # Initialize auth manager
            auth_manager = AuthManager(db_manager=db_manager)
            await auth_manager.initialize()

            # Create test admin user
            test_admin = await auth_manager.create_user(
                username="admin",
                email="admin@example.com",
                password="admin123",
                role="admin",
            )

            self.log(f"✅ Created test admin user: {test_admin.username}", "SUCCESS")

            # Create test API key
            api_key = await auth_manager.create_api_key(
                user_id=test_admin.id, name="test_key", scopes=["read", "write"]
            )

            self.log(f"✅ Created test API key: {api_key.name}", "SUCCESS")

            # Clean up
            await db_manager.close()
            os.unlink(db_path)

            self.log("✅ Database setup test completed successfully", "SUCCESS")
            return True

        except Exception as e:
            self.log(f"❌ Database setup failed: {e}", "ERROR")
            self.errors.append(f"Database setup: {e}")
            return False

    def run_unit_tests(self) -> bool:
        """Run unit tests with coverage."""
        self.log("Running unit tests", "HEADER")

        cmd = [
            sys.executable,
            "-m",
            "pytest",
            "tests/test_unit/",
            "--cov=mcp_platform.gateway",
            "--cov-report=html:htmlcov",
            "--cov-report=xml:coverage.xml",
            "--cov-report=term-missing",
            "--cov-fail-under=80",
            "-v" if self.verbose else "--tb=short",
        ]

        return self.run_command(cmd, "Unit tests with coverage")

    def run_integration_tests(self) -> bool:
        """Run integration tests."""
        self.log("Running integration tests", "HEADER")

        cmd = [
            sys.executable,
            "-m",
            "pytest",
            "tests/test_integration/",
            "-v" if self.verbose else "--tb=short",
            "--timeout=60",
        ]

        return self.run_command(cmd, "Integration tests")

    def run_existing_tests(self) -> bool:
        """Run existing test suite to ensure nothing is broken."""
        self.log("Running existing test suite", "HEADER")

        cmd = [
            sys.executable,
            "-m",
            "pytest",
            "tests/",
            "--ignore=tests/test_unit/test_gateway_v2/",
            "--ignore=tests/test_integration/",
            "-v" if self.verbose else "--tb=short",
        ]

        return self.run_command(cmd, "Existing test suite")

    def validate_imports(self) -> bool:
        """Validate that all enhanced gateway modules can be imported."""
        self.log("Validating enhanced gateway imports", "HEADER")

        modules_to_test = [
            "mcp_platform.gateway.models",
            "mcp_platform.gateway.database",
            "mcp_platform.gateway.auth",
            "mcp_platform.gateway.client",
            "mcp_platform.gateway.registry_v2",
            "mcp_platform.gateway.gateway_server_v2",
        ]

        for module in modules_to_test:
            try:
                __import__(module)
                self.log(f"✅ {module} imported successfully", "SUCCESS")
            except Exception as e:
                self.log(f"❌ Failed to import {module}: {e}", "ERROR")
                self.errors.append(f"Import {module}: {e}")
                return False

        return True

    def run_performance_tests(self) -> bool:
        """Run basic performance tests."""
        self.log("Running performance tests", "HEADER")

        cmd = [
            sys.executable,
            "-m",
            "pytest",
            "-k",
            "performance",
            "--timeout=120",
            "-v" if self.verbose else "--tb=short",
        ]

        return self.run_command(cmd, "Performance tests")

    def check_code_quality(self) -> bool:
        """Check code quality with linting tools."""
        self.log("Checking code quality", "HEADER")

        # Check if tools are available
        tools = ["black", "isort", "mypy"]
        available_tools = []

        for tool in tools:
            try:
                result = subprocess.run([tool, "--version"], capture_output=True)
                if result.returncode == 0:
                    available_tools.append(tool)
                    self.log(f"✅ {tool} is available", "SUCCESS")
                else:
                    self.log(f"⚠️  {tool} is not available", "WARNING")
            except FileNotFoundError:
                self.log(f"⚠️  {tool} is not installed", "WARNING")

        success = True

        # Run available tools
        if "black" in available_tools:
            cmd = ["black", "--check", "mcp_platform/gateway/", "tests/"]
            if not self.run_command(cmd, "Black code formatting check"):
                success = False

        if "isort" in available_tools:
            cmd = ["isort", "--check-only", "mcp_platform/gateway/", "tests/"]
            if not self.run_command(cmd, "Import sorting check"):
                success = False

        if "mypy" in available_tools:
            cmd = ["mypy", "mcp_platform/gateway/", "--ignore-missing-imports"]
            # Note: mypy might have warnings, so we don't fail on this
            self.run_command(cmd, "Type checking with mypy")

        return success

    def generate_test_report(self) -> None:
        """Generate a comprehensive test report."""
        self.log("Generating test report", "HEADER")

        report_lines = [
            "# Enhanced MCP Gateway Test Report",
            f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            "## Summary",
            f"- Total Errors: {len(self.errors)}",
            f"- Total Warnings: {len(self.warnings)}",
            "",
        ]

        if self.errors:
            report_lines.extend(["## Errors", ""])
            for error in self.errors:
                report_lines.append(f"- {error}")
            report_lines.append("")

        if self.warnings:
            report_lines.extend(["## Warnings", ""])
            for warning in self.warnings:
                report_lines.append(f"- {warning}")
            report_lines.append("")

        # Coverage information
        coverage_file = self.project_root / "coverage.xml"
        if coverage_file.exists():
            report_lines.extend(
                [
                    "## Coverage Report",
                    "Coverage report generated in coverage.xml and htmlcov/",
                    "",
                ]
            )

        # Write report
        report_file = self.project_root / "test_report.md"
        report_file.write_text("\n".join(report_lines))

        self.log(f"Test report written to {report_file}", "SUCCESS")

    async def run_full_setup(self) -> bool:
        """Run complete setup process."""
        self.log("=== Starting Full Setup Process ===", "HEADER")

        success = True

        # Environment checks
        if not self.check_python_version():
            success = False

        # Dependency management
        if not self.check_dependencies():
            self.log("Installing missing dependencies...", "INFO")
            if not self.install_dependencies():
                success = False

        # Import validation
        if not self.validate_imports():
            success = False

        # Database setup
        if not await self.setup_database():
            success = False

        return success

    async def run_full_tests(self) -> bool:
        """Run complete test suite."""
        self.log("=== Starting Full Test Suite ===", "HEADER")

        success = True

        # Run existing tests first to ensure we didn't break anything
        if not self.run_existing_tests():
            success = False

        # Run new unit tests
        if not self.run_unit_tests():
            success = False

        # Run integration tests
        if not self.run_integration_tests():
            success = False

        # Run performance tests
        if not self.run_performance_tests():
            success = False

        # Code quality checks
        if not self.check_code_quality():
            # Don't fail on code quality issues, just warn
            self.warnings.append("Code quality checks had issues")

        return success

    async def run_all(self) -> bool:
        """Run complete setup and test process."""
        self.log("=== Starting Complete Setup and Test Process ===", "HEADER")

        start_time = time.time()

        # Run setup
        setup_success = await self.run_full_setup()
        if not setup_success:
            self.log("❌ Setup failed, skipping tests", "ERROR")
            return False

        # Run tests
        test_success = await self.run_full_tests()

        # Generate report
        self.generate_test_report()

        end_time = time.time()
        duration = end_time - start_time

        self.log(f"=== Process completed in {duration:.2f} seconds ===", "HEADER")

        if setup_success and test_success:
            self.log("🎉 All setup and tests completed successfully!", "SUCCESS")
            return True
        else:
            self.log(
                "💥 Some steps failed. Check the test report for details.", "ERROR"
            )
            return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Enhanced MCP Gateway Setup and Test Script",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/setup_and_test.py --full
  python scripts/setup_and_test.py --setup-only
  python scripts/setup_and_test.py --test-only
  python scripts/setup_and_test.py --unit-tests-only
        """,
    )

    parser.add_argument(
        "--setup-only",
        action="store_true",
        help="Run only setup steps (dependencies, database, validation)",
    )
    parser.add_argument(
        "--test-only",
        action="store_true",
        help="Run only test steps (assumes setup is complete)",
    )
    parser.add_argument(
        "--unit-tests-only", action="store_true", help="Run only unit tests"
    )
    parser.add_argument(
        "--integration-tests-only",
        action="store_true",
        help="Run only integration tests",
    )
    parser.add_argument(
        "--existing-tests-only",
        action="store_true",
        help="Run only existing test suite",
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="Run complete setup and test process (default)",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose output"
    )

    args = parser.parse_args()

    # Default to full process if no specific option is chosen
    if not any(
        [
            args.setup_only,
            args.test_only,
            args.unit_tests_only,
            args.integration_tests_only,
            args.existing_tests_only,
        ]
    ):
        args.full = True

    manager = SetupAndTestManager(verbose=args.verbose)

    async def run_selected_operations():
        """Run the selected operations."""
        success = True

        if args.setup_only:
            success = await manager.run_full_setup()
        elif args.test_only:
            success = await manager.run_full_tests()
        elif args.unit_tests_only:
            success = manager.run_unit_tests()
        elif args.integration_tests_only:
            success = manager.run_integration_tests()
        elif args.existing_tests_only:
            success = manager.run_existing_tests()
        elif args.full:
            success = await manager.run_all()

        # Always generate report
        manager.generate_test_report()

        return success

    try:
        success = asyncio.run(run_selected_operations())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        manager.log("❌ Process interrupted by user", "ERROR")
        sys.exit(1)
    except Exception as e:
        manager.log(f"❌ Unexpected error: {e}", "ERROR")
        sys.exit(1)


if __name__ == "__main__":
    main()
