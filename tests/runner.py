"""
Test runner script for the enhanced MCP Gateway system.
Provides convenient commands to run different test suites with proper coverage reporting.
"""

import subprocess
import sys
from pathlib import Path
from typing import Any


def run_command(cmd, description):
    """Run a command and handle errors."""
    print(f"\n{'=' * 60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print(f"{'=' * 60}")

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
    cmd = ["python", "-m", "pytest", "-m", "integration"]

    if verbose:
        cmd.append("-v")

    cmd.extend(["--tb=short"])

    return run_command(cmd, "Integration Tests")


def run_docker_tests(self, verbose: bool = True) -> dict[str, Any]:
    """Run Docker-dependent tests.

    Args:
        verbose: Whether to show verbose output

    Returns:
        Dict containing test results
    """
    cmd = [sys.executable, "-m", "pytest", "-m", "docker", "--tb=short"]

    if verbose:
        cmd.append("-v")

    return self._run_pytest(cmd, "Docker Tests")


def run_e2e_tests(self, verbose: bool = True) -> dict[str, Any]:
    """Run end-to-end tests.

    Args:
        verbose: Whether to show verbose output

    Returns:
        Dict containing test results
    """
    cmd = [sys.executable, "-m", "pytest", "-m", "e2e", "--tb=long"]

    if verbose:
        cmd.append("-v")

    return self._run_pytest(cmd, "End-to-End Tests")


def run_template_tests(
    self, template_name: str | None = None, verbose: bool = True
) -> dict[str, Any]:
    """Run template-specific tests.

    Args:
        template_name: Specific template to test (None for all)
        verbose: Whether to show verbose output

    Returns:
        Dict containing test results
    """
    if template_name:
        test_path = f"templates/{template_name}/tests"
        cmd = [sys.executable, "-m", "pytest", test_path, "--tb=short"]
    else:
        cmd = [sys.executable, "-m", "pytest", "-m", "template", "--tb=short"]

    if verbose:
        cmd.append("-v")

    return self._run_pytest(cmd, f"Template Tests ({template_name or 'all'})")


def run_all_tests(
    self,
    include_slow: bool = False,
    include_docker: bool = False,
    verbose: bool = True,
) -> dict[str, Any]:
    """Run all tests with comprehensive coverage.

    Args:
        include_slow: Whether to include slow tests
        include_docker: Whether to include Docker-dependent tests
        verbose: Whether to show verbose output

    Returns:
        Dict containing comprehensive test results
    """
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "--cov=mcp_platform",
        "--cov=templates",
        "--cov-report=term-missing",
        "--cov-report=html",
        "--cov-report=xml",
        "--cov-fail-under=15",
    ]

    # Build marker expression
    markers = []
    if not include_slow:
        markers.append("not slow")
    if not include_docker:
        markers.append("not docker")

    if markers:
        cmd.extend(["-m", " and ".join(markers)])

    if verbose:
        cmd.append("-v")

    return self._run_pytest(cmd, "All Tests")


def run_specific_test_file(self, test_file: str, verbose: bool = True) -> dict[str, Any]:
    """Run a specific test file.

    Args:
        test_file: Path to the test file
        verbose: Whether to show verbose output

    Returns:
        Dict containing test results
    """
    cmd = [sys.executable, "-m", "pytest", test_file, "--tb=short"]

    if verbose:
        cmd.append("-v")

    return self._run_pytest(cmd, f"Test File: {test_file}")


def run_coverage_only(self) -> dict[str, Any]:
    """Run tests purely for coverage measurement.

    Returns:
        Dict containing coverage results
    """
    cmd = [
        sys.executable,
        "-m",
        "pytest",
        "--cov=mcp_platform",
        "--cov=templates",
        "--cov-report=term-missing",
        "--cov-report=html",
        "--cov-report=xml",
        "--quiet",
        "-x",  # Stop on first failure
    ]

    return self._run_pytest(cmd, "Coverage Analysis")


def generate_coverage_report(self) -> Path:
    """Generate detailed coverage report.

    Returns:
        Path to the generated HTML coverage report
    """
    # Run coverage
    subprocess.run(
        [
            sys.executable,
            "-m",
            "coverage",
            "html",
            "--directory",
            str(self.coverage_dir),
        ],
        check=True,
    )

    return self.coverage_dir / "index.html"


def check_test_quality(self) -> dict[str, Any]:
    """Check test quality metrics.

    Returns:
        Dict containing quality metrics
    """
    metrics = {
        "test_files": len(list(self.test_dir.glob("**/test_*.py"))),
        "test_coverage": self._get_coverage_percentage(),
        "missing_tests": self._find_missing_tests(),
        "duplicate_tests": self._find_duplicate_tests(),
    }

    return metrics


def _run_pytest(self, cmd: list[str], test_type: str) -> dict[str, Any]:
    """Run pytest command and capture results.

    Args:
        cmd: Command to run
        test_type: Type of tests being run

    Returns:
        Dict containing test results
    """
    print(f"\n=== Running {test_type} ===")
    print(f"Command: {' '.join(cmd)}")

    try:
        result = subprocess.run(
            cmd,
            cwd=self.root_dir,
            capture_output=True,
            text=True,
            timeout=600,  # 10 minute timeout
        )

        return {
            "test_type": test_type,
            "success": result.returncode == 0,
            "return_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "command": cmd,
        }

    except subprocess.TimeoutExpired:
        return {
            "test_type": test_type,
            "success": False,
            "return_code": -1,
            "error": "Test execution timed out",
            "command": cmd,
        }
    except Exception as e:
        return {
            "test_type": test_type,
            "success": False,
            "return_code": -1,
            "error": str(e),
            "command": cmd,
        }


