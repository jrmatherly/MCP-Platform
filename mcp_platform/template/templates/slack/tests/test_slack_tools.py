"""
Tests for Slack MCP server tools and functionality.

These tests verify tool configurations and mock Slack API responses.
"""

import json
from pathlib import Path
from unittest.mock import patch

import pytest


class TestSlackTools:
    """Test Slack MCP server tools and API interactions."""

    @pytest.fixture
    def template_config(self) -> dict:
        """Load template configuration."""
        template_dir = Path(__file__).parent.parent
        template_json = template_dir / "template.json"

        with open(template_json, "r") as f:
            return json.load(f)

    @pytest.fixture
    def mock_slack_response(self):
        """Create mock Slack API response."""
        return {
            "ok": True,
            "messages": [
                {
                    "type": "message",
                    "user": "U123456789",
                    "text": "Hello from Slack!",
                    "ts": "1234567890.123456",
                    "thread_ts": None,
                },
                {
                    "type": "message",
                    "user": "U987654321",
                    "text": "Reply to the message",
                    "ts": "1234567891.123456",
                    "thread_ts": "1234567890.123456",
                },
            ],
            "has_more": False,
            "response_metadata": {"next_cursor": ""},
        }

    @pytest.fixture
    def mock_search_response(self):
        """Create mock Slack search response."""
        return {
            "ok": True,
            "query": "test query",
            "messages": {
                "total": 2,
                "paging": {"count": 20, "total": 2, "page": 1, "pages": 1},
                "matches": [
                    {
                        "type": "message",
                        "user": "U123456789",
                        "username": "testuser",
                        "text": "This is a test message",
                        "ts": "1234567890.123456",
                        "channel": {"id": "C123456789", "name": "general"},
                    }
                ],
            },
        }

    def test_tool_capabilities_structure(self, template_config):
        """Test that tool capabilities are properly structured."""
        capabilities = template_config["capabilities"]

        # Should have all expected Slack tools
        expected_tools = [
            "conversations_history",
            "conversations_replies",
            "conversations_add_message",
            "search_messages",
            "channel_management",
            "user_management",
        ]

        tool_names = [cap["name"] for cap in capabilities]

        for tool in expected_tools:
            assert tool in tool_names, f"Missing tool capability: {tool}"

    def test_conversations_history_capability(self, template_config):
        """Test conversations_history capability definition."""
        capabilities = template_config["capabilities"]

        history_cap = next(
            cap for cap in capabilities if cap["name"] == "conversations_history"
        )

        # Verify capability structure
        assert "description" in history_cap
        assert "example" in history_cap
        assert "example_args" in history_cap
        assert "example_response" in history_cap

        # Verify example arguments
        example_args = history_cap["example_args"]
        assert "channel_id" in example_args
        assert "limit" in example_args
        assert "include_activity_messages" in example_args

    def test_conversations_replies_capability(self, template_config):
        """Test conversations_replies capability definition."""
        capabilities = template_config["capabilities"]

        replies_cap = next(
            cap for cap in capabilities if cap["name"] == "conversations_replies"
        )

        # Verify capability structure
        assert "description" in replies_cap
        assert "example" in replies_cap

        # Verify example arguments include thread_ts
        example_args = replies_cap["example_args"]
        assert "channel_id" in example_args
        assert "thread_ts" in example_args

    def test_message_posting_capability(self, template_config):
        """Test conversations_add_message capability definition."""
        capabilities = template_config["capabilities"]

        posting_cap = next(
            cap for cap in capabilities if cap["name"] == "conversations_add_message"
        )

        # Verify safety messaging in description
        assert "safety" in posting_cap["description"].lower()

        # Verify example arguments
        example_args = posting_cap["example_args"]
        assert "channel_id" in example_args
        assert "text" in example_args

    def test_search_messages_capability(self, template_config):
        """Test search_messages capability definition."""
        capabilities = template_config["capabilities"]

        search_cap = next(
            cap for cap in capabilities if cap["name"] == "search_messages"
        )

        # Verify capability structure
        assert "description" in search_cap

        # Verify example arguments
        example_args = search_cap["example_args"]
        assert "query" in example_args
        assert "sort" in example_args
        assert "count" in example_args

    @patch("requests.post")
    def test_mock_conversations_history_call(self, mock_post, mock_slack_response):
        """Test mocked conversations_history API call."""
        # Configure mock response
        mock_post.return_value.json.return_value = mock_slack_response
        mock_post.return_value.status_code = 200

        # This would be the actual API call in the slack server
        # We're testing the mock setup here
        import requests

        response = requests.post(
            "https://slack.com/api/conversations.history",
            headers={"Authorization": "Bearer xoxb-test-token"},
            json={"channel": "C123456789", "limit": 10},
        )

        result = response.json()

        # Verify mock response structure
        assert result["ok"] is True
        assert "messages" in result
        assert len(result["messages"]) == 2
        assert result["messages"][0]["user"] == "U123456789"

    @patch("requests.post")
    def test_mock_search_messages_call(self, mock_post, mock_search_response):
        """Test mocked search.messages API call."""
        # Configure mock response
        mock_post.return_value.json.return_value = mock_search_response
        mock_post.return_value.status_code = 200

        import requests

        response = requests.post(
            "https://slack.com/api/search.messages",
            headers={"Authorization": "Bearer xoxb-test-token"},
            json={"query": "test query", "sort": "timestamp"},
        )

        result = response.json()

        # Verify mock response structure
        assert result["ok"] is True
        assert "messages" in result
        assert result["messages"]["total"] == 2
        assert len(result["messages"]["matches"]) == 1

    def test_channel_id_formats(self, template_config):
        """Test that channel ID format examples are documented."""
        capabilities = template_config["capabilities"]

        # Check that examples include different channel formats
        history_cap = next(
            cap for cap in capabilities if cap["name"] == "conversations_history"
        )

        # Should document #channel and @user formats
        description = history_cap["description"].lower()
        assert (
            "#" in str(history_cap["example_args"]["channel_id"])
            or "channel" in description
        )

    def test_pagination_support(self, template_config):
        """Test that pagination is documented in capabilities."""
        capabilities = template_config["capabilities"]

        history_cap = next(
            cap for cap in capabilities if cap["name"] == "conversations_history"
        )

        # Should mention pagination or cursor
        description = history_cap["description"].lower()
        assert "pagination" in description or "cursor" in description

    def test_thread_support(self, template_config):
        """Test that thread support is properly documented."""
        capabilities = template_config["capabilities"]

        replies_cap = next(
            cap for cap in capabilities if cap["name"] == "conversations_replies"
        )

        # Should have thread_ts in example
        example_args = replies_cap["example_args"]
        assert "thread_ts" in example_args
        assert example_args["thread_ts"] == "1234567890.123456"

    def test_user_lookup_capability(self, template_config):
        """Test user management capability."""
        capabilities = template_config["capabilities"]

        user_cap = next(cap for cap in capabilities if cap["name"] == "user_management")

        # Should include user lookup functionality
        description = user_cap["description"].lower()
        assert "user" in description
        assert "lookup" in description or "information" in description

    def test_channel_management_capability(self, template_config):
        """Test channel management capability."""
        capabilities = template_config["capabilities"]

        channel_cap = next(
            cap for cap in capabilities if cap["name"] == "channel_management"
        )

        # Should include channel operations
        description = channel_cap["description"].lower()
        assert "channel" in description
        assert "list" in description or "lookup" in description

    @patch("requests.post")
    def test_mock_error_handling(self, mock_post):
        """Test mock error response handling."""
        # Configure mock error response
        mock_post.return_value.json.return_value = {
            "ok": False,
            "error": "channel_not_found",
            "response_metadata": {},
        }
        mock_post.return_value.status_code = 200

        import requests

        response = requests.post(
            "https://slack.com/api/conversations.history",
            headers={"Authorization": "Bearer xoxb-invalid-token"},
            json={"channel": "invalid_channel"},
        )

        result = response.json()

        # Verify error response structure
        assert result["ok"] is False
        assert "error" in result
        assert result["error"] == "channel_not_found"

    def test_authentication_modes_documented(self, template_config):
        """Test that authentication modes are documented in examples."""
        examples = template_config.get("examples", {})

        # Should have cookie and OAuth authentication examples
        assert "cookie_authentication" in examples
        assert "oauth_authentication" in examples

        oauth_example = examples["oauth_authentication"]
        assert "description" in oauth_example
        assert "config" in oauth_example

        cookie_example = examples["cookie_authentication"]
        assert "description" in cookie_example
        assert "config" in cookie_example

    def test_safety_features_documented(self, template_config):
        """Test that safety features are documented."""
        examples = template_config.get("examples", {})

        # Should have message posting example
        assert "message_posting" in examples

        posting_example = examples["message_posting"]
        assert "description" in posting_example
        assert (
            "disabled by default" in posting_example["description"].lower()
            or "channel controls" in posting_example["description"].lower()
        )
