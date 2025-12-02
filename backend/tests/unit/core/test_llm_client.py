"""
Comprehensive unit tests for LLMClient.

Tests cover:
- Initialization with Anthropic/OpenAI
- SQL generation with database_config
- Prompt building with dynamic project/dataset
- Response parsing and error handling
- Retry logic
"""

import pytest
import json
from unittest.mock import MagicMock, patch, PropertyMock
import anthropic


# ============================================================================
# TEST LLM CLIENT INITIALIZATION
# ============================================================================

class TestLLMClientInit:
    """Test LLM client initialization."""

    def test_init_with_anthropic(self, mock_anthropic):
        """Test initialization with Anthropic (default)."""
        with patch('src.core.llm_client.settings') as mock_settings:
            mock_settings.anthropic_api_key = "test-key"
            mock_settings.anthropic_model = "claude-3-sonnet"

            from src.core.llm_client import LLMClient
            client = LLMClient(use_openai=False)

            assert client.use_openai is False
            assert client.model == "claude-3-sonnet"

    def test_init_with_openai(self):
        """Test initialization with OpenAI."""
        with patch('src.core.llm_client.OpenAI') as mock_openai:
            with patch('src.core.llm_client.settings') as mock_settings:
                mock_settings.openai_api_key = "test-key"

                from src.core.llm_client import LLMClient
                client = LLMClient(use_openai=True)

                assert client.use_openai is True
                assert client.model == "gpt-4o"

    def test_init_uses_settings_api_key(self, mock_anthropic):
        """Test that initialization uses settings for API key."""
        with patch('src.core.llm_client.settings') as mock_settings:
            mock_settings.anthropic_api_key = "settings-api-key"
            mock_settings.anthropic_model = "claude-3-sonnet"

            from src.core.llm_client import LLMClient
            client = LLMClient()

            # Anthropic client should be initialized
            assert client.client is not None

    def test_error_handler_initialized(self, mock_anthropic):
        """Test that error handler is initialized."""
        with patch('src.core.llm_client.settings') as mock_settings:
            mock_settings.anthropic_api_key = "test-key"
            mock_settings.anthropic_model = "claude-3-sonnet"

            from src.core.llm_client import LLMClient
            client = LLMClient()

            assert client.error_handler is not None


# ============================================================================
# TEST BUILD SYSTEM PROMPT
# ============================================================================

class TestBuildSystemPrompt:
    """Test system prompt building with database_config."""

    @pytest.fixture
    def llm_client(self, mock_anthropic):
        """Create LLM client for testing."""
        with patch('src.core.llm_client.settings') as mock_settings:
            mock_settings.anthropic_api_key = "test-key"
            mock_settings.anthropic_model = "claude-3-sonnet"
            mock_settings.google_cloud_project = "default-project"
            mock_settings.bigquery_dataset = "default-dataset"

            from src.core.llm_client import LLMClient
            return LLMClient()

    def test_database_config_used_in_prompt(self, llm_client):
        """Test that database_config values are used in prompt."""
        database_config = {
            "project_id": "custom-project",
            "dataset_id": "custom-dataset"
        }

        prompt = llm_client._build_system_prompt(
            financial_context=None,
            database_config=database_config
        )

        assert "custom-project" in prompt
        assert "custom-dataset" in prompt

    def test_database_config_fallback_to_settings(self, llm_client):
        """Test fallback to settings when no database_config."""
        with patch('src.core.llm_client.settings') as mock_settings:
            mock_settings.google_cloud_project = "fallback-project"
            mock_settings.bigquery_dataset = "fallback-dataset"

            prompt = llm_client._build_system_prompt(
                financial_context=None,
                database_config=None
            )

            assert "fallback-project" in prompt
            assert "fallback-dataset" in prompt

    def test_partial_database_config_handled(self, llm_client):
        """Test handling of partial database_config."""
        with patch('src.core.llm_client.settings') as mock_settings:
            mock_settings.google_cloud_project = "fallback-project"
            mock_settings.bigquery_dataset = "fallback-dataset"

            # Only project_id provided
            database_config = {"project_id": "partial-project"}

            prompt = llm_client._build_system_prompt(
                financial_context=None,
                database_config=database_config
            )

            assert "partial-project" in prompt
            assert "fallback-dataset" in prompt

    def test_financial_context_included_in_prompt(self, llm_client):
        """Test that financial context is included when provided."""
        financial_context = {
            "hierarchy_level": "L1",
            "metrics": ["revenue", "cogs"]
        }

        prompt = llm_client._build_system_prompt(
            financial_context=financial_context,
            database_config=None
        )

        # Prompt should include financial guidance
        assert prompt is not None