def _get_coverage_percentage(self) -> float | None:
    """Get current test coverage percentage.

    Returns:
        Coverage percentage or None if not available
    """
    coverage_file = self.root_dir / "coverage.xml"
    if not coverage_file.exists():
        return None

    try:
        import xml.etree.ElementTree as ET

        tree = ET.parse(coverage_file)
        root = tree.getroot()

        coverage_elem = root.find(".//coverage")
        if coverage_elem is not None:
            return float(coverage_elem.get("line-rate", 0)) * 100

    except Exception:
        pass

    return None


def _find_missing_tests(self) -> list[str]:
    """Find source files that don't have corresponding tests.

    Returns:
        List of source files missing tests
    """
    missing_tests = []

    # Check mcp_platform module
    mcp_platform_dir = self.root_dir / "mcp_platform"
    if mcp_platform_dir.exists():
        for py_file in mcp_platform_dir.glob("*.py"):
            if py_file.name.startswith("_"):
                continue

            test_file = self.test_dir / f"test_{py_file.stem}.py"
            if not test_file.exists():
                missing_tests.append(str(py_file.relative_to(self.root_dir)))

    return missing_tests


def _find_duplicate_tests(self) -> list[str]:
    """Find potentially duplicate test functions.

    Returns:
        List of potentially duplicate tests
    """
    test_names = {}
    duplicates = []

    for test_file in self.test_dir.glob("**/test_*.py"):
        try:
            content = test_file.read_text()
            for line_num, line in enumerate(content.split("\n"), 1):
                if line.strip().startswith("def test_"):
                    test_name = line.split("(")[0].replace("def ", "")

                    if test_name in test_names:
                        duplicates.append(
                            f"{test_name} in {test_file} and {test_names[test_name]}"
                        )
                    else:
                        test_names[test_name] = f"{test_file}:{line_num}"

        except Exception:
            continue

    return duplicates


def main():
    """Main function for running tests from command line."""
    import argparse

    parser = argparse.ArgumentParser(description="Run MCP Template tests")
    parser.add_argument("--unit", action="store_true", help="Run unit tests only")
    parser.add_argument(
        "--integration", action="store_true", help="Run integration tests only"
    )
    parser.add_argument("--docker", action="store_true", help="Run Docker tests only")
    parser.add_argument("--e2e", action="store_true", help="Run end-to-end tests only")
    parser.add_argument("--template", help="Run tests for specific template")
    parser.add_argument("--file", help="Run specific test file")
    parser.add_argument(
        "--coverage", action="store_true", help="Run coverage analysis only"
    )
    parser.add_argument("--all", action="store_true", help="Run all tests")
    parser.add_argument("--include-slow", action="store_true", help="Include slow tests")
    parser.add_argument(
        "--include-docker", action="store_true", help="Include Docker tests"
    )
    parser.add_argument("--quiet", action="store_true", help="Reduce output verbosity")
    parser.add_argument(
        "--quality", action="store_true", help="Check test quality metrics"
    )

    args = parser.parse_args()

    verbose = not args.quiet

    results = []

    if args.unit:
        success = run_unit_tests(verbose)
        results.append(
            {
                "success": success,
                "test_type": "Unit Tests",
                "return_code": 0 if success else 1,
            }
        )
    elif args.integration:
        success = run_integration_tests(verbose)
        results.append(
            {
                "success": success,
                "test_type": "Integration Tests",
                "return_code": 0 if success else 1,
            }
        )
    elif args.docker:
        print("Docker tests not yet implemented")
        results.append({"success": False, "test_type": "Docker Tests", "return_code": 1})
    elif args.e2e:
        print("E2E tests not yet implemented")
        results.append({"success": False, "test_type": "E2E Tests", "return_code": 1})
    elif args.template:
        print(f"Template tests for {args.template} not yet implemented")
        results.append(
            {
                "success": False,
                "test_type": f"Template Tests ({args.template})",
                "return_code": 1,
            }
        )
    elif args.file:
        print(f"Specific file tests for {args.file} not yet implemented")
        results.append(
            {"success": False, "test_type": f"File Tests ({args.file})", "return_code": 1}
        )
    elif args.coverage:
        success = run_unit_tests(verbose, coverage=True)
        results.append(
            {
                "success": success,
                "test_type": "Coverage Tests",
                "return_code": 0 if success else 1,
            }
        )
    elif args.quality:
        print("Test quality metrics not yet implemented")
        return
    elif args.all:
        success = run_unit_tests(verbose)
        results.append(
            {
                "success": success,
                "test_type": "All Tests",
                "return_code": 0 if success else 1,
            }
        )
    else:
        # Default: run unit tests
        success = run_unit_tests(verbose)
        results.append(
            {
                "success": success,
                "test_type": "Unit Tests",
                "return_code": 0 if success else 1,
            }
        )

    # Print results summary
    print("\n" + "=" * 60)
    print("TEST RESULTS SUMMARY")
    print("=" * 60)

    total_success = True
    for result in results:
        status = "✅ PASSED" if result["success"] else "❌ FAILED"
        print(f"{result['test_type']}: {status}")
        if not result["success"]:
            total_success = False
            print(f"  Return code: {result['return_code']}")
            if "error" in result:
                print(f"  Error: {result['error']}")
            if "stdout" in result:
                print(f"  Output: {result['stdout']}")
            if "stderr" in result:
                print(f"  Errors: {result['stderr']}")

    print("=" * 60)
    overall_status = "✅ ALL TESTS PASSED" if total_success else "❌ SOME TESTS FAILED"
    print(f"OVERALL: {overall_status}")

    sys.exit(0 if total_success else 1)


if __name__ == "__main__":
    main()
