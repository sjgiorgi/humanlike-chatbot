import json
import logging

from asgiref.sync import sync_to_async
from django.core.cache import cache
from kani import ChatMessage, ChatRole, Kani

from server.engine import get_or_create_engine_from_model

from ..models import Bot, Conversation, Utterance
from .moderation import moderate_message

# Get logger for this module
logger = logging.getLogger(__name__)

# Dictionary to store engine instances
engine_instances = {}


def generate_system_prompt(bot, selected_persona=None):
    """
    Generate a dynamic system prompt by combining the bot's base prompt
    with instructions from the selected persona for this conversation.

    Args:
        bot: Bot instance with prompt
        selected_persona: Persona instance selected for this conversation (can be None)

    Returns:
        str: Combined system prompt
    """
    try:
        # Start with the bot's base prompt
        system_prompt = bot.prompt.strip() if bot.prompt else ""

        # Add selected persona instructions if available
        if (
            selected_persona
            and hasattr(selected_persona, "name")
            and hasattr(selected_persona, "instructions")
        ):
            # Combine base prompt with persona instructions
            if system_prompt:
                system_prompt += "\n\n"

            system_prompt += f"Additional personality instructions:\nPersona '{selected_persona.name}': {selected_persona.instructions}"

        return system_prompt
    except Exception as e:
        logger.error(f"Error generating system prompt: {e}")
        # Fallback to just the bot's prompt
        return bot.prompt.strip() if bot.prompt else ""


async def save_chat_to_db(
    conversation_id,
    speaker_id,
    text,
    bot_name=None,
    participant_id=None,
    instruction_prompt=None,
    chat_history_used=None,
):
    """
    Save chat messages asynchronously to the Utterance table.
    """
    try:
        conversation = await sync_to_async(Conversation.objects.get)(
            conversation_id=conversation_id,
        )

        await sync_to_async(Utterance.objects.create)(
            conversation=conversation,
            speaker_id=speaker_id,
            bot_name=bot_name,
            participant_id=participant_id,
            text=text,
            instruction_prompt=instruction_prompt,
            chat_history_used=chat_history_used,
        )

    except Conversation.DoesNotExist:
        logger.warning(f"Conversation with ID {conversation_id} not found.")
    except Exception as e:
        logger.error(f"Failed to save message to Utterance table: {e}")
        import traceback

        traceback.print_exc()