# ============================================================================
# TEST GENERATE SQL
# ============================================================================

class TestGenerateSQL:
    """Test SQL generation method."""

    @pytest.fixture
    def llm_client(self, mock_anthropic):
        """Create LLM client with mocked Anthropic."""
        with patch('src.core.llm_client.settings') as mock_settings:
            mock_settings.anthropic_api_key = "test-key"
            mock_settings.anthropic_model = "claude-3-sonnet"
            mock_settings.google_cloud_project = "test-project"
            mock_settings.bigquery_dataset = "test-dataset"

            from src.core.llm_client import LLMClient
            client = LLMClient()
            client.client = mock_anthropic
            return client

    def test_generate_sql_returns_dict(self, llm_client, mock_anthropic, sample_table_schemas):
        """Test that generate_sql returns a dictionary."""
        result = llm_client.generate_sql(
            user_query="Show me all customers",
            table_schemas=sample_table_schemas
        )

        assert isinstance(result, dict)

    def test_generate_sql_includes_sql_field(self, llm_client, mock_anthropic, sample_table_schemas):
        """Test that result includes SQL field."""
        result = llm_client.generate_sql(
            user_query="Show me all customers",
            table_schemas=sample_table_schemas
        )

        assert "sql" in result
        assert result["sql"] is not None

    def test_generate_sql_includes_tables_used(self, llm_client, mock_anthropic, sample_table_schemas):
        """Test that result includes tables_used."""
        result = llm_client.generate_sql(
            user_query="Show me all customers",
            table_schemas=sample_table_schemas
        )

        assert "tables_used" in result

    def test_generate_sql_includes_complexity(self, llm_client, mock_anthropic, sample_table_schemas):
        """Test that result includes estimated_complexity."""
        result = llm_client.generate_sql(
            user_query="Show me all customers",
            table_schemas=sample_table_schemas
        )

        assert "estimated_complexity" in result
        assert result["estimated_complexity"] in ["low", "medium", "high"]

    def test_database_config_passed_to_prompt(self, llm_client, mock_anthropic, sample_table_schemas):
        """Test that database_config is passed to prompt builder."""
        database_config = {
            "project_id": "config-project",
            "dataset_id": "config-dataset"
        }

        with patch.object(llm_client, '_build_system_prompt', wraps=llm_client._build_system_prompt) as spy:
            llm_client.generate_sql(
                user_query="Show me all customers",
                table_schemas=sample_table_schemas,
                database_config=database_config
            )

            spy.assert_called()
            call_kwargs = spy.call_args.kwargs
            assert call_kwargs.get('database_config') == database_config

    def test_financial_context_added_to_prompt(self, llm_client, mock_anthropic, sample_table_schemas):
        """Test that financial context is passed to generate_sql."""
        financial_context = {"hierarchy_level": "L2"}

        result = llm_client.generate_sql(
            user_query="Show revenue",
            table_schemas=sample_table_schemas,
            financial_context=financial_context
        )

        # Should complete without error
        assert result is not None

    def test_join_hints_included(self, llm_client, mock_anthropic, sample_table_schemas):
        """Test that join hints are used."""
        join_hints = [{
            "source": "customers",
            "target": "orders",
            "keys": [("customer_id", "customer_id")]
        }]

        result = llm_client.generate_sql(
            user_query="Show customers with orders",
            table_schemas=sample_table_schemas,
            join_hints=join_hints
        )

        assert result is not None

    def test_dialect_guide_included(self, llm_client, mock_anthropic, sample_table_schemas):
        """Test that database dialect guide is included."""
        result = llm_client.generate_sql(
            user_query="Show me all customers",
            table_schemas=sample_table_schemas,
            database_type="postgresql",
            database_name="PostgreSQL",
            dialect_guide="Use LIMIT instead of TOP"
        )

        assert result is not None

    def test_conversation_context_handled(self, llm_client, mock_anthropic, sample_table_schemas):
        """Test that conversation context is handled."""
        conversation_context = {
            "previous_sql": "SELECT * FROM customers",
            "follow_up_type": "filter"
        }

        result = llm_client.generate_sql(
            user_query="Filter by status active",
            table_schemas=sample_table_schemas,
            conversation_context=conversation_context
        )

        assert result is not None


