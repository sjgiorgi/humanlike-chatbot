"""
Test all engines with real API calls to verify functionality.
Tests OpenAI, Anthropic, and Bedrock engines with actual API responses.
"""

import os
import pytest
from kani import Kani
from kani.engines.openai import OpenAIEngine
from kani.engines.anthropic import AnthropicEngine
from chatbot.engines.bedrock_engine import BedrockEngine
from server.engine import initialize_engine, initialize_engine_from_model


class TestRealEngineAPICalls:
    """Test all engines with real API calls."""

    # Test data - simple prompt for all engines
    TEST_PROMPT = "Hello, how are you? Please respond in one sentence."
    SYSTEM_PROMPT = "You are a helpful assistant."

    @pytest.mark.asyncio
    async def test_openai_engines_real_api(self):
        """Test OpenAI engines with real API calls."""
        openai_key = os.getenv("OPENAI_API_KEY")
        if not openai_key:
            pytest.skip("OPENAI_API_KEY not set")

        # Test GPT-4o
        engine = OpenAIEngine(api_key=openai_key, model="gpt-4o")
        kani = Kani(engine, system_prompt=self.SYSTEM_PROMPT)

        response = await kani.chat_round_str(self.TEST_PROMPT)
        assert response is not None
        assert len(response) > 0
        print(f"GPT-4o response: {response}")

        # Test GPT-4o-mini
        engine = OpenAIEngine(api_key=openai_key, model="gpt-4o-mini")
        kani = Kani(engine, system_prompt=self.SYSTEM_PROMPT)

        response = await kani.chat_round_str(self.TEST_PROMPT)
        assert response is not None
        assert len(response) > 0
        print(f"GPT-4o-mini response: {response}")

        # Test GPT-3.5-turbo
        engine = OpenAIEngine(api_key=openai_key, model="gpt-3.5-turbo")
        kani = Kani(engine, system_prompt=self.SYSTEM_PROMPT)

        response = await kani.chat_round_str(self.TEST_PROMPT)
        assert response is not None
        assert len(response) > 0
        print(f"GPT-3.5-turbo response: {response}")

    @pytest.mark.asyncio
    async def test_anthropic_engines_real_api(self):
        """Test Anthropic engines with real API calls."""
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        if not anthropic_key:
            pytest.skip("ANTHROPIC_API_KEY not set")

        # Test Claude Sonnet 4
        engine = AnthropicEngine(
            api_key=anthropic_key, model="claude-sonnet-4-20250514")
        kani = Kani(engine, system_prompt=self.SYSTEM_PROMPT)

        response = await kani.chat_round_str(self.TEST_PROMPT)
        assert response is not None
        assert len(response) > 0
        print(f"Claude Sonnet 4 response: {response}")

        # Test Claude 3.5 Haiku
        engine = AnthropicEngine(
            api_key=anthropic_key, model="claude-3-5-haiku-20241022")
        kani = Kani(engine, system_prompt=self.SYSTEM_PROMPT)

        response = await kani.chat_round_str(self.TEST_PROMPT)
        assert response is not None
        assert len(response) > 0
        print(f"Claude 3.5 Haiku response: {response}")

        # Test Claude 3 Haiku
        engine = AnthropicEngine(
            api_key=anthropic_key, model="claude-3-haiku-20240307")
        kani = Kani(engine, system_prompt=self.SYSTEM_PROMPT)

        response = await kani.chat_round_str(self.TEST_PROMPT)
        assert response is not None
        assert len(response) > 0
        print(f"Claude 3 Haiku response: {response}")

    @pytest.mark.asyncio
    async def test_bedrock_engines_real_api(self):
        """Test Bedrock engines with real API calls."""
        aws_key = os.getenv("AWS_ACCESS_KEY_ID")
        aws_secret = os.getenv("AWS_SECRET_ACCESS_KEY")
        if not aws_key or not aws_secret:
            pytest.skip("AWS credentials not set")

        # Test Llama 3 8B
        engine = BedrockEngine(
            model_id="meta.llama3-8b-instruct-v1:0",
            aws_access_key_id=aws_key,
            aws_secret_access_key=aws_secret,
            region_name="us-east-1"
        )
        kani = Kani(engine, system_prompt=self.SYSTEM_PROMPT)

        response = await kani.chat_round_str(self.TEST_PROMPT)
        assert response is not None
        assert len(response) > 0
        print(f"Llama 3 8B response: {response}")

        # Test Llama 3 70B
        engine = BedrockEngine(
            model_id="meta.llama3-70b-instruct-v1:0",
            aws_access_key_id=aws_key,
            aws_secret_access_key=aws_secret,
            region_name="us-east-1"
        )
        kani = Kani(engine, system_prompt=self.SYSTEM_PROMPT)

        response = await kani.chat_round_str(self.TEST_PROMPT)
        assert response is not None
        assert len(response) > 0
        print(f"Llama 3 70B response: {response}")

    @pytest.mark.asyncio
    async def test_engine_agnosticism_real_api(self):
        """Test that all engines work identically with Kani interface."""
        # Test OpenAI
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key:
            engine = OpenAIEngine(api_key=openai_key, model="gpt-4o-mini")
            kani = Kani(engine, system_prompt=self.SYSTEM_PROMPT)
            openai_response = await kani.chat_round_str(self.TEST_PROMPT)
            assert openai_response is not None
            print(f"OpenAI response: {openai_response}")

        # Test Anthropic
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        if anthropic_key:
            engine = AnthropicEngine(
                api_key=anthropic_key, model="claude-sonnet-4-20250514")
            kani = Kani(engine, system_prompt=self.SYSTEM_PROMPT)
            anthropic_response = await kani.chat_round_str(self.TEST_PROMPT)
            assert anthropic_response is not None
            print(f"Anthropic response: {anthropic_response}")

        # Test Bedrock
        aws_key = os.getenv("AWS_ACCESS_KEY_ID")
        aws_secret = os.getenv("AWS_SECRET_ACCESS_KEY")
        if aws_key and aws_secret:
            engine = BedrockEngine(
                model_id="meta.llama3-8b-instruct-v1:0",
                aws_access_key_id=aws_key,
                aws_secret_access_key=aws_secret,
                region_name="us-east-1"
            )
            kani = Kani(engine, system_prompt=self.SYSTEM_PROMPT)
            bedrock_response = await kani.chat_round_str(self.TEST_PROMPT)
            assert bedrock_response is not None
            print(f"Bedrock response: {bedrock_response}")

    @pytest.mark.asyncio
    async def test_engine_initialization_real_api(self):
        """Test engine initialization through chatbot's engine creation system."""
        # Test OpenAI engine creation
        openai_key = os.getenv("OPENAI_API_KEY")
        if openai_key:
            engine = initialize_engine("OpenAI", "gpt-4o-mini")
            assert engine is not None
            kani = Kani(engine, system_prompt=self.SYSTEM_PROMPT)
            response = await kani.chat_round_str(self.TEST_PROMPT)
            assert response is not None
            print(f"OpenAI via initialize_engine: {response}")

        # Test Anthropic engine creation
        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        if anthropic_key:
            engine = initialize_engine("Anthropic", "claude-sonnet-4-20250514")
            assert engine is not None
            kani = Kani(engine, system_prompt=self.SYSTEM_PROMPT)
            response = await kani.chat_round_str(self.TEST_PROMPT)
            assert response is not None
            print(f"Anthropic via initialize_engine: {response}")

        # Test Bedrock engine creation
        aws_key = os.getenv("AWS_ACCESS_KEY_ID")
        aws_secret = os.getenv("AWS_SECRET_ACCESS_KEY")
        if aws_key and aws_secret:
            engine = initialize_engine(
                "Bedrock", "meta.llama3-8b-instruct-v1:0")
            assert engine is not None
            kani = Kani(engine, system_prompt=self.SYSTEM_PROMPT)
            response = await kani.chat_round_str(self.TEST_PROMPT)
            assert response is not None
            print(f"Bedrock via initialize_engine: {response}")

    def test_engine_parameter_compatibility(self):
        """Test that all engines accept the same parameters through Kani interface."""
        # Test OpenAI
        openai_key = os.getenv("OPENAI_API_KEY", "test-key")
        engine = OpenAIEngine(api_key=openai_key, model="gpt-4o-mini")
        kani = Kani(engine, system_prompt=self.SYSTEM_PROMPT)
        assert kani is not None

        # Test Anthropic
        anthropic_key = os.getenv("ANTHROPIC_API_KEY", "test-key")
        engine = AnthropicEngine(
            api_key=anthropic_key, model="claude-3-5-haiku-20241022")
        kani = Kani(engine, system_prompt=self.SYSTEM_PROMPT)
        assert kani is not None

        # Test Bedrock
        aws_key = os.getenv("AWS_ACCESS_KEY_ID", "test-key")
        aws_secret = os.getenv("AWS_SECRET_ACCESS_KEY", "test-secret")
        engine = BedrockEngine(
            model_id="meta.llama3-8b-instruct-v1:0",
            aws_access_key_id=aws_key,
            aws_secret_access_key=aws_secret,
            region_name="us-east-1"
        )
        kani = Kani(engine, system_prompt=self.SYSTEM_PROMPT)
        assert kani is not None
