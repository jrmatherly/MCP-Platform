"""
Enhanced Test Runner for MCP Gateway System.

This is the new comprehensive test runner with enhanced features for
the upgraded MCP Gateway system.
"""

import argparse
import subprocess
import sys
from pathlib import Path


def run_command(cmd, description):
    """Run a command and handle errors."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'='*60}")

    result = subprocess.run(cmd, capture_output=False)
    if result.returncode != 0:
        print(f"❌ {description} failed with exit code {result.returncode}")
        return False
    else:
        print(f"✅ {description} completed successfully")
        return True


def run_unit_tests(verbose=False, coverage=True):
    """Run unit tests."""
    cmd = ["python", "-m", "pytest", "tests/test_unit/"]

    if verbose:
        cmd.append("-v")

    if coverage:
        cmd.extend(
            [
                "--cov=mcp_platform.gateway",
                "--cov-report=html:htmlcov",
                "--cov-report=xml:coverage.xml",
                "--cov-report=term-missing",
            ]
        )

    cmd.extend(["--tb=short"])

    return run_command(cmd, "Unit Tests")


def run_integration_tests(verbose=False):
    """Run integration tests."""
    cmd = ["python", "-m", "pytest", "tests/test_integration/"]

    if verbose:
        cmd.append("-v")

    cmd.extend(["--tb=short"])

    return run_command(cmd, "Integration Tests")


def run_all_tests(verbose=False, coverage=True):
    """Run all tests."""
    cmd = ["python", "-m", "pytest", "tests/"]

    if verbose:
        cmd.append("-v")

    if coverage:
        cmd.extend(
            [
                "--cov=mcp_platform",
                "--cov-report=html:htmlcov",
                "--cov-report=xml:coverage.xml",
                "--cov-report=term-missing",
                "--cov-fail-under=80",
            ]
        )

    cmd.extend(["--tb=short"])

    return run_command(cmd, "All Tests")


def main():
    """Main test runner function."""
    parser = argparse.ArgumentParser(description="MCP Gateway Test Runner")
    parser.add_argument(
        "command", choices=["unit", "integration", "all"], help="Test command to run"
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument(
        "--no-coverage", action="store_true", help="Skip coverage reporting"
    )

    args = parser.parse_args()

    success = True

    if args.command == "unit":
        success = run_unit_tests(args.verbose, not args.no_coverage)
    elif args.command == "integration":
        success = run_integration_tests(args.verbose)
    elif args.command == "all":
        success = run_all_tests(args.verbose, not args.no_coverage)

    if success:
        print(f"\n🎉 {args.command.title()} tests completed successfully!")
        sys.exit(0)
    else:
        print(f"\n💥 {args.command.title()} tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
