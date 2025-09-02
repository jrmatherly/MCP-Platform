#!/usr/bin/env python3
"""
Integration tests for BigQuery MCP Server.

These tests focus on end-to-end integration scenarios and complex workflows.
"""

import json
import os
import sys
import tempfile
from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

# Add the parent directory to sys.path to import server modules
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

# Mock Google Cloud imports before importing server
mock_bigquery = MagicMock()
mock_service_account = MagicMock()
mock_default = MagicMock()

sys.modules["google.cloud.bigquery"] = mock_bigquery
sys.modules["google.cloud.service_account"] = mock_service_account
sys.modules["google.auth.default"] = mock_default

# Import after mocking
from server import BigQueryMCPServer


class TestBigQueryIntegration:
    """Integration tests for BigQuery server functionality."""

    def setup_method(self):
        """Set up test fixtures."""
        self.test_config = {
            "project_id": "test-project",
            "auth_method": "application_default",
            "read_only": True,
            "allowed_datasets": "*",
            "max_results": 1000,
        }

    def create_mock_server(self, config=None):
        """Create a mock server with all dependencies."""
        if config is None:
            config = self.test_config.copy()

        patches = []
        additional_mocks = {}

        # Mock BigQueryServerConfig
        mock_config_patch = patch("server.BigQueryServerConfig")
        mock_config_class = mock_config_patch.start()
        patches.append(mock_config_patch)

        # Mock BigQuery module
        mock_bigquery_patch = patch("server.bigquery")
        mock_bigquery_module = mock_bigquery_patch.start()
        patches.append(mock_bigquery_patch)

        # Set up config mock
        mock_config = Mock()
        mock_config.get_template_config.return_value = config
        mock_config.get_template_data.return_value = {
            "name": "test-server",
            "version": "1.0.0",
        }
        mock_config.logger = Mock()
        mock_config_class.return_value = mock_config

        # Set up BigQuery client mock
        mock_client = Mock()
        mock_bigquery_module.Client.return_value = mock_client

        # Create server
        server = BigQueryMCPServer(config_dict=config, skip_validation=True)

        return server, mock_config, mock_client, patches, additional_mocks

    def teardown_method(self):
        """Clean up after tests."""
        # Reset all mocks
        mock_bigquery.reset_mock()
        mock_service_account.reset_mock()
        mock_default.reset_mock()

    def test_full_workflow_dataset_to_query(self):
        """Test complete workflow from listing datasets to executing queries."""
        server, _, mock_client, patches, _ = self.create_mock_server()

        # Mock dataset listing
        mock_dataset = Mock()
        mock_dataset.dataset_id = "analytics_prod"
        mock_dataset.project = "test-project"
        mock_dataset.location = "US"
        mock_dataset.created = datetime(2023, 1, 1)
        mock_dataset.modified = datetime(2023, 1, 2)
        mock_client.list_datasets.return_value = [mock_dataset]

        # Step 1: List datasets
        datasets_result = server.list_datasets()
        assert len(datasets_result["datasets"]) == 1
        assert datasets_result["datasets"][0]["dataset_id"] == "analytics_prod"

        # Mock table listing
        mock_table = Mock()
        mock_table.table_id = "user_events"
        mock_table.table_type = "TABLE"
        mock_table.created = datetime(2023, 1, 1)
        mock_table.modified = datetime(2023, 1, 2)
        mock_client.list_tables.return_value = [mock_table]

        # Step 2: List tables in dataset
        tables_result = server.list_tables(dataset_id="analytics_prod")
        assert len(tables_result["tables"]) == 1
        assert tables_result["tables"][0]["table_id"] == "user_events"

        # Mock table description
        mock_table_detailed = Mock()
        mock_table_detailed.project = "test-project"
        mock_table_detailed.dataset_id = "analytics_prod"
        mock_table_detailed.table_id = "user_events"
        mock_table_detailed.full_table_id = "test-project.analytics_prod.user_events"
        mock_table_detailed.table_type = "TABLE"
        mock_table_detailed.num_rows = 50000
        mock_table_detailed.num_bytes = 1000000
        mock_table_detailed.created = datetime(2023, 1, 1)
        mock_table_detailed.modified = datetime(2023, 1, 2)
        mock_table_detailed.description = "User events table"
        mock_table_detailed.clustering_fields = []
        mock_table_detailed.time_partitioning = None
        mock_field1 = Mock()
        mock_field1.name = "user_id"
        mock_field1.field_type = "STRING"
        mock_field1.mode = "REQUIRED"
        mock_field1.description = None
        mock_field1.fields = None
        mock_field2 = Mock()
        mock_field2.name = "event_time"
        mock_field2.field_type = "TIMESTAMP"
        mock_field2.mode = "REQUIRED"
        mock_field2.description = None
        mock_field2.fields = None
        mock_field3 = Mock()
        mock_field3.name = "event_type"
        mock_field3.field_type = "STRING"
        mock_field3.mode = "NULLABLE"
        mock_field3.description = None
        mock_field3.fields = None
        mock_table_detailed.schema = [mock_field1, mock_field2, mock_field3]
        mock_client.get_table.return_value = mock_table_detailed

        # Step 3: Describe table
        table_desc = server.describe_table(
            dataset_id="analytics_prod", table_id="user_events"
        )
        assert table_desc["table_id"] == "user_events"
        assert table_desc["num_rows"] == 50000
        assert len(table_desc["schema"]) == 3

        # Mock query execution
        mock_job = Mock()
        mock_job.result.return_value = [
            {"user_id": "user1", "event_count": 25},
            {"user_id": "user2", "event_count": 30},
        ]
        mock_job.schema = [
            Mock(name="user_id", field_type="STRING"),
            Mock(name="event_count", field_type="INTEGER"),
        ]
        mock_client.query.return_value = mock_job

        # Step 4: Execute query
        query_result = server.execute_query(
            "SELECT user_id, COUNT(*) as event_count FROM analytics_prod.user_events GROUP BY user_id"
        )
        assert len(query_result["rows"]) == 2
        assert query_result["rows"][0]["user_id"] == "user1"

        # Clean up
        for patch_obj in patches:
            patch_obj.stop()

    def test_multi_dataset_query_scenario(self):
        """Test scenario involving multiple datasets."""
        server, _, mock_client, patches, _ = self.create_mock_server()

        # Configure server to allow specific datasets
        server.config_data = {"allowed_datasets": "analytics_*,public_*"}

        # Mock multiple datasets
        datasets = [
            Mock(dataset_id="analytics_prod", project="test-project"),
            Mock(dataset_id="analytics_staging", project="test-project"),
            Mock(dataset_id="public_data", project="test-project"),
            Mock(
                dataset_id="private_data", project="test-project"
            ),  # Should be filtered out
        ]
        mock_client.list_datasets.return_value = datasets

        # List datasets - should filter based on allowed_datasets
        result = server.list_datasets()
        dataset_ids = [d["dataset_id"] for d in result["datasets"]]
        assert "analytics_prod" in dataset_ids
        assert "analytics_staging" in dataset_ids
        assert "public_data" in dataset_ids
        assert "private_data" not in dataset_ids

        # Mock cross-dataset query
        mock_job = Mock()
        mock_job.result.return_value = [
            {"dataset": "analytics_prod", "table_count": 15},
            {"dataset": "analytics_staging", "table_count": 12},
        ]
        mock_job.schema = [
            Mock(name="dataset", field_type="STRING"),
            Mock(name="table_count", field_type="INTEGER"),
        ]
        mock_client.query.return_value = mock_job

        # Execute cross-dataset query
        query_result = server.execute_query(
            """
                SELECT
                    'analytics_prod' as dataset,
                    COUNT(*) as table_count
                FROM analytics_prod.INFORMATION_SCHEMA.TABLES
                UNION ALL
                SELECT
                    'analytics_staging' as dataset,
                    COUNT(*) as table_count
                FROM analytics_staging.INFORMATION_SCHEMA.TABLES
            """
        )

        assert len(query_result["rows"]) == 2
        assert query_result["rows"][0]["dataset"] == "analytics_prod"

        # Clean up
        for patch_obj in patches:
            patch_obj.stop()

    def test_read_only_enforcement_scenario(self):
        """Test comprehensive read-only enforcement."""
        config = self.test_config.copy()
        config["read_only"] = True
        server, _, mock_client, patches, _ = self.create_mock_server(config)

        # Test that write operations are blocked
        write_operations = [
            "INSERT INTO table VALUES (1, 'test')",
            "UPDATE table SET col = 'new_value' WHERE id = 1",
            "DELETE FROM table WHERE id = 1",
            "DROP TABLE table",
            "CREATE TABLE new_table (id INT64, name STRING)",
            "ALTER TABLE table ADD COLUMN new_col STRING",
        ]

        for query in write_operations:
            result = server.execute_query(query)
            assert result["success"] is False
            assert "read-only" in result["error"].lower()

        # Test that read operations work
        mock_job = Mock()
        mock_job.result.return_value = [{"count": 100}]
        mock_job.schema = [Mock(name="count", field_type="INTEGER")]
        mock_client.query.return_value = mock_job

        read_operations = [
            "SELECT COUNT(*) as count FROM table",
            "WITH cte AS (SELECT * FROM table) SELECT * FROM cte",
            "SELECT * FROM table WHERE date = CURRENT_DATE()",
        ]

        for query in read_operations:
            result = server.execute_query(query)
            assert "rows" in result
            assert len(result["rows"]) == 1

        # Clean up
        for patch_obj in patches:
            patch_obj.stop()

    def test_authentication_flow_integration(self):
        """Test authentication flow with different methods."""
        # Test with service account file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(
                {
                    "type": "service_account",
                    "project_id": "test-project",
                    "private_key_id": "key-id",
                    "private_key": "fake-key",
                    "client_email": "test@test-project.iam.gserviceaccount.com",
                },
                f,
            )
            service_account_path = f.name

        try:
            config = self.test_config.copy()
            config.update(
                {
                    "auth_method": "service_account",
                    "service_account_path": service_account_path,
                }
            )

            with (
                patch("server.BigQueryServerConfig") as mock_config_class,
                patch("server.service_account") as mock_sa,
                patch("server.bigquery") as mock_bigquery_module,
            ):
                # Set up mocks
                mock_config = Mock()
                mock_config.get_template_config.return_value = config
                mock_config.get_template_data.return_value = {
                    "name": "test-server",
                    "version": "1.0.0",
                }
                mock_config.logger = Mock()
                mock_config_class.return_value = mock_config

                mock_credentials = Mock()
                mock_sa.Credentials.from_service_account_file.return_value = (
                    mock_credentials
                )
                mock_client = Mock()
                mock_bigquery_module.Client.return_value = mock_client

                # Create server
                server = BigQueryMCPServer(config_dict=config, skip_validation=True)

                # Verify service account authentication was used
                mock_sa.Credentials.from_service_account_file.assert_called_once_with(
                    service_account_path
                )
                mock_bigquery_module.Client.assert_called_once_with(
                    project="test-project", credentials=mock_credentials
                )

                # Test that server can perform operations
                mock_client.list_datasets.return_value = []
                result = server.list_datasets()
                assert "datasets" in result

        finally:
            os.unlink(service_account_path)

    def test_large_result_pagination_scenario(self):
        """Test handling of large result sets with pagination."""
        server, _, mock_client, patches, _ = self.create_mock_server()

        # Create a large mock result set
        large_dataset = []
        for i in range(10000):
            large_dataset.append(
                {
                    "id": i,
                    "name": f"item_{i}",
                    "value": i * 10.5,
                    "category": f"cat_{i % 5}",
                }
            )

        mock_job = Mock()
        mock_job.result.return_value = large_dataset
        mock_job.schema = [
            Mock(name="id", field_type="INTEGER"),
            Mock(name="name", field_type="STRING"),
            Mock(name="value", field_type="FLOAT"),
            Mock(name="category", field_type="STRING"),
        ]
        mock_client.query.return_value = mock_job

        # Test with default max_results
        result = server.execute_query("SELECT * FROM large_table")

        # Should be limited by server config max_results (1000)
        assert len(result["rows"]) <= 1000
        assert "job_id" in result
        assert result["success"] is True

        # Test with custom max_results (note: execute_query doesn't accept max_results parameter)
        # The max_results is controlled by server configuration only
        result = server.execute_query("SELECT * FROM large_table")

        # Should be limited by server config max_results (1000)
        assert len(result["rows"]) <= 1000

        # Clean up
        for patch_obj in patches:
            patch_obj.stop()

    def test_error_recovery_scenario(self):
        """Test error recovery and graceful degradation."""
        server, _, mock_client, patches, _ = self.create_mock_server()

        # Simulate network issues
        mock_client.list_datasets.side_effect = Exception("Network timeout")

        result = server.list_datasets()
        assert result["success"] is False
        assert "Network timeout" in result["error"]

        # Reset client to working state
        mock_client.list_datasets.side_effect = None
        mock_client.list_datasets.return_value = []

        # Should work again
        result = server.list_datasets()
        assert "datasets" in result

        # Test query timeout
        mock_client.query.side_effect = Exception("Query timeout")

        result = server.execute_query("SELECT 1")
        assert result["success"] is False
        assert "Query timeout" in result["error"]

        # Clean up
        for patch_obj in patches:
            patch_obj.stop()

    def test_complex_schema_scenario(self):
        """Test handling of complex BigQuery schemas."""
        server, _, mock_client, patches, _ = self.create_mock_server()

        # Create complex nested schema
        nested_field = Mock()
        nested_field.name = "nested_field"
        nested_field.field_type = "STRING"
        nested_field.mode = "NULLABLE"
        nested_field.description = None
        nested_field.fields = None

        record_field = Mock()
        record_field.name = "record_field"
        record_field.field_type = "RECORD"
        record_field.mode = "REPEATED"
        record_field.description = None
        record_field.fields = [nested_field]

        array_field = Mock()
        array_field.name = "array_field"
        array_field.field_type = "STRING"
        array_field.mode = "REPEATED"
        array_field.description = None
        array_field.fields = None

        complex_table = Mock()
        complex_table.project = "test-project"
        complex_table.dataset_id = "test_dataset"
        complex_table.table_id = "complex_table"
        complex_table.full_table_id = "test-project.test_dataset.complex_table"
        complex_table.table_type = "TABLE"
        complex_table.schema = [record_field, array_field]
        complex_table.num_rows = 1000
        complex_table.num_bytes = 50000
        complex_table.created = datetime(2023, 1, 1)
        complex_table.modified = datetime(2023, 1, 2)
        complex_table.description = "Complex table with nested fields"
        complex_table.clustering_fields = []
        complex_table.time_partitioning = None

        mock_client.get_table.return_value = complex_table

        # Test table description with complex schema
        result = server.describe_table("test_dataset", "complex_table")

        assert result["table_id"] == "complex_table"
        assert len(result["schema"]) == 2

        # Check record field
        record_schema = result["schema"][0]
        assert record_schema["name"] == "record_field"
        assert record_schema["field_type"] == "RECORD"
        assert record_schema["mode"] == "REPEATED"
        assert len(record_schema["fields"]) == 1

        # Check array field
        array_schema = result["schema"][1]
        assert array_schema["name"] == "array_field"
        assert array_schema["mode"] == "REPEATED"

        # Clean up
        for patch_obj in patches:
            patch_obj.stop()

    def test_concurrent_operations_scenario(self):
        """Test handling of concurrent operations."""
        server, _, mock_client, patches, _ = self.create_mock_server()

        # Mock multiple concurrent operations
        call_count = 0

        def mock_query_side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            mock_job = Mock()
            mock_job.result.return_value = [
                {"query_id": call_count, "result": f"result_{call_count}"}
            ]
            mock_job.schema = [
                Mock(name="query_id", field_type="INTEGER"),
                Mock(name="result", field_type="STRING"),
            ]
            return mock_job

        mock_client.query.side_effect = mock_query_side_effect

        # Execute multiple queries
        results = []
        for i in range(5):
            result = server.execute_query(
                f"SELECT {i+1} as query_id, 'result_{i+1}' as result"
            )
            results.append(result)

        # Verify all queries were executed
        assert len(results) == 5
        for i, result in enumerate(results):
            assert result["rows"][0]["query_id"] == i + 1
            assert result["rows"][0]["result"] == f"result_{i + 1}"

        # Clean up
        for patch_obj in patches:
            patch_obj.stop()

    def test_configuration_edge_cases(self):
        """Test edge cases in configuration handling."""
        # Test with minimal configuration
        minimal_config = {"project_id": "test-project"}
        server, _, _, patches, _ = self.create_mock_server(minimal_config)

        # Should use defaults for missing values
        assert server.config_data["project_id"] == "test-project"

        # Clean up
        for patch_obj in patches:
            patch_obj.stop()

        # Test with maximum configuration
        max_config = {
            "project_id": "test-project",
            "auth_method": "service_account",
            "service_account_path": "/fake/path.json",
            "read_only": False,
            "allowed_datasets": "analytics_*,public_*",
            "dataset_regex": r"^(analytics|public)_.*",
            "max_results": 5000,
        }

        with patch("server.service_account"):
            server, _, _, patches, _ = self.create_mock_server(max_config)

            # Should use all provided configuration
            assert server.config_data["max_results"] == 5000
            assert server.config_data["read_only"] is False

            # Clean up
            for patch_obj in patches:
                patch_obj.stop()
