import logging
import os

from kani.engines.anthropic import AnthropicEngine
from kani.engines.openai import OpenAIEngine

# Get logger for this module
logger = logging.getLogger(__name__)


def initialize_engine(model_type, model_id, csv_name=""):
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

    raise ValueError(f"Unsupported model type: {model_type}")


def get_or_create_engine(model_type, model_id, engine_instances):
    """
    We pass in engine_instances so we do NOT rely on a global variable here.
    """
    engine_key = (model_type, model_id)

    if engine_key not in engine_instances:
        logger.info(f"Initializing Engine: Type={model_type}, Model={model_id}")
        engine_instances[engine_key] = initialize_engine(model_type, model_id)

    return engine_instances[engine_key]
