"""
Test BedrockEngine integration with chatbot's engine creation pattern.
Verifies compatibility with existing engine initialization methods.
"""

import os
import pytest
from unittest.mock import patch, MagicMock
from server.engine import initialize_engine, initialize_engine_from_model
from chatbot.engines.bedrock_engine import BedrockEngine


class TestEngineIntegration:
    """Test BedrockEngine integration with chatbot engine creation."""

    def test_initialize_engine_bedrock(self):
        """Test BedrockEngine creation through initialize_engine."""
        with patch.dict(os.environ, {
            'AWS_ACCESS_KEY_ID': 'test-key',
            'AWS_SECRET_ACCESS_KEY': 'test-secret',
            'AWS_REGION': 'us-west-2'
        }):
            engine = initialize_engine(
                "Bedrock", "meta.llama3-8b-instruct-v1:0")

            # Verify engine type and stored attributes
            assert isinstance(engine, BedrockEngine)
            assert engine.model_id == "meta.llama3-8b-instruct-v1:0"
            assert engine.max_tokens == 1000
            assert engine.temperature == 0.7
            assert engine.top_p == 0.9

    def test_initialize_engine_bedrock_default_region(self):
        """Test BedrockEngine with default region."""
        with patch.dict(os.environ, {
            'AWS_ACCESS_KEY_ID': 'test-key',
            'AWS_SECRET_ACCESS_KEY': 'test-secret'
        }):
            engine = initialize_engine(
                "Bedrock", "meta.llama3-8b-instruct-v1:0")

            # Verify engine is created successfully with default parameters
            assert isinstance(engine, BedrockEngine)
            assert engine.model_id == "meta.llama3-8b-instruct-v1:0"

    def test_initialize_engine_missing_credentials(self):
        """Test BedrockEngine with missing credentials."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValueError, match="Missing AWS credentials"):
                initialize_engine("Bedrock", "meta.llama3-8b-instruct-v1:0")

    def test_initialize_engine_from_model_bedrock(self):
        """Test BedrockEngine creation through initialize_engine_from_model."""
        # Mock Model instance
        mock_model = MagicMock()
        mock_model.provider.name = "Bedrock"
        mock_model.model_id = "meta.llama3-70b-instruct-v1:0"

        with patch.dict(os.environ, {
            'AWS_ACCESS_KEY_ID': 'test-key',
            'AWS_SECRET_ACCESS_KEY': 'test-secret',
            'AWS_REGION': 'eu-west-1'
        }):
            engine = initialize_engine_from_model(mock_model)

            # Verify engine type and parameters
            assert isinstance(engine, BedrockEngine)
            assert engine.model_id == "meta.llama3-70b-instruct-v1:0"
            assert engine.max_tokens == 1000
            assert engine.temperature == 0.7
            assert engine.top_p == 0.9

    def test_engine_parameter_compatibility(self):
        """Test that BedrockEngine uses same parameter pattern as other engines."""
        # Test that BedrockEngine can be created with minimal parameters
        # (matching the pattern used by OpenAI and Anthropic engines)
        with patch.dict(os.environ, {
            'AWS_ACCESS_KEY_ID': 'test-key',
            'AWS_SECRET_ACCESS_KEY': 'test-secret'
        }):
            engine = initialize_engine(
                "Bedrock", "meta.llama3-8b-instruct-v1:0")

            # Verify default parameters are set
            assert engine.max_tokens == 1000  # Default from BedrockEngine
            assert engine.temperature == 0.7  # Default from BedrockEngine
            assert engine.top_p == 0.9  # Default from BedrockEngine

            # Verify required parameters are set
            assert engine.model_id == "meta.llama3-8b-instruct-v1:0"

    def test_unsupported_model_type(self):
        """Test error handling for unsupported model types."""
        with pytest.raises(ValueError, match="Unsupported model type: InvalidEngine"):
            initialize_engine("InvalidEngine", "some-model")

    def test_unsupported_model_provider(self):
        """Test error handling for unsupported model providers."""
        mock_model = MagicMock()
        mock_model.provider.name = "InvalidProvider"
        mock_model.model_id = "some-model"

        with pytest.raises(ValueError, match="Unsupported model provider: InvalidProvider"):
            initialize_engine_from_model(mock_model)
