"""
Minimal test to validate prompt and chat history passing to Kani engines.
Tests engine agnosticism - both engines receive identical inputs from Kani.
Mocks only external API calls to test role mapping and message transformation.
"""

import os
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from kani import ChatMessage, ChatRole, Kani
from kani.engines.anthropic import AnthropicEngine
from chatbot.engines.bedrock_engine import BedrockEngine


class TestEngineInputPassing:
    """Test that Bedrock and Anthropic engines receive identical inputs from Kani framework."""

    # Test data - DRY principle: define once, use everywhere
    SYSTEM_PROMPT = "You are a helpful assistant."
    CHAT_HISTORY = [
        ChatMessage(role=ChatRole.USER, content="Hello"),
        ChatMessage(role=ChatRole.ASSISTANT, content="Hi there!"),
        ChatMessage(role=ChatRole.USER, content="How are you?")
    ]
    USER_QUERY = "What's your name?"

    @pytest.mark.asyncio
    async def test_anthropic_role_mapping(self):
        """Test Anthropic engine role mapping and message format."""
        with patch('kani.engines.anthropic.engine.AsyncAnthropic') as mock_anthropic:
            # Mock Anthropic client
            mock_client = MagicMock()
            mock_anthropic.return_value = mock_client

            # Mock response with proper structure
            mock_content = MagicMock()
            mock_content.type = "text"
            mock_content.text = "Test response"

            mock_response = MagicMock()
            mock_response.content = [mock_content]
            mock_client.messages.create = AsyncMock(return_value=mock_response)

            # Create engine with environment variables
            anthropic_key = os.getenv("ANTHROPIC_API_KEY", "test-key")
            engine = AnthropicEngine(
                api_key=anthropic_key, model="claude-3-haiku-20240307")
            kani = Kani(engine, system_prompt=self.SYSTEM_PROMPT,
                        chat_history=self.CHAT_HISTORY)

            # Make request
            await kani.chat_round_str(self.USER_QUERY)

            # Assert API call parameters
            call_args = mock_client.messages.create.call_args
            kwargs = call_args[1]

            # System prompt should go to system parameter (not messages)
            assert kwargs['system'] == self.SYSTEM_PROMPT

            # Chat history should be in messages array
            messages = kwargs['messages']
            # 3 history + 1 new (no system in messages) - but Kani merges consecutive messages
            assert len(messages) == 3  # Kani merges consecutive user messages
            assert messages[0]['content'][0]['text'] == "Hello"
            assert messages[1]['content'][0]['text'] == "Hi there!"
            # Merged user messages
            assert messages[2]['content'][0]['text'] == f"How are you?\n{self.USER_QUERY}"

    @pytest.mark.asyncio
    async def test_bedrock_role_mapping(self):
        """Test Bedrock engine role mapping and message format."""
        with patch('chatbot.engines.bedrock_engine.boto3.client') as mock_boto3:
            # Mock Bedrock client
            mock_client = MagicMock()
            mock_boto3.return_value = mock_client

            # Mock response
            mock_response = {
                'output': {
                    'message': {
                        'content': [{'text': 'Test response'}]
                    }
                }
            }
            mock_client.converse.return_value = mock_response

            # Create engine with environment variables
            aws_key = os.getenv("AWS_ACCESS_KEY_ID", "test-key")
            aws_secret = os.getenv("AWS_SECRET_ACCESS_KEY", "test-secret")
            engine = BedrockEngine(
                model_id="meta.llama3-8b-instruct-v1:0",
                aws_access_key_id=aws_key,
                aws_secret_access_key=aws_secret,
                region_name="us-east-1"
            )
            kani = Kani(engine, system_prompt=self.SYSTEM_PROMPT,
                        chat_history=self.CHAT_HISTORY)

            # Make request
            await kani.chat_round_str(self.USER_QUERY)

            # Assert API call parameters
            call_args = mock_client.converse.call_args
            messages = call_args[1]['messages']

            # System prompt should be mapped to user role (first message)
            assert messages[0]['role'] == 'user'
            assert messages[0]['content'][0]['text'] == self.SYSTEM_PROMPT

            # Chat history should be preserved in Bedrock format
            # system + 3 history + 1 new + assistant response + continue message
            assert len(messages) >= 5  # At least system + 3 history + 1 new
            assert messages[1]['content'][0]['text'] == "Hello"
            assert messages[2]['content'][0]['text'] == "Hi there!"
            assert messages[3]['content'][0]['text'] == "How are you?"
            assert messages[4]['content'][0]['text'] == self.USER_QUERY

    def test_engine_interface_consistency(self):
        """Test that both engines implement same Kani interface."""
        # Test method existence
        assert hasattr(AnthropicEngine, 'predict')
        assert hasattr(AnthropicEngine, 'stream')
        assert hasattr(BedrockEngine, 'predict')
        assert hasattr(BedrockEngine, 'stream')

        # Test engine creation
        anthropic_key = os.getenv("ANTHROPIC_API_KEY", "test-key")
        aws_key = os.getenv("AWS_ACCESS_KEY_ID", "test-key")
        aws_secret = os.getenv("AWS_SECRET_ACCESS_KEY", "test-secret")

        anthropic_engine = AnthropicEngine(
            api_key=anthropic_key, model="claude-3-haiku-20240307")
        bedrock_engine = BedrockEngine(
            model_id="meta.llama3-8b-instruct-v1:0",
            aws_access_key_id=aws_key,
            aws_secret_access_key=aws_secret,
            region_name="us-east-1"
        )

        # Both engines should be usable with Kani
        anthropic_kani = Kani(
            anthropic_engine, system_prompt=self.SYSTEM_PROMPT)
        bedrock_kani = Kani(bedrock_engine, system_prompt=self.SYSTEM_PROMPT)

        assert anthropic_kani is not None
        assert bedrock_kani is not None

    def test_pipeline_transformation(self):
        """Test that BedrockEngine pipeline transforms roles correctly."""
        # Create engine
        engine = BedrockEngine(
            model_id="meta.llama3-8b-instruct-v1:0",
            aws_access_key_id="test-key",
            aws_secret_access_key="test-secret",
            region_name="us-east-1"
        )

        # Test pipeline transformation
        messages = [
            ChatMessage(role=ChatRole.SYSTEM, content="You are helpful"),
            ChatMessage(role=ChatRole.USER, content="Hello"),
            ChatMessage(role=ChatRole.ASSISTANT, content="Hi there!")
        ]

        # Transform messages through pipeline
        transformed = engine.pipeline(messages, [])

        # Assert role mapping
        assert transformed[0]['role'] == 'user'  # System mapped to user
        assert transformed[0]['content'][0]['text'] == "You are helpful"
        assert transformed[1]['role'] == 'user'
        assert transformed[1]['content'][0]['text'] == "Hello"
        assert transformed[2]['role'] == 'assistant'
        assert transformed[2]['content'][0]['text'] == "Hi there!"

    @pytest.mark.asyncio
    async def test_engine_agnosticism(self):
        """Test that both engines work identically with Kani interface."""
        # Test Anthropic
        with patch('kani.engines.anthropic.engine.AsyncAnthropic') as mock_anthropic:
            mock_client = MagicMock()
            mock_anthropic.return_value = mock_client
            # Mock response with proper structure
            mock_content = MagicMock()
            mock_content.type = "text"
            mock_content.text = "Anthropic response"

            mock_response = MagicMock()
            mock_response.content = [mock_content]
            mock_client.messages.create = AsyncMock(return_value=mock_response)

            anthropic_key = os.getenv("ANTHROPIC_API_KEY", "test-key")
            anthropic_engine = AnthropicEngine(
                api_key=anthropic_key, model="claude-3-haiku-20240307")
            anthropic_kani = Kani(
                anthropic_engine, system_prompt=self.SYSTEM_PROMPT)
            anthropic_response = await anthropic_kani.chat_round_str("Hello")
            assert anthropic_response == "Anthropic response"

        # Test Bedrock
        with patch('chatbot.engines.bedrock_engine.boto3.client') as mock_boto3:
            mock_client = MagicMock()
            mock_boto3.return_value = mock_client
            mock_response = {
                'output': {
                    'message': {
                        'content': [{'text': 'Bedrock response'}]
                    }
                }
            }
            mock_client.converse.return_value = mock_response

            aws_key = os.getenv("AWS_ACCESS_KEY_ID", "test-key")
            aws_secret = os.getenv("AWS_SECRET_ACCESS_KEY", "test-secret")
            bedrock_engine = BedrockEngine(
                model_id="meta.llama3-8b-instruct-v1:0",
                aws_access_key_id=aws_key,
                aws_secret_access_key=aws_secret,
                region_name="us-east-1"
            )
            bedrock_kani = Kani(
                bedrock_engine, system_prompt=self.SYSTEM_PROMPT)
            bedrock_response = await bedrock_kani.chat_round_str("Hello")
            assert bedrock_response == "Bedrock response"

        # Both engines should work with same Kani interface
        assert anthropic_response is not None
        assert bedrock_response is not None
