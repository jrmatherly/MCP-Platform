#!/usr/bin/env python3
"""
Comprehensive test runner for BigQuery MCP Server.

This script runs all tests (unit and integration) and provides coverage reporting.
It ensures the BigQuery template meets the 70% coverage requirement.
"""

import json
import os
import subprocess
import sys
from pathlib import Path


def setup_test_environment():
    """Set up the test environment."""
    print("🔧 Setting up test environment...")

    # Get the BigQuery template directory
    bigquery_dir = Path(__file__).parent
    tests_dir = bigquery_dir / "tests"

    # Ensure tests directory exists
    tests_dir.mkdir(exist_ok=True)

    # Install test dependencies
    test_requirements = [
        "pytest>=6.0.0",
        "pytest-cov>=2.10.0",
        "pytest-mock>=3.0.0",
        "coverage>=5.0.0",
    ]

    print("📦 Installing test dependencies...")
    for req in test_requirements:
        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", req],
                check=True,
                capture_output=True,
            )
        except subprocess.CalledProcessError as e:
            print(f"⚠️  Warning: Could not install {req}: {e}")

    return bigquery_dir, tests_dir


def run_unit_tests(bigquery_dir, tests_dir):
    """Run unit tests with coverage."""
    print("\n🧪 Running unit tests...")

    # Change to the BigQuery directory
    original_cwd = os.getcwd()
    os.chdir(bigquery_dir)

    try:
        # Run pytest with coverage
        cmd = [
            sys.executable,
            "-m",
            "pytest",
            str(tests_dir / "test_bigquery_server.py"),
            "-v",
            "--cov=server",
            "--cov-report=term-missing",
            "--cov-report=json:coverage.json",
            "--tb=short",
        ]

        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)

        print("STDOUT:")
        print(result.stdout)

        if result.stderr:
            print("STDERR:")
            print(result.stderr)

        return result.returncode == 0, result.stdout, result.stderr

    except Exception as e:
        print(f"❌ Error running unit tests: {e}")
        return False, "", str(e)
    finally:
        os.chdir(original_cwd)


