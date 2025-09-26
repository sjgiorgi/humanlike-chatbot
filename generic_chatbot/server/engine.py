import logging
import os

from kani.engines.anthropic import AnthropicEngine
from kani.engines.openai import OpenAIEngine
from chatbot.engines.bedrock_engine import BedrockEngine

# Get logger for this module
logger = logging.getLogger(__name__)


def initialize_engine(model_type, model_id, csv_name=""):
    """Initialize engine with model type and model ID (legacy support)"""
    if model_type == "OpenAI":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("Missing OPENAI_API_KEY.")
        return OpenAIEngine(api_key=api_key, model=model_id)

    if model_type == "Anthropic":
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("Missing ANTHROPIC_API_KEY.")
        return AnthropicEngine(api_key=api_key, model=model_id)

    if model_type == "Bedrock":
        aws_key = os.getenv("AWS_ACCESS_KEY_ID")
        aws_secret = os.getenv("AWS_SECRET_ACCESS_KEY")
        if not aws_key or not aws_secret:
            raise ValueError("Missing AWS credentials.")
        return BedrockEngine(
            model_id=model_id,
            aws_access_key_id=aws_key,
            aws_secret_access_key=aws_secret,
            region_name=os.getenv("AWS_REGION", "us-east-1")
        )

    raise ValueError(f"Unsupported model type: {model_type}")


def initialize_engine_from_model(model):
    """Initialize engine from Model instance"""
    if model.provider.name == "OpenAI":
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("Missing OPENAI_API_KEY.")
        return OpenAIEngine(api_key=api_key, model=model.model_id)

    if model.provider.name == "Anthropic":
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("Missing ANTHROPIC_API_KEY.")
        return AnthropicEngine(api_key=api_key, model=model.model_id)

    if model.provider.name == "Bedrock":
        aws_key = os.getenv("AWS_ACCESS_KEY_ID")
        aws_secret = os.getenv("AWS_SECRET_ACCESS_KEY")
        if not aws_key or not aws_secret:
            raise ValueError("Missing AWS credentials.")
        return BedrockEngine(
            model_id=model.model_id,
            aws_access_key_id=aws_key,
            aws_secret_access_key=aws_secret,
            region_name=os.getenv("AWS_REGION", "us-east-1")
        )

    raise ValueError(f"Unsupported model provider: {model.provider.name}")


def get_or_create_engine(model_type, model_id, engine_instances):
    """
    We pass in engine_instances so we do NOT rely on a global variable here.
    Legacy function for backward compatibility.
    """
    engine_key = (model_type, model_id)

    if engine_key not in engine_instances:
        logger.info(
            f"Initializing Engine: Type={model_type}, Model={model_id}")
        engine_instances[engine_key] = initialize_engine(model_type, model_id)

    return engine_instances[engine_key]


def get_or_create_engine_from_model(model, engine_instances):
    """
    Get or create engine from Model instance.
    We pass in engine_instances so we do NOT rely on a global variable here.
    """
    engine_key = (model.provider.name, model.model_id)

    if engine_key not in engine_instances:
        logger.info(
            f"Initializing Engine: Type={model.provider.name}, Model={model.model_id}",
        )
        engine_instances[engine_key] = initialize_engine_from_model(model)

    return engine_instances[engine_key]
