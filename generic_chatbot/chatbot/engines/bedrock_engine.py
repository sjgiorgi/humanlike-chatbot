"""
Amazon Bedrock engine for Kani framework.
"""

import asyncio
import os
from concurrent.futures import ThreadPoolExecutor
from typing import Any, Dict, List, Optional

import boto3
from botocore.exceptions import ClientError
from kani.engines.base import BaseCompletion, BaseEngine
from kani.models import ChatMessage, ChatRole
from kani.prompts.pipeline import PromptPipeline


class BedrockCompletion(BaseCompletion):
    """Completion wrapper for Bedrock responses."""

    def __init__(self, message: ChatMessage, prompt_tokens: Optional[int] = None, completion_tokens: Optional[int] = None):
        self._message = message
        self._prompt_tokens = prompt_tokens
        self._completion_tokens = completion_tokens

    @property
    def message(self) -> ChatMessage:
        return self._message

    @property
    def prompt_tokens(self) -> Optional[int]:
        return self._prompt_tokens

    @property
    def completion_tokens(self) -> Optional[int]:
        return self._completion_tokens


class BedrockEngine(BaseEngine):
    """Amazon Bedrock engine for Kani framework."""

    def __init__(
        self,
        model_id: str,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        region_name: str = "us-east-1",
        max_tokens: int = 1000,
        temperature: float = 0.7,
        top_p: float = 0.9,
        **kwargs,
    ):
        super().__init__(**kwargs)

        self.model_id = model_id
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.top_p = top_p

        # Initialize Bedrock client
        self.client = boto3.client(
            "bedrock-runtime",
            aws_access_key_id=aws_access_key_id or os.getenv(
                "AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=aws_secret_access_key or os.getenv(
                "AWS_SECRET_ACCESS_KEY"),
            region_name=region_name,
        )

        # Set context size based on model
        self.max_context_size = self._get_model_context_size(model_id)

        # Thread pool for running sync Bedrock calls
        self._executor = ThreadPoolExecutor(max_workers=1)

        # Create prompt pipeline
        self.pipeline = self._create_pipeline()

    def _get_model_context_size(self, model_id: str) -> int:
        """Get context size for the model."""
        context_sizes = {
            "meta.llama3-8b-instruct-v1:0": 8192,
            "meta.llama3-70b-instruct-v1:0": 8192,
            "meta.llama3.1-8b-instruct-v1:0": 8192,
            "meta.llama3.1-70b-instruct-v1:0": 8192,
            "meta.llama3.2-1b-instruct-v1:0": 8192,
            "meta.llama3.2-3b-instruct-v1:0": 8192,
            "meta.llama3.2-11b-instruct-v1:0": 8192,
            "meta.llama3.2-90b-instruct-v1:0": 8192,
            "meta.llama3.3-70b-instruct-v1:0": 8192,
            "anthropic.claude-3-sonnet-20240229-v1:0": 200000,
            "anthropic.claude-3-haiku-20240307-v1:0": 200000,
        }
        return context_sizes.get(model_id, 8192)

    def _create_pipeline(self) -> PromptPipeline:
        """Create the prompt pipeline for Bedrock message conversion."""
        return (
            PromptPipeline()
            # Convert to Bedrock format: list of dicts with role/content
            .conversation_dict(
                system_role="user",  # Map system to user for Bedrock
                user_role="user",
                assistant_role="assistant",
                function_role="user",  # Map function to user for Bedrock
                content_transform=self._transform_content,
            )
            # Ensure conversation starts with user message (after role mapping)
            .macro_apply(self._ensure_starts_with_user)
            # Ensure conversation ends with user message (Bedrock requirement)
            .macro_apply(self._ensure_ends_with_user)
        )

    def _transform_content(self, message: ChatMessage) -> List[Dict[str, str]]:
        """Transform message content to Bedrock format."""
        if isinstance(message.content, str):
            return [{"text": message.content}]
        elif isinstance(message.content, list):
            return message.content
        else:
            return [{"text": str(message.content)}]

    def _ensure_starts_with_user(self, messages: List[Dict], functions: List) -> List[Dict]:
        """Ensure the conversation starts with a user message (system prompt)."""
        if not messages or messages[0]["role"] != "user":
            # If no system prompt at start, add a default one
            messages.insert(0, {
                "role": "user",
                "content": [{"text": "You are a helpful assistant."}],
            })
        return messages

    def _ensure_ends_with_user(self, messages: List[Dict], functions: List) -> List[Dict]:
        """Ensure the conversation ends with a user message (Bedrock requirement)."""
        if not messages or messages[-1]["role"] != "user":
            messages.append(
                {"role": "user", "content": [{"text": "Continue"}]})
        return messages

    def message_len(self, message: ChatMessage) -> int:
        """Estimate message length in tokens."""
        if isinstance(message.content, str):
            # Rough estimation: 1 token ≈ 4 chars
            return len(message.content) // 4
        return 50  # Default for complex content

    async def predict(
        self,
        messages: List[ChatMessage],
        functions: Optional[List] = None,
        **kwargs,
    ) -> BedrockCompletion:
        """Generate a response from Bedrock."""
        try:
            # Convert messages using pipeline
            conversation = self.pipeline(messages, functions or [])

            # Call Bedrock in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                self._executor,
                self._call_bedrock,
                conversation,
            )

            # Extract response text
            response_text = response["output"]["message"]["content"][0]["text"]

            # Create response message
            response_message = ChatMessage(
                role=ChatRole.ASSISTANT, content=response_text)

            return BedrockCompletion(response_message)

        except Exception as e:
            raise RuntimeError(f"Bedrock API call failed: {e}")

    async def stream(
        self,
        messages: List[ChatMessage],
        functions: Optional[List] = None,
        **kwargs,
    ):
        """Stream a response from Bedrock."""
        try:
            # Convert messages using pipeline
            conversation = self.pipeline(messages, functions or [])

            # Call Bedrock in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                self._executor,
                self._call_bedrock_stream,
                conversation,
            )

            # Process the streaming response
            for event in response["stream"]:
                if "contentBlockDelta" in event:
                    # Extract text chunk from the delta
                    text_chunk = event["contentBlockDelta"]["delta"]["text"]
                    yield text_chunk

        except Exception as e:
            raise RuntimeError(f"Bedrock streaming API call failed: {e}")

    def _call_bedrock(self, conversation: List[Dict]) -> Dict[str, Any]:
        """Make the actual Bedrock API call."""
        try:
            response = self.client.converse(
                modelId=self.model_id,
                messages=conversation,
                inferenceConfig={
                    "maxTokens": self.max_tokens,
                    "temperature": self.temperature,
                    "topP": self.top_p,
                },
            )
            return response
        except ClientError as e:
            raise RuntimeError(f"Bedrock API call failed: {e}")

    def _call_bedrock_stream(self, conversation: List[Dict]) -> Dict[str, Any]:
        """Make the actual Bedrock streaming API call."""
        try:
            response = self.client.converse_stream(
                modelId=self.model_id,
                messages=conversation,
                inferenceConfig={
                    "maxTokens": self.max_tokens,
                    "temperature": self.temperature,
                    "topP": self.top_p,
                },
            )
            return response
        except ClientError as e:
            raise RuntimeError(f"Bedrock streaming API call failed: {e}")

    async def close(self):
        """Close the engine and cleanup resources."""
        if hasattr(self, "_executor"):
            self._executor.shutdown(wait=True)

    def explain_pipeline(self):
        """Print an explanation of the configured prompt pipeline."""
        print("BedrockEngine Prompt Pipeline:")
        print("=" * 40)
        self.pipeline.explain()