async def run_chat_round(bot_name, conversation_id, participant_id, message):
    """
    Handles one full round of chat interaction: user -> bot response.
    Runs moderation on incoming message before processing.
    Returns the bot response text.
    """
    # Prevent followup requests from being processed as regular user messages
    if message.startswith("[FOLLOW-UP REQUEST]"):
        logger.warning(
            f"Followup request detected in regular chat round, ignoring: {message[:50]}...",
        )
        return "I'm sorry, but I can't process followup requests through the regular chat. Please use the appropriate followup mechanism."

    # Fetch bot object with personas and ai_model prefetched
    bot = await sync_to_async(
        Bot.objects.prefetch_related("personas", "ai_model__provider").get,
    )(name=bot_name)

    # Moderate incoming message
    # Run in thread to avoid blocking
    blocked = await sync_to_async(moderate_message)(message, bot)
    if blocked:
        # Prepare a warning response without further processing
        warning_text = f"Your message was blocked by moderation due to: {blocked}"
        # Save both user message and moderation response
        await save_chat_to_db(
            conversation_id=conversation_id,
            speaker_id="user",
            text=message,
            bot_name=None,
            participant_id=participant_id,
        )
        await save_chat_to_db(
            conversation_id=conversation_id,
            speaker_id="assistant",
            text=warning_text,
            bot_name=bot.name,
            participant_id=None,
            instruction_prompt=bot.prompt,  # Use bot prompt for moderation responses
        )
        return warning_text

    # Retrieve history from cache
    cache_key = f"conversation_cache_{conversation_id}"
    conversation_history = cache.get(cache_key, [])

    # If cache is empty, try to load from database
    if not conversation_history:
        try:
            conversation = await sync_to_async(Conversation.objects.get)(
                conversation_id=conversation_id,
            )
            utterances = await sync_to_async(list)(
                Utterance.objects.filter(conversation=conversation).order_by(
                    "created_time",
                ),
            )

            # Build conversation history from database
            for utterance in utterances:
                role = "user" if utterance.speaker_id == "user" else "assistant"
                conversation_history.append({"role": role, "content": utterance.text})

            # Populate cache
            cache.set(cache_key, conversation_history, timeout=3600)
            logger.info(
                f"Loaded {len(conversation_history)} messages from database for conversation {conversation_id}",
            )
        except Exception as e:
            logger.warning(f"Failed to load conversation history from database: {e}")
            conversation_history = []

    # Apply transcript length limit to history only (before adding new message)
    if bot.max_transcript_length > 0:
        # Keep only the latest messages from history up to the limit
        conversation_history = conversation_history[-bot.max_transcript_length :]
        logger.info(
            f"Limited history to {len(conversation_history)} messages (max: {bot.max_transcript_length})",
        )
    elif bot.max_transcript_length == 0:
        # 0 means no chat history - clear history
        conversation_history = []
        logger.info("No chat history - using only current message")
    else:
        logger.info(
            f"No transcript limit applied, using all {len(conversation_history)} messages from history",
        )

    # Append new message after applying transcript limit
    conversation_history.append({"role": "user", "content": message})

    # Format for Kani
    formatted_history = [
        ChatMessage(
            role=ChatRole.USER if msg["role"] == "user" else ChatRole.ASSISTANT,
            content=str(msg["content"]),
        )
        for msg in conversation_history
    ]

    # Get the selected persona for this conversation
    conversation = await sync_to_async(
        Conversation.objects.select_related("selected_persona").get,
    )(conversation_id=conversation_id)
    selected_persona = conversation.selected_persona

    # Generate dynamic system prompt combining bot prompt with selected persona
    system_prompt = generate_system_prompt(bot, selected_persona)

    # Log the generated prompt for debugging
    logger.info(f"Bot '{bot.name}' system prompt:")
    logger.info(f"   Base prompt: {bot.prompt[:100] if bot.prompt else 'None'}...")
    logger.info(
        f"   Selected persona: {selected_persona.name if selected_persona and hasattr(selected_persona, 'name') else 'None'}",
    )
    logger.info(f"   Final prompt length: {len(system_prompt)} characters")

    # Run Kani - ai_model is now required
    engine = get_or_create_engine_from_model(bot.ai_model, engine_instances)
    kani = Kani(engine, system_prompt=system_prompt, chat_history=formatted_history)

    latest_user_message = formatted_history[-1].content
    response_text = ""

    async for msg in kani.full_round(query=latest_user_message):
        if hasattr(msg, "text") and isinstance(msg.text, str):
            response_text += msg.text + " "

    response_text = response_text.strip()

    # Capture the chat history that was actually used (before appending bot response)
    # Store only the chat history sent to LLM (excluding the new user message)
    chat_history_json = json.dumps(conversation_history[:-1], indent=2)

    # Append bot response
    conversation_history.append({"role": "assistant", "content": response_text})
    cache.set(cache_key, conversation_history, timeout=3600)

    # Save to DB (but not followup requests)
    if not message.startswith("[FOLLOW-UP REQUEST]"):
        await save_chat_to_db(
            conversation_id=conversation_id,
            speaker_id="user",
            text=message,
            bot_name=None,
            participant_id=participant_id,
        )

    await save_chat_to_db(
        conversation_id=conversation_id,
        speaker_id="assistant",
        text=response_text,
        bot_name=bot.name,
        participant_id=None,
        instruction_prompt=system_prompt,
        chat_history_used=chat_history_json,
    )

    return response_text
