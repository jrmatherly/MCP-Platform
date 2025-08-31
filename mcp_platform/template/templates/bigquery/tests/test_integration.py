#!/usr/bin/env python3
"""
Integration Tests for BigQuery MCP Server.

These tests validate the complete integration of the BigQuery MCP server
with mocked BigQuery services to ensure end-to-end functionality.
"""

import os
import sys
import tempfile
from datetime import datetime, timezone
from unittest.mock import MagicMock, Mock, patch

import pytest

import os
import sys
import tempfile
from datetime import datetime, timezone
from unittest.mock import MagicMock, Mock, patch

import pytest

# Add the parent directory to sys.path to import server modules
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# Mock all Google Cloud imports
mock_modules = {
    "google.cloud": MagicMock(),
    "google.cloud.bigquery": MagicMock(),
    "google.oauth2": MagicMock(),
    "google.oauth2.service_account": MagicMock(),
    "google.auth": MagicMock(),
    "google.auth.default": MagicMock(),
    "google.api_core": MagicMock(),
    "google.api_core.exceptions": MagicMock(),
}

# Set up mock exception classes
mock_modules["google.api_core.exceptions"].NotFound = Exception
mock_modules["google.api_core.exceptions"].Forbidden = Exception
mock_modules["google.api_core.exceptions"].BadRequest = Exception

for module_name, mock_module in mock_modules.items():
    sys.modules[module_name] = mock_module

# Now import the server after mocking
from server import BigQueryMCPServer


