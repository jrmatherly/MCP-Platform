#!/usr/bin/env python3
"""
Test script for conditional configuration validation
"""

import os
import sys

sys.path.insert(0, "/home/sam/data-everything/mcp-platform/MCP-Platform")

from mcp_platform.cli.interactive_cli import (
    _generate_config_suggestions,
    _validate_config_schema,
)

# Test with the open-elastic-search template config schema
test_schema = {
    "type": "object",
    "properties": {
        "engine_type": {
            "type": "string",
            "enum": ["elasticsearch", "opensearch"],
            "default": "elasticsearch",
        },
        "elasticsearch_hosts": {"type": "string", "description": "Elasticsearch hosts"},
        "elasticsearch_api_key": {
            "type": "string",
            "description": "Elasticsearch API key",
        },
        "elasticsearch_username": {
            "type": "string",
            "description": "Elasticsearch username",
        },
        "elasticsearch_password": {
            "type": "string",
            "description": "Elasticsearch password",
        },
        "opensearch_hosts": {"type": "string", "description": "OpenSearch hosts"},
        "opensearch_username": {"type": "string", "description": "OpenSearch username"},
        "opensearch_password": {"type": "string", "description": "OpenSearch password"},
    },
    "anyOf": [
        {
            "properties": {"engine_type": {"const": "elasticsearch"}},
            "required": ["elasticsearch_hosts"],
            "oneOf": [
                {"required": ["elasticsearch_api_key"]},
                {"required": ["elasticsearch_username", "elasticsearch_password"]},
            ],
        },
        {
            "properties": {"engine_type": {"const": "opensearch"}},
            "required": [
                "opensearch_hosts",
                "opensearch_username",
                "opensearch_password",
            ],
        },
    ],
}


def test_config_validation():
    print("🧪 Testing Conditional Configuration Validation\n")

    # Test Case 1: Empty config (should fail)
    print("Test 1: Empty config")
    config1 = {}
    result1 = _validate_config_schema(test_schema, config1)
    print(f"Valid: {result1['valid']}")
    print(f"Suggestions: {result1.get('suggestions', [])}")
    print()

    # Test Case 2: Elasticsearch with API key (should pass)
    print("Test 2: Elasticsearch with API key")
    config2 = {
        "engine_type": "elasticsearch",
        "elasticsearch_hosts": "https://localhost:9200",
        "elasticsearch_api_key": "test-key",
    }
    result2 = _validate_config_schema(test_schema, config2)
    print(f"Valid: {result2['valid']}")
    print(f"Missing: {result2.get('missing_required', [])}")
    print()

    # Test Case 3: Elasticsearch with username/password (should pass)
    print("Test 3: Elasticsearch with username/password")
    config3 = {
        "engine_type": "elasticsearch",
        "elasticsearch_hosts": "https://localhost:9200",
        "elasticsearch_username": "user",
        "elasticsearch_password": "pass",
    }
    result3 = _validate_config_schema(test_schema, config3)
    print(f"Valid: {result3['valid']}")
    print(f"Missing: {result3.get('missing_required', [])}")
    print()

    # Test Case 4: Elasticsearch with both auth methods (should fail oneOf)
    print("Test 4: Elasticsearch with both auth methods")
    config4 = {
        "engine_type": "elasticsearch",
        "elasticsearch_hosts": "https://localhost:9200",
        "elasticsearch_api_key": "test-key",
        "elasticsearch_username": "user",
        "elasticsearch_password": "pass",
    }
    result4 = _validate_config_schema(test_schema, config4)
    print(f"Valid: {result4['valid']}")
    print(f"Issues: {result4.get('conditional_issues', [])}")
    print()

    # Test Case 5: OpenSearch complete (should pass)
    print("Test 5: OpenSearch complete")
    config5 = {
        "engine_type": "opensearch",
        "opensearch_hosts": "https://localhost:9200",
        "opensearch_username": "admin",
        "opensearch_password": "secret",
    }
    result5 = _validate_config_schema(test_schema, config5)
    print(f"Valid: {result5['valid']}")
    print(f"Missing: {result5.get('missing_required', [])}")
    print()

    # Test Case 6: OpenSearch incomplete (should fail)
    print("Test 6: OpenSearch incomplete")
    config6 = {
        "engine_type": "opensearch",
        "opensearch_hosts": "https://localhost:9200",
    }
    result6 = _validate_config_schema(test_schema, config6)
    print(f"Valid: {result6['valid']}")
    print(f"Suggestions: {result6.get('suggestions', [])}")
    print()


if __name__ == "__main__":
    test_config_validation()