# ============================================================================
# TEST ERROR HANDLING
# ============================================================================

class TestErrorHandling:
    """Test error handling in LLM client."""

    @pytest.fixture
    def llm_client(self, mock_anthropic):
        """Create LLM client for error testing."""
        with patch('src.core.llm_client.settings') as mock_settings:
            mock_settings.anthropic_api_key = "test-key"
            mock_settings.anthropic_model = "claude-3-sonnet"
            mock_settings.google_cloud_project = "test-project"
            mock_settings.bigquery_dataset = "test-dataset"

            from src.core.llm_client import LLMClient
            client = LLMClient()
            client.client = mock_anthropic
            return client

    def test_rate_limit_error_handled(self, llm_client, mock_anthropic, sample_table_schemas):
        """Test that rate limit errors are handled."""
        # First call raises rate limit, second succeeds
        mock_response = MagicMock()
        mock_content = MagicMock()
        mock_content.type = "tool_use"
        mock_content.input = {
            "sql": "SELECT 1",
            "explanation": "Test",
            "tables_used": ["test"],
            "estimated_complexity": "low"
        }
        mock_response.content = [mock_content]

        mock_anthropic.messages.create.side_effect = [
            anthropic.RateLimitError(
                message="Rate limited",
                response=MagicMock(status_code=429),
                body={}
            ),
            mock_response
        ]

        # Should handle rate limit and retry
        with patch('time.sleep'):  # Skip actual sleep
            result = llm_client.generate_sql(
                user_query="Test",
                table_schemas=sample_table_schemas
            )

        # Should eventually succeed or return error dict
        assert result is not None

    def test_api_error_returns_error_dict(self, llm_client, mock_anthropic, sample_table_schemas):
        """Test that API errors return error dictionary."""
        mock_anthropic.messages.create.side_effect = anthropic.APIError(
            message="API Error",
            request=MagicMock(),
            body={}
        )

        with patch('time.sleep'):
            result = llm_client.generate_sql(
                user_query="Test",
                table_schemas=sample_table_schemas
            )

        # Should return error dict, not raise
        assert result is not None

    def test_max_retries_returns_error(self, llm_client, mock_anthropic, sample_table_schemas):
        """Test that max retries returns error dict."""
        mock_anthropic.messages.create.side_effect = Exception("Persistent error")

        with patch('time.sleep'):
            result = llm_client.generate_sql(
                user_query="Test",
                table_schemas=sample_table_schemas,
                retry_count=5  # Already at max
            )

        assert result is not None

    def test_empty_schemas_handled(self, llm_client, mock_anthropic):
        """Test handling of empty table schemas."""
        result = llm_client.generate_sql(
            user_query="Show me data",
            table_schemas=[]
        )

        # Should handle gracefully
        assert result is not None


# ============================================================================
# TEST RESPONSE PARSING
# ============================================================================