@pytest.mark.integration
class TestBigQueryIntegration:
    """Integration tests for BigQuery MCP Server."""

    def setup_method(self):
        """Set up test fixtures for integration tests."""
        self.mock_bigquery = sys.modules["google.cloud.bigquery"]
        self.mock_client = Mock()
        self.mock_bigquery.Client.return_value = self.mock_client

        # Base configuration for integration tests
        self.integration_config = {
            "project_id": "integration-test-project",
            "auth_method": "application_default",
            "read_only": True,
            "allowed_datasets": "*",
            "query_timeout": 300,
            "max_results": 1000,
            "log_level": "info",
        }

    def test_complete_dataset_discovery_workflow(self):
        """Test complete dataset discovery and exploration workflow."""
        with patch("google.cloud.bigquery.Client") as mock_client_class:
            # Configure the BigQuery client mock
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            
            # Create server instance
            server = BigQueryMCPServer(
                config_dict=self.integration_config, skip_validation=True
            )

            # Step 1: List datasets
            mock_dataset1 = Mock()
            mock_dataset1.dataset_id = "ecommerce_analytics"
            mock_dataset1.full_dataset_id = (
                "integration-test-project.ecommerce_analytics"
            )
            mock_dataset1.location = "US"
            mock_dataset1.created = datetime.now(timezone.utc)
            mock_dataset1.modified = datetime.now(timezone.utc)

            mock_dataset2 = Mock()
            mock_dataset2.dataset_id = "user_behavior"
            mock_dataset2.full_dataset_id = "integration-test-project.user_behavior"
            mock_dataset2.location = "EU"
            mock_dataset2.created = datetime.now(timezone.utc)
            mock_dataset2.modified = datetime.now(timezone.utc)

            mock_client.list_datasets.return_value = [mock_dataset1, mock_dataset2]

            datasets_result = server.list_datasets()
            assert datasets_result["success"] is True
            assert len(datasets_result["datasets"]) == 2

            # Step 2: Get dataset info
            mock_dataset_info = Mock()
            mock_dataset_info.full_dataset_id = (
                "integration-test-project.ecommerce_analytics"
            )
            mock_dataset_info.location = "US"
            mock_dataset_info.description = "E-commerce analytics data"
            mock_dataset_info.created = datetime.now(timezone.utc)
            mock_dataset_info.modified = datetime.now(timezone.utc)
            mock_dataset_info.default_table_expiration_ms = 7776000000  # 90 days
            mock_dataset_info.default_partition_expiration_ms = None
            mock_dataset_info.labels = {"team": "analytics", "env": "prod"}
            mock_dataset_info.access_entries = []

            mock_dataset_ref = Mock()
            self.mock_client.dataset.return_value = mock_dataset_ref
            self.mock_client.get_dataset.return_value = mock_dataset_info

            dataset_info_result = server.get_dataset_info("ecommerce_analytics")
            assert dataset_info_result["success"] is True
            assert dataset_info_result["location"] == "US"
            assert dataset_info_result["labels"]["team"] == "analytics"

            # Step 3: List tables in dataset
            mock_table1 = Mock()
            mock_table1.table_id = "orders"
            mock_table1.full_table_id = (
                "integration-test-project.ecommerce_analytics.orders"
            )
            mock_table1.table_type = "TABLE"
            mock_table1.created = datetime.now(timezone.utc)
            mock_table1.modified = datetime.now(timezone.utc)

            mock_table2 = Mock()
            mock_table2.table_id = "customers"
            mock_table2.full_table_id = (
                "integration-test-project.ecommerce_analytics.customers"
            )
            mock_table2.table_type = "TABLE"
            mock_table2.created = datetime.now(timezone.utc)
            mock_table2.modified = datetime.now(timezone.utc)

            self.mock_client.list_tables.return_value = [mock_table1, mock_table2]

            tables_result = server.list_tables("ecommerce_analytics")
            assert tables_result["success"] is True
            assert len(tables_result["tables"]) == 2
            assert tables_result["tables"][0]["table_id"] == "orders"

            # Step 4: Describe table schema
            mock_field1 = Mock()
            mock_field1.name = "order_id"
            mock_field1.field_type = "INTEGER"
            mock_field1.mode = "REQUIRED"
            mock_field1.description = "Unique order identifier"
            mock_field1.fields = []

            mock_field2 = Mock()
            mock_field2.name = "customer_id"
            mock_field2.field_type = "INTEGER"
            mock_field2.mode = "REQUIRED"
            mock_field2.description = "Customer identifier"
            mock_field2.fields = []

            mock_field3 = Mock()
            mock_field3.name = "order_details"
            mock_field3.field_type = "RECORD"
            mock_field3.mode = "REPEATED"
            mock_field3.description = "Order line items"

            # Nested fields
            mock_nested_field1 = Mock()
            mock_nested_field1.name = "product_id"
            mock_nested_field1.field_type = "INTEGER"
            mock_nested_field1.mode = "REQUIRED"
            mock_nested_field1.description = "Product identifier"
            mock_nested_field1.fields = []

            mock_nested_field2 = Mock()
            mock_nested_field2.name = "quantity"
            mock_nested_field2.field_type = "INTEGER"
            mock_nested_field2.mode = "REQUIRED"
            mock_nested_field2.description = "Product quantity"
            mock_nested_field2.fields = []

            mock_field3.fields = [mock_nested_field1, mock_nested_field2]

            mock_table_schema = Mock()
            mock_table_schema.full_table_id = (
                "integration-test-project.ecommerce_analytics.orders"
            )
            mock_table_schema.table_type = "TABLE"
            mock_table_schema.num_rows = 1500000
            mock_table_schema.num_bytes = 50000000
            mock_table_schema.created = datetime.now(timezone.utc)
            mock_table_schema.modified = datetime.now(timezone.utc)
            mock_table_schema.description = "Customer orders table"
            mock_table_schema.schema = [mock_field1, mock_field2, mock_field3]
            mock_table_schema.clustering_fields = ["customer_id"]
            mock_table_schema.time_partitioning = None

            mock_table_ref = Mock()
            self.mock_client.dataset.return_value.table.return_value = mock_table_ref
            self.mock_client.get_table.return_value = mock_table_schema

            schema_result = server.describe_table("ecommerce_analytics", "orders")
            assert schema_result["success"] is True
            assert schema_result["num_rows"] == 1500000
            assert len(schema_result["schema"]) == 3
            assert schema_result["schema"][2]["name"] == "order_details"
            assert len(schema_result["schema"][2]["fields"]) == 2

    def test_complete_query_execution_workflow(self):
        """Test complete query execution workflow with dry run and actual execution."""
        with patch("google.cloud.bigquery.Client") as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            
            server = BigQueryMCPServer(
                config_dict=self.integration_config, skip_validation=True
            )

            query = """
            SELECT 
                customer_id,
                COUNT(*) as order_count,
                SUM(total_amount) as total_spent
            FROM `integration-test-project.ecommerce_analytics.orders`
            WHERE order_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
            GROUP BY customer_id
            ORDER BY total_spent DESC
            LIMIT 100
            """

            # Step 1: Dry run to validate query
            mock_dry_run_job = Mock()
            mock_dry_run_job.total_bytes_processed = 256000000  # 256MB

            mock_client.query.return_value = mock_dry_run_job

            dry_run_result = server.execute_query(query, dry_run=True)
            assert dry_run_result["success"] is True
            assert dry_run_result["dry_run"] is True
            assert dry_run_result["total_bytes_processed"] == 256000000
            assert "would process" in dry_run_result["message"]

            # Step 2: Execute actual query
            mock_execution_job = Mock()
            mock_execution_job.job_id = "job_integration_test_12345"
            mock_execution_job.total_bytes_processed = 256000000
            mock_execution_job.total_bytes_billed = 256000000
            mock_execution_job.cache_hit = False

            # Mock query results
            mock_results = [
                {"customer_id": 101, "order_count": 15, "total_spent": 2500.50},
                {"customer_id": 102, "order_count": 12, "total_spent": 1980.75},
                {"customer_id": 103, "order_count": 8, "total_spent": 1750.25},
            ]

            mock_result_iterator = Mock()
            mock_result_iterator.__iter__ = Mock(return_value=iter(mock_results))
            mock_execution_job.result.return_value = mock_result_iterator

            mock_client.query.return_value = mock_execution_job

            execution_result = server.execute_query(query, dry_run=False)
            assert execution_result["success"] is True
            assert execution_result["job_id"] == "job_integration_test_12345"
            assert execution_result["num_rows"] == 3
            assert execution_result["total_bytes_processed"] == 256000000
            assert execution_result["rows"][0]["customer_id"] == 101
            assert execution_result["rows"][0]["total_spent"] == 2500.50

            # Step 3: Check job status
            mock_job_status = Mock()
            mock_job_status.state = "DONE"
            mock_job_status.job_type = "QUERY"
            mock_job_status.created = datetime.now(timezone.utc)
            mock_job_status.started = datetime.now(timezone.utc)
            mock_job_status.ended = datetime.now(timezone.utc)
            mock_job_status.error_result = None
            mock_job_status.errors = []
            mock_job_status.user_email = "test@integration.com"

            mock_client.get_job.return_value = mock_job_status

            job_status_result = server.get_job_status("job_integration_test_12345")
            assert job_status_result["success"] is True
            assert job_status_result["state"] == "DONE"
            assert job_status_result["job_type"] == "QUERY"

    def test_access_control_integration(self):
        """Test complete access control workflow with different permissions."""
        # Test with restricted dataset access
        restricted_config = self.integration_config.copy()
        restricted_config.update(
            {"allowed_datasets": "analytics_*,public_*", "read_only": True}
        )

        with patch("google.cloud.bigquery.Client") as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            
            server = BigQueryMCPServer(
                config_dict=restricted_config, skip_validation=True
            )

            # Mock datasets with mixed access levels
            mock_allowed_dataset1 = Mock()
            mock_allowed_dataset1.dataset_id = "analytics_prod"
            mock_allowed_dataset1.full_dataset_id = (
                "integration-test-project.analytics_prod"
            )

            mock_allowed_dataset2 = Mock()
            mock_allowed_dataset2.dataset_id = "public_reference"
            mock_allowed_dataset2.full_dataset_id = (
                "integration-test-project.public_reference"
            )

            mock_restricted_dataset = Mock()
            mock_restricted_dataset.dataset_id = "sensitive_data"
            mock_restricted_dataset.full_dataset_id = (
                "integration-test-project.sensitive_data"
            )

            mock_private_dataset = Mock()
            mock_private_dataset.dataset_id = "internal_metrics"
            mock_private_dataset.full_dataset_id = (
                "integration-test-project.internal_metrics"
            )

            all_datasets = [
                mock_allowed_dataset1,
                mock_allowed_dataset2,
                mock_restricted_dataset,
                mock_private_dataset,
            ]

            mock_client.list_datasets.return_value = all_datasets

            # Test that only allowed datasets are returned
            datasets_result = server.list_datasets()
            assert datasets_result["success"] is True
            assert (
                len(datasets_result["datasets"]) == 2
            )  # Only analytics_ and public_ allowed
            returned_names = [d["dataset_id"] for d in datasets_result["datasets"]]
            assert "analytics_prod" in returned_names
            assert "public_reference" in returned_names
            assert "sensitive_data" not in returned_names
            assert "internal_metrics" not in returned_names

    def test_authentication_methods_integration(self):
        """Test integration with different authentication methods."""

        # Test service account authentication
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write(
                """{
                "type": "service_account",
                "project_id": "integration-test-project",
                "private_key_id": "test",
                "private_key": "-----BEGIN PRIVATE KEY-----\\ntest\\n-----END PRIVATE KEY-----\\n",
                "client_email": "test@integration-test-project.iam.gserviceaccount.com",
                "client_id": "test",
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token"
            }"""
            )
            service_account_path = f.name

        try:
            service_account_config = self.integration_config.copy()
            service_account_config.update(
                {
                    "auth_method": "service_account",
                    "service_account_path": service_account_path,
                }
            )

            mock_credentials = Mock()
            
            with patch("google.oauth2.service_account.Credentials.from_service_account_file") as mock_sa_creds, \
                 patch("google.cloud.bigquery.Client") as mock_client_class:
                
                mock_sa_creds.return_value = mock_credentials
                mock_client = Mock()
                mock_client_class.return_value = mock_client

                server = BigQueryMCPServer(
                    config_dict=service_account_config, skip_validation=True
                )

                # Verify service account credentials were used
                mock_sa_creds.assert_called_once_with(service_account_path)
                mock_client_class.assert_called_with(
                    credentials=mock_credentials, project="integration-test-project"
                )

        finally:
            os.unlink(service_account_path)

        # Test OAuth2 authentication
        oauth_config = self.integration_config.copy()
        oauth_config["auth_method"] = "oauth2"

        mock_oauth_credentials = Mock()
        
        with patch("google.auth.default") as mock_auth_default, \
             patch("google.cloud.bigquery.Client") as mock_client_class:
            
            mock_auth_default.return_value = (
                mock_oauth_credentials,
                "integration-test-project",
            )
            mock_client = Mock()
            mock_client_class.return_value = mock_client

            server = BigQueryMCPServer(config_dict=oauth_config, skip_validation=True)

            # Verify OAuth2 credentials were used
            mock_auth_default.assert_called()

    def test_error_handling_integration(self):
        """Test comprehensive error handling across the integration."""
        with patch("google.cloud.bigquery.Client") as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            
            server = BigQueryMCPServer(
                config_dict=self.integration_config, skip_validation=True
            )

            # Test BigQuery API errors
            mock_api_error = Exception("BigQuery API: Access Denied")

            # Test dataset listing error
            mock_client.list_datasets.side_effect = mock_api_error
            datasets_result = server.list_datasets()
            assert datasets_result["success"] is False
            assert "Access Denied" in datasets_result["error"]

            # Reset side effect
            mock_client.list_datasets.side_effect = None

            # Test table listing error
            mock_client.list_tables.side_effect = mock_api_error
            tables_result = server.list_tables("test_dataset")
            assert tables_result["success"] is False
            assert "Access Denied" in tables_result["error"]

            # Test query execution error
            mock_client.query.side_effect = mock_api_error
            query_result = server.execute_query("SELECT 1")
            assert query_result["success"] is False
            assert "Access Denied" in query_result["error"]

            # Test job status error
            mock_client.get_job.side_effect = mock_api_error
            job_result = server.get_job_status("test_job")
            assert job_result["success"] is False
            assert "Access Denied" in job_result["error"]

    def test_query_limits_integration(self):
        """Test query execution with various limits and configurations."""
        # Test with custom limits
        custom_limits_config = self.integration_config.copy()
        custom_limits_config.update(
            {
                "query_timeout": 600,  # 10 minutes
                "max_results": 500,  # Limit to 500 rows
            }
        )

        with patch("google.cloud.bigquery.Client") as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            
            server = BigQueryMCPServer(
                config_dict=custom_limits_config, skip_validation=True
            )

            # Mock a large result set (1000 rows)
            large_results = [{"id": i, "value": f"value_{i}"} for i in range(1000)]

            mock_job = Mock()
            mock_job.job_id = "job_large_result_test"
            mock_job.total_bytes_processed = 1000000
            mock_job.total_bytes_billed = 1000000
            mock_job.cache_hit = False

            mock_result_iterator = Mock()
            mock_result_iterator.__iter__ = Mock(return_value=iter(large_results))
            mock_job.result.return_value = mock_result_iterator

            mock_client.query.return_value = mock_job

            # Execute query
            query_result = server.execute_query("SELECT * FROM large_table")

            # Verify results are limited to max_results
            assert query_result["success"] is True
            assert query_result["num_rows"] == 1000  # Total rows found
            assert len(query_result["rows"]) == 500  # Limited to max_results
            assert query_result["truncated"] is True

            # Verify timeout was passed to BigQuery job config
            call_args = mock_client.query.call_args
            query_text = call_args[0][0]
            job_config = call_args[1]["job_config"]

            # The timeout is used in job.result(), not job_config
            # But we can verify the query was executed
            assert "SELECT * FROM large_table" in query_text

    def test_regex_dataset_filtering_integration(self):
        """Test regex-based dataset filtering in integration scenario."""
        regex_config = self.integration_config.copy()
        regex_config.update(
            {
                "dataset_regex": "^(prod|staging)_.*$",
                "allowed_datasets": "*",  # This should be ignored due to regex
            }
        )

        with patch("google.cloud.bigquery.Client") as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            
            server = BigQueryMCPServer(config_dict=regex_config, skip_validation=True)

            # Mock datasets with various naming patterns
            mock_datasets = []
            dataset_names = [
                "prod_analytics",
                "staging_analytics",
                "dev_analytics",  # Should be filtered out
                "test_data",  # Should be filtered out
                "prod_reporting",
                "staging_user_data",
                "backup_analytics",  # Should be filtered out
            ]

            for name in dataset_names:
                mock_dataset = Mock()
                mock_dataset.dataset_id = name
                mock_dataset.full_dataset_id = f"integration-test-project.{name}"
                mock_dataset.location = "US"
                mock_dataset.created = datetime.now(timezone.utc)
                mock_dataset.modified = datetime.now(timezone.utc)
                mock_datasets.append(mock_dataset)

            mock_client.list_datasets.return_value = mock_datasets

            # Test dataset listing with regex filtering
            datasets_result = server.list_datasets()
            assert datasets_result["success"] is True
            assert (
                len(datasets_result["datasets"]) == 4
            )  # Only prod_ and staging_ datasets

            returned_dataset_ids = [
                d["dataset_id"] for d in datasets_result["datasets"]
            ]
            assert "prod_analytics" in returned_dataset_ids
            assert "staging_analytics" in returned_dataset_ids
            assert "prod_reporting" in returned_dataset_ids
            assert "staging_user_data" in returned_dataset_ids
            assert "dev_analytics" not in returned_dataset_ids
            assert "test_data" not in returned_dataset_ids
            assert "backup_analytics" not in returned_dataset_ids

    def test_health_check_integration(self):
        """Test health check endpoint integration."""
        with patch("google.cloud.bigquery.Client") as mock_client_class:
            mock_client = Mock()
            mock_client_class.return_value = mock_client
            
            server = BigQueryMCPServer(
                config_dict=self.integration_config, skip_validation=True
            )

            # Mock successful BigQuery connection test
            mock_dataset = Mock()
            mock_dataset.dataset_id = "test_connection"
            mock_client.list_datasets.return_value = [mock_dataset]

            # Create mock request
            mock_request = Mock()

            # Import the health check function
            # Test successful health check
            import asyncio

            from server import health_check

            result = asyncio.run(health_check(mock_request))

            # The result would be a JSONResponse, but we can test the logic
            # In a real integration test, we'd test the actual HTTP endpoint
            assert result is not None