def run_integration_tests(bigquery_dir, tests_dir):
    """Run integration tests."""
    print("\n🔗 Running integration tests...")

    # Change to the BigQuery directory
    original_cwd = os.getcwd()
    os.chdir(bigquery_dir)

    try:
        # Run integration tests
        cmd = [
            sys.executable,
            "-m",
            "pytest",
            str(tests_dir / "test_bigquery_integration.py"),
            "-v",
            "--tb=short",
        ]

        print(f"Running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True)

        print("STDOUT:")
        print(result.stdout)

        if result.stderr:
            print("STDERR:")
            print(result.stderr)

        return result.returncode == 0, result.stdout, result.stderr

    except Exception as e:
        print(f"❌ Error running integration tests: {e}")
        return False, "", str(e)
    finally:
        os.chdir(original_cwd)


def analyze_coverage(bigquery_dir):
    """Analyze test coverage."""
    print("\n📊 Analyzing test coverage...")

    coverage_file = bigquery_dir / "coverage.json"

    if not coverage_file.exists():
        print("⚠️  No coverage report found")
        return False, 0.0

    try:
        with open(coverage_file, "r") as f:
            coverage_data = json.load(f)

        # Get overall coverage percentage
        total_coverage = coverage_data.get("totals", {}).get("percent_covered", 0.0)

        print(f"📈 Overall test coverage: {total_coverage:.1f}%")

        # Show file-by-file coverage
        files = coverage_data.get("files", {})
        for filename, file_data in files.items():
            file_coverage = file_data.get("summary", {}).get("percent_covered", 0.0)
            print(f"   {filename}: {file_coverage:.1f}%")

        # Check if we meet the 70% threshold
        meets_threshold = total_coverage >= 70.0

        if meets_threshold:
            print("✅ Coverage meets the 70% threshold!")
        else:
            print(f"❌ Coverage ({total_coverage:.1f}%) is below the 70% threshold")
            print("   Consider adding more tests to improve coverage")

        return meets_threshold, total_coverage

    except Exception as e:
        print(f"❌ Error analyzing coverage: {e}")
        return False, 0.0


def run_linting(bigquery_dir):
    """Run code linting and style checks."""
    print("\n🔍 Running code quality checks...")

    # Change to the BigQuery directory
    original_cwd = os.getcwd()
    os.chdir(bigquery_dir)

    try:
        # Check if flake8 is available
        try:
            subprocess.run(
                [sys.executable, "-m", "flake8", "--version"],
                check=True,
                capture_output=True,
            )
            has_flake8 = True
        except:
            has_flake8 = False

        if has_flake8:
            # Run flake8 on server.py
            cmd = [sys.executable, "-m", "flake8", "server.py", "--max-line-length=100"]
            result = subprocess.run(cmd, capture_output=True, text=True)

            if result.returncode == 0:
                print("✅ Code style checks passed")
            else:
                print("⚠️  Code style issues found:")
                print(result.stdout)
                print(result.stderr)
        else:
            print("⚠️  flake8 not available, skipping style checks")

    except Exception as e:
        print(f"⚠️  Error running linting: {e}")
    finally:
        os.chdir(original_cwd)


def generate_test_report(
    bigquery_dir, unit_success, integration_success, coverage_percent
):
    """Generate a comprehensive test report."""
    print("\n📋 Generating test report...")

    report = {
        "timestamp": subprocess.run(
            ["date", "+%Y-%m-%d %H:%M:%S"], capture_output=True, text=True
        ).stdout.strip(),
        "unit_tests": {
            "status": "PASSED" if unit_success else "FAILED",
            "success": unit_success,
        },
        "integration_tests": {
            "status": "PASSED" if integration_success else "FAILED",
            "success": integration_success,
        },
        "coverage": {
            "percentage": coverage_percent,
            "meets_threshold": coverage_percent >= 70.0,
            "threshold": 70.0,
        },
        "overall_status": (
            "PASSED"
            if (unit_success and integration_success and coverage_percent >= 70.0)
            else "FAILED"
        ),
    }

    # Save report
    report_file = bigquery_dir / "test_report.json"
    with open(report_file, "w") as f:
        json.dump(report, f, indent=2)

    # Print summary
    print("\n" + "=" * 50)
    print("🎯 TEST SUMMARY")
    print("=" * 50)
    print(f"Unit Tests:        {'✅ PASSED' if unit_success else '❌ FAILED'}")
    print(f"Integration Tests: {'✅ PASSED' if integration_success else '❌ FAILED'}")
    print(
        f"Coverage:          {coverage_percent:.1f}% {'✅' if coverage_percent >= 70.0 else '❌'}"
    )
    print(
        f"Overall Status:    {'✅ PASSED' if report['overall_status'] == 'PASSED' else '❌ FAILED'}"
    )
    print(f"\nReport saved to: {report_file}")

    return report


def main():
    """Main test runner function."""
    print("🚀 BigQuery MCP Server Test Suite")
    print("=" * 50)

    # Setup
    bigquery_dir, tests_dir = setup_test_environment()

    # Run tests
    unit_success, unit_stdout, unit_stderr = run_unit_tests(bigquery_dir, tests_dir)
    integration_success, int_stdout, int_stderr = run_integration_tests(
        bigquery_dir, tests_dir
    )

    # Analyze coverage
    coverage_ok, coverage_percent = analyze_coverage(bigquery_dir)

    # Run code quality checks
    run_linting(bigquery_dir)

    # Generate report
    report = generate_test_report(
        bigquery_dir, unit_success, integration_success, coverage_percent
    )

    # Exit with appropriate code
    if report["overall_status"] == "PASSED":
        print("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print("\n💥 Some tests failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()
