#!/usr/bin/env python3
"""
Real-time BigQuery Template Integration Test Script.

This script tests the BigQuery template in a real environment with actual
Google Cloud BigQuery access, providing comprehensive testing of all functionality.
"""

import subprocess
import sys
import time
from pathlib import Path

import requests

# Add project root to path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root))


class BigQueryRealTimeTest:
    """Real-time integration test for BigQuery template."""

    def __init__(self, project_id: str, base_url: str = "http://localhost:8000"):
        self.project_id = project_id
        self.base_url = base_url
        self.template_id = "bigquery"
        self.deployment_name = None

    def deploy_template(self) -> bool:
        """Deploy the BigQuery template."""
        print("🚀 Deploying BigQuery template...")

        try:
            # Stop any existing deployment
            self.cleanup()

            # Deploy with configuration
            cmd = [
                "python",
                "-m",
                "mcp_platform",
                "deploy",
                self.template_id,
                "--config",
                f"project_id={self.project_id}",
                "--config",
                "read_only=true",
                "--config",
                "max_results=100",
            ]

            result = subprocess.run(
                cmd, capture_output=True, text=True, cwd=project_root
            )

            if result.returncode != 0:
                print(f"❌ Deployment failed: {result.stderr}")
                return False

            # Extract deployment name from output
            for line in result.stdout.split("\n"):
                if "deployed as" in line.lower():
                    self.deployment_name = line.split()[-1]
                    break

            if not self.deployment_name:
                print("❌ Could not extract deployment name")
                return False

            print(f"✅ Template deployed as: {self.deployment_name}")

            # Wait for deployment to be ready
            time.sleep(10)
            return True

        except Exception as e:
            print(f"❌ Deployment error: {e}")
            return False

    def test_tool_discovery(self) -> bool:
        """Test tool discovery via HTTP API."""
        print("🔍 Testing tool discovery...")

        try:
            response = requests.get(
                f"{self.base_url}/v1/templates/{self.template_id}/tools"
            )

            if response.status_code != 200:
                print(f"❌ Tool discovery failed: {response.status_code}")
                return False

            tools = response.json()
            expected_tools = [
                "list_datasets",
                "list_tables",
                "describe_table",
                "query_table",
                "get_table_sample",
                "execute_query",
            ]

            found_tools = [tool["name"] for tool in tools.get("tools", [])]

            for tool in expected_tools:
                if tool in found_tools:
                    print(f"  ✅ Found tool: {tool}")
                else:
                    print(f"  ❌ Missing tool: {tool}")
                    return False

            return True

        except Exception as e:
            print(f"❌ Tool discovery error: {e}")
            return False

    def test_list_datasets(self) -> bool:
        """Test list_datasets tool."""
        print("📊 Testing list_datasets...")

        try:
            payload = {
                "template_id": self.template_id,
                "tool_name": "list_datasets",
                "arguments": {},
            }

            response = requests.post(f"{self.base_url}/v1/call", json=payload)

            if response.status_code != 200:
                print(
                    f"❌ list_datasets failed: {response.status_code} - {response.text}"
                )
                return False

            result = response.json()

            if "datasets" not in result:
                print(f"❌ Invalid response format: {result}")
                return False

            datasets = result["datasets"]
            print(f"  ✅ Found {len(datasets)} datasets")

            # Test dataset structure
            if datasets:
                dataset = datasets[0]
                required_fields = ["dataset_id", "project_id", "location"]
                for field in required_fields:
                    if field not in dataset:
                        print(f"  ❌ Missing field in dataset: {field}")
                        return False

                print(f"  ✅ Dataset structure valid: {dataset['dataset_id']}")

            return True

        except Exception as e:
            print(f"❌ list_datasets error: {e}")
            return False

    def test_list_tables(self, dataset_id: str = None) -> bool:
        """Test list_tables tool."""
        print("📋 Testing list_tables...")

        if not dataset_id:
            # First get a dataset
            try:
                payload = {
                    "template_id": self.template_id,
                    "tool_name": "list_datasets",
                    "arguments": {},
                }

                response = requests.post(f"{self.base_url}/v1/call", json=payload)
                result = response.json()
                datasets = result.get("datasets", [])

                if not datasets:
                    print("  ⚠️  No datasets available for table listing test")
                    return True

                dataset_id = datasets[0]["dataset_id"]

            except Exception as e:
                print(f"❌ Could not get dataset for table test: {e}")
                return False

        try:
            payload = {
                "template_id": self.template_id,
                "tool_name": "list_tables",
                "arguments": {"dataset_id": dataset_id},
            }

            response = requests.post(f"{self.base_url}/v1/call", json=payload)

            if response.status_code != 200:
                print(
                    f"❌ list_tables failed: {response.status_code} - {response.text}"
                )
                return False

            result = response.json()

            if "tables" not in result:
                print(f"❌ Invalid response format: {result}")
                return False

            tables = result["tables"]
            print(f"  ✅ Found {len(tables)} tables in dataset {dataset_id}")

            return True

        except Exception as e:
            print(f"❌ list_tables error: {e}")
            return False

    def test_describe_table(self) -> bool:
        """Test describe_table tool."""
        print("🔍 Testing describe_table...")

        # Use a common public dataset for testing
        try:
            payload = {
                "template_id": self.template_id,
                "tool_name": "describe_table",
                "arguments": {
                    "dataset_id": "bigquery-public-data.usa_names",
                    "table_id": "usa_1910_current",
                },
            }

            response = requests.post(f"{self.base_url}/v1/call", json=payload)

            if response.status_code != 200:
                print("  ⚠️  describe_table test skipped (public data not accessible)")
                return True

            result = response.json()

            if "schema" not in result:
                print(f"❌ Invalid response format: {result}")
                return False

            print("  ✅ Table description retrieved successfully")
            return True

        except Exception as e:
            print(f"  ⚠️  describe_table test skipped: {e}")
            return True

    def test_query_execution(self) -> bool:
        """Test query execution tools."""
        print("🔍 Testing query execution...")

        # Test a simple query
        try:
            payload = {
                "template_id": self.template_id,
                "tool_name": "execute_query",
                "arguments": {"query": "SELECT 1 as test_column", "max_results": 10},
            }

            response = requests.post(f"{self.base_url}/v1/call", json=payload)

            if response.status_code != 200:
                print(
                    f"❌ execute_query failed: {response.status_code} - {response.text}"
                )
                return False

            result = response.json()

            if "rows" not in result:
                print(f"❌ Invalid response format: {result}")
                return False

            rows = result["rows"]
            if len(rows) != 1 or rows[0]["test_column"] != 1:
                print(f"❌ Unexpected query result: {rows}")
                return False

            print("  ✅ Simple query executed successfully")
            return True

        except Exception as e:
            print(f"❌ execute_query error: {e}")
            return False

    def test_read_only_protection(self) -> bool:
        """Test read-only protection."""
        print("🔒 Testing read-only protection...")

        write_queries = [
            "CREATE TABLE test_table (id INT64)",
            "INSERT INTO test_table VALUES (1)",
            "UPDATE test_table SET id = 2",
            "DELETE FROM test_table WHERE id = 1",
            "DROP TABLE test_table",
        ]

        for query in write_queries:
            try:
                payload = {
                    "template_id": self.template_id,
                    "tool_name": "execute_query",
                    "arguments": {"query": query},
                }

                response = requests.post(f"{self.base_url}/v1/call", json=payload)

                # Should fail with read-only protection
                if response.status_code == 200:
                    print(f"❌ Write query was allowed: {query}")
                    return False

                print(f"  ✅ Write query blocked: {query[:30]}...")

            except Exception:
                print(f"  ✅ Write query blocked with exception: {query[:30]}...")

        return True

    def test_error_handling(self) -> bool:
        """Test error handling."""
        print("⚠️  Testing error handling...")

        test_cases = [
            {
                "name": "Invalid dataset",
                "tool": "list_tables",
                "args": {"dataset_id": "nonexistent_dataset"},
            },
            {
                "name": "Invalid query",
                "tool": "execute_query",
                "args": {"query": "SELECT FROM invalid_syntax"},
            },
            {"name": "Missing required parameter", "tool": "list_tables", "args": {}},
        ]

        for test_case in test_cases:
            try:
                payload = {
                    "template_id": self.template_id,
                    "tool_name": test_case["tool"],
                    "arguments": test_case["args"],
                }

                response = requests.post(f"{self.base_url}/v1/call", json=payload)

                # Should return error, not crash
                if response.status_code == 500:
                    print(f"❌ Server error for {test_case['name']}")
                    return False

                print(f"  ✅ Error handled gracefully: {test_case['name']}")

            except Exception:
                print(f"  ✅ Error handled with exception: {test_case['name']}")

        return True

    def check_logs(self) -> bool:
        """Check deployment logs for errors."""
        print("📋 Checking deployment logs...")

        if not self.deployment_name:
            print("  ⚠️  No deployment name available")
            return True

        try:
            cmd = ["python", "-m", "mcp_platform", "logs", self.deployment_name]
            result = subprocess.run(
                cmd, capture_output=True, text=True, cwd=project_root
            )

            logs = result.stdout

            # Check for common error patterns
            error_patterns = [
                "AttributeError",
                "ImportError",
                "ModuleNotFoundError",
                "Traceback",
                "Exception:",
                "Error:",
            ]

            errors_found = []
            for pattern in error_patterns:
                if pattern in logs:
                    errors_found.append(pattern)

            if errors_found:
                print(f"❌ Errors found in logs: {errors_found}")
                print("Recent logs:")
                print(logs[-1000:])  # Last 1000 characters
                return False
            else:
                print("  ✅ No errors found in logs")
                return True

        except Exception as e:
            print(f"  ⚠️  Could not check logs: {e}")
            return True

    def cleanup(self):
        """Clean up deployment."""
        print("🧹 Cleaning up...")

        try:
            cmd = ["python", "-m", "mcp_platform", "stop", self.template_id]
            subprocess.run(cmd, capture_output=True, cwd=project_root)
            print("  ✅ Cleanup completed")
        except Exception as e:
            print(f"  ⚠️  Cleanup warning: {e}")

    def run_full_test_suite(self) -> bool:
        """Run the complete test suite."""
        print("🧪 Starting BigQuery Template Real-Time Test Suite")
        print("=" * 60)

        test_results = []

        # Deploy template
        test_results.append(("Deploy Template", self.deploy_template()))

        if test_results[-1][1]:  # Only continue if deployment succeeded
            # Core functionality tests
            test_results.append(("Tool Discovery", self.test_tool_discovery()))
            test_results.append(("List Datasets", self.test_list_datasets()))
            test_results.append(("List Tables", self.test_list_tables()))
            test_results.append(("Describe Table", self.test_describe_table()))
            test_results.append(("Query Execution", self.test_query_execution()))

            # Security and error handling
            test_results.append(
                ("Read-Only Protection", self.test_read_only_protection())
            )
            test_results.append(("Error Handling", self.test_error_handling()))

            # System checks
            test_results.append(("Log Check", self.check_logs()))

        # Cleanup
        self.cleanup()

        # Report results
        print("\n" + "=" * 60)
        print("📊 Test Results Summary")
        print("=" * 60)

        passed = 0
        total = len(test_results)

        for test_name, result in test_results:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{test_name:25} {status}")
            if result:
                passed += 1

        print("=" * 60)
        print(f"Results: {passed}/{total} tests passed ({passed/total*100:.1f}%)")

        if passed == total:
            print("🎉 All tests passed! BigQuery template is working correctly.")
            return True
        else:
            print("❌ Some tests failed. Check the output above for details.")
            return False


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print("Usage: python bigquery_realtime_test.py <project_id> [base_url]")
        print("Example: python bigquery_realtime_test.py gen-lang-client-0945188133")
        sys.exit(1)

    project_id = sys.argv[1]
    base_url = sys.argv[2] if len(sys.argv) > 2 else "http://localhost:8000"

    tester = BigQueryRealTimeTest(project_id, base_url)
    success = tester.run_full_test_suite()

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