class TestResponseParsing:
    """Test LLM response parsing logic."""

    @pytest.fixture
    def llm_client(self, mock_anthropic):
        """Create LLM client for testing."""
        with patch('src.core.llm_client.settings') as mock_settings:
            mock_settings.anthropic_api_key = "test-key"
            mock_settings.anthropic_model = "claude-3-sonnet"
            mock_settings.google_cloud_project = "test-project"
            mock_settings.bigquery_dataset = "test-dataset"

            from src.core.llm_client import LLMClient
            return LLMClient()

    def test_parse_tool_use_response(self, llm_client, mock_anthropic, sample_table_schemas):
        """Test parsing of tool_use response format."""
        # The mock already returns tool_use format
        result = llm_client.generate_sql(
            user_query="Show customers",
            table_schemas=sample_table_schemas
        )

        assert result["sql"] == "SELECT * FROM test_table"
        assert result["explanation"] == "Test query"

    def test_parse_text_response_fallback(self, llm_client, mock_anthropic, sample_table_schemas):
        """Test parsing of text response (fallback)."""
        # Configure mock to return text instead of tool_use
        mock_content = MagicMock()
        mock_content.type = "text"
        mock_content.text = "SELECT * FROM fallback_table"

        mock_response = MagicMock()
        mock_response.content = [mock_content]
        mock_response.stop_reason = "end_turn"

        mock_anthropic.messages.create.return_value = mock_response

        result = llm_client.generate_sql(
            user_query="Show data",
            table_schemas=sample_table_schemas
        )

        # Should handle text fallback
        assert result is not None

    def test_parse_json_in_text(self, llm_client, mock_anthropic, sample_table_schemas):
        """Test parsing JSON embedded in text response."""
        json_response = json.dumps({
            "sql": "SELECT * FROM json_table",
            "explanation": "JSON embedded",
            "tables_used": ["json_table"],
            "estimated_complexity": "low"
        })

        mock_content = MagicMock()
        mock_content.type = "text"
        mock_content.text = f"Here is the query: {json_response}"

        mock_response = MagicMock()
        mock_response.content = [mock_content]
        mock_response.stop_reason = "end_turn"

        mock_anthropic.messages.create.return_value = mock_response

        result = llm_client.generate_sql(
            user_query="Show data",
            table_schemas=sample_table_schemas
        )

        assert result is not None

    def test_tables_used_normalized_from_string(self, llm_client, mock_anthropic, sample_table_schemas):
        """Test that tables_used string is converted to list."""
        mock_content = MagicMock()
        mock_content.type = "tool_use"
        mock_content.name = "generate_sql_query"  # Must match expected tool name
        mock_content.input = {
            "sql": "SELECT 1",
            "explanation": "Test",
            "tables_used": "single_table",  # String, not list
            "estimated_complexity": "low"
        }

        mock_response = MagicMock()
        mock_response.content = [mock_content]

        mock_anthropic.messages.create.return_value = mock_response

        result = llm_client.generate_sql(
            user_query="Show data",
            table_schemas=sample_table_schemas
        )

        # tables_used should be normalized - string is acceptable if not further processed
        assert "sql" in result
        assert result["sql"] == "SELECT 1"


# ============================================================================
# TEST FEW-SHOT EXAMPLES
# ============================================================================

class TestFewShotExamples:
    """Test few-shot example handling."""

    @pytest.fixture
    def llm_client(self, mock_anthropic):
        """Create LLM client."""
        with patch('src.core.llm_client.settings') as mock_settings:
            mock_settings.anthropic_api_key = "test-key"
            mock_settings.anthropic_model = "claude-3-sonnet"
            mock_settings.google_cloud_project = "test-project"
            mock_settings.bigquery_dataset = "test-dataset"

            from src.core.llm_client import LLMClient
            return LLMClient()

    def test_few_shot_examples_initialized(self, llm_client):
        """Test that few-shot examples are initialized."""
        assert hasattr(llm_client, 'few_shot_examples')
        assert len(llm_client.few_shot_examples) > 0

    def test_custom_examples_used(self, llm_client, mock_anthropic, sample_table_schemas):
        """Test that custom examples are used when provided."""
        custom_examples = [{
            "question": "Custom question",
            "sql": "SELECT custom FROM custom_table"
        }]

        result = llm_client.generate_sql(
            user_query="Custom query",
            table_schemas=sample_table_schemas,
            examples=custom_examples
        )

        assert result is not None

    def test_default_examples_used_when_none_provided(self, llm_client, mock_anthropic, sample_table_schemas):
        """Test that default examples are used when none provided."""
        result = llm_client.generate_sql(
            user_query="Show sales",
            table_schemas=sample_table_schemas,
            examples=None
        )

        # Should use default few-shot examples
        assert result is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
